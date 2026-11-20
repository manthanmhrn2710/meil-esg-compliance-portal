"""HTTP routes"""
from flask import Blueprint, request, jsonify, session, send_file
from functools import wraps
from datetime import datetime
import os, io
from app.models import (SessionLocal, Employee, BusinessUnit, FinancialYear,
                         ESGMetric, ReportCycle, MetricValue, ActivityLog,
                         ReportingBoundary, hash_password)
from app.kpi_engine import compute_metric, compute_esg_rating, compute_risk
from app.consolidation import aggregate
from app.config import UPLOAD_FOLDER, PROJECT_PORTFOLIO

api = Blueprint("api", __name__, url_prefix="/api")
STATES = ["DRAFT", "PROJECT_REVIEW", "SUBSIDIARY_CONSOLIDATION",
          "GROUP_CONSOLIDATION", "FINAL_APPROVAL", "LOCKED"]


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "employee_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        return f(*args, **kwargs)
    return wrapper


def log_act(db, eid, action, tt, tid, note=""):
    db.add(ActivityLog(employee_id=eid, activity_type=action, target_type=tt,
                       target_id=tid, activity_note=note))
    db.commit()


def desc(db, root):
    ids = [root]; stack = [root]
    while stack:
        c = stack.pop()
        for x in db.query(BusinessUnit).filter(BusinessUnit.parent_id == c).all():
            ids.append(x.id); stack.append(x.id)
    return ids


def summarize(db, uid, fid):
    uids = desc(db, uid)
    cycles = db.query(ReportCycle).filter(ReportCycle.unit_id.in_(uids),
                                           ReportCycle.fy_id == fid).all()
    cids = [c.id for c in cycles]
    vals = db.query(MetricValue).filter(MetricValue.cycle_id.in_(cids)).all() if cids else []
    metrics = db.query(ESGMetric).all()
    mmap = {m.id: m for m in metrics}
    buckets = {}
    for v in vals:
        m = mmap.get(v.metric_id)
        if not m: continue
        cyc = next((c for c in cycles if c.id == v.cycle_id), None)
        unit = db.query(BusinessUnit).filter(BusinessUnit.id == cyc.unit_id).first() if cyc else None
        w = unit.employee_count if unit and unit.employee_count else 1
        buckets.setdefault(m.compute_key, {"metric": m, "items": []})
        buckets[m.compute_key]["items"].append((v.computed_value, w, v.input_value))
    summary = {k: aggregate(b["metric"], b["items"]) for k, b in buckets.items()}
    for m in metrics:
        if m.compute_key not in summary:
            summary[m.compute_key] = 0
    return summary, cycles, vals, mmap


@api.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    pw = request.form.get("password", "")
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.email == email).first()
        if not emp or emp.password_hash != hash_password(pw):
            return jsonify({"error": "Invalid credentials"}), 401
        session["employee_id"] = emp.id
        session["unit_id"] = emp.unit_id
        unit = db.query(BusinessUnit).filter(BusinessUnit.id == emp.unit_id).first()
        log_act(db, emp.id, "LOGIN", "Employee", emp.id, "Logged in")
        return jsonify({"employee": {
            "id": emp.id, "name": emp.full_name, "email": emp.email,
            "designation": emp.designation, "role_title": emp.role_title,
            "unit_id": emp.unit_id, "unit_name": unit.unit_name if unit else "N/A"}})
    finally:
        db.close()


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@api.route("/metrics", methods=["GET"])
@login_required
def get_metrics():
    db = SessionLocal()
    try:
        return jsonify([{"id": m.id, "principle": m.ngbrc_principle,
            "category": m.metric_category, "section": m.brsr_section,
            "name": m.metric_name, "unit": m.metric_unit,
            "dept": m.responsible_dept, "compute_key": m.compute_key,
            "sdg_number": m.sdg_number, "sdg_label": m.sdg_label,
            "assurance": m.assurance_required, "risk_weight": m.risk_weight,
            "aggregation_rule": m.aggregation_rule} for m in db.query(ESGMetric).all()])
    finally:
        db.close()


@api.route("/portfolio", methods=["GET"])
@login_required
def get_portfolio():
    return jsonify(PROJECT_PORTFOLIO)


@api.route("/cycle/<int:uid>", methods=["GET"])
@login_required
def get_cycle(uid):
    db = SessionLocal()
    try:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        cyc = db.query(ReportCycle).filter(ReportCycle.unit_id == uid,
                                            ReportCycle.fy_id == fy.id).first()
        if not cyc:
            cyc = ReportCycle(unit_id=uid, fy_id=fy.id, cycle_status="DRAFT")
            db.add(cyc); db.commit(); db.refresh(cyc)
        vals = db.query(MetricValue).filter(MetricValue.cycle_id == cyc.id).all()
        return jsonify({"cycle_id": cyc.id, "status": cyc.cycle_status,
            "fy_label": fy.fy_label, "is_locked": cyc.cycle_status == "LOCKED",
            "values": [{"id": v.id, "metric_id": v.metric_id,
                "input_value": v.input_value, "computed_value": v.computed_value,
                "evidence_file": v.evidence_file, "source_document": v.source_document,
                "page_number": v.page_number, "sheet_name": v.sheet_name,
                "notes": v.notes} for v in vals]})
    finally:
        db.close()


@api.route("/metric-value", methods=["POST"])
@login_required
def save_metric():
    cid = int(request.form.get("cycle_id"))
    mid = int(request.form.get("metric_id"))
    raw = float(request.form.get("value", 0))
    notes = request.form.get("notes", "")
    src = request.form.get("source_document", "")
    pg = request.form.get("page_number", "")
    sh = request.form.get("sheet_name", "")
    db = SessionLocal()
    try:
        cyc = db.query(ReportCycle).filter(ReportCycle.id == cid).first()
        if cyc and cyc.cycle_status == "LOCKED":
            return jsonify({"error": "Locked"}), 403
        m = db.query(ESGMetric).filter(ESGMetric.id == mid).first()
        if not m: return jsonify({"error": "Not found"}), 404
        computed = compute_metric(m.compute_key, raw)
        ex = db.query(MetricValue).filter(MetricValue.cycle_id == cid,
                                           MetricValue.metric_id == mid).first()
        if ex:
            ex.input_value = raw; ex.computed_value = computed; ex.notes = notes
            ex.source_document = src; ex.page_number = pg; ex.sheet_name = sh
            ex.updated_on = datetime.utcnow(); mv = ex
        else:
            mv = MetricValue(cycle_id=cid, metric_id=mid, input_value=raw,
                             computed_value=computed, notes=notes,
                             source_document=src, page_number=pg, sheet_name=sh)
            db.add(mv)
        db.commit()
        return jsonify({"ok": True, "value_id": mv.id, "computed": computed})
    finally:
        db.close()


@api.route("/upload-evidence", methods=["POST"])
@login_required
def upload_ev():
    vid = int(request.form.get("value_id"))
    f = request.files.get("file")
    if not f: return jsonify({"error": "No file"}), 400
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(UPLOAD_FOLDER, str(vid) + "_" + f.filename)
    f.save(path)
    db = SessionLocal()
    try:
        mv = db.query(MetricValue).filter(MetricValue.id == vid).first()
        if not mv: return jsonify({"error": "Not found"}), 404
        mv.evidence_file = f.filename; db.commit()
        return jsonify({"ok": True, "filename": f.filename})
    finally:
        db.close()


@api.route("/cycle/<int:cid>/transition", methods=["POST"])
@login_required
def transition(cid):
    target = request.form.get("target_state", "")
    db = SessionLocal()
    try:
        cyc = db.query(ReportCycle).filter(ReportCycle.id == cid).first()
        if not cyc: return jsonify({"error": "Not found"}), 404
        if target not in STATES: return jsonify({"error": "Invalid"}), 400
        cyc.cycle_status = target
        now = datetime.utcnow()
        if target == "PROJECT_REVIEW": cyc.submitted_on = now
        elif target == "FINAL_APPROVAL": cyc.approved_on = now
        elif target == "LOCKED": cyc.locked_on = now
        db.commit()
        log_act(db, session["employee_id"], "TRANSITION", "ReportCycle", cyc.id, target)
        return jsonify({"ok": True, "status": target})
    finally:
        db.close()


@api.route("/cycle/<int:cid>/submit", methods=["POST"])
@login_required
def submit_cycle(cid):
    return transition(cid)


@api.route("/cycle/<int:cid>/reject", methods=["POST"])
@login_required
def reject_cycle(cid):
    db = SessionLocal()
    try:
        cyc = db.query(ReportCycle).filter(ReportCycle.id == cid).first()
        if not cyc: return jsonify({"error": "Not found"}), 404
        prev = {"PROJECT_REVIEW": "DRAFT",
                "SUBSIDIARY_CONSOLIDATION": "PROJECT_REVIEW",
                "GROUP_CONSOLIDATION": "SUBSIDIARY_CONSOLIDATION",
                "FINAL_APPROVAL": "GROUP_CONSOLIDATION"}
        cyc.cycle_status = prev.get(cyc.cycle_status, "DRAFT"); db.commit()
        return jsonify({"ok": True, "status": cyc.cycle_status})
    finally:
        db.close()


@api.route("/dashboard/<int:uid>", methods=["GET"])
@login_required
def get_dashboard(uid):
    db = SessionLocal()
    try:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        summary, cycles, vals, mmap = summarize(db, uid, fy.id)
        tq = db.query(ESGMetric).count()
        filled = len({(v.cycle_id, v.metric_id) for v in vals})
        comp = round(filled / max(tq * max(len(cycles), 1), 1) * 100, 1)
        esg = compute_esg_rating(summary)
        meta = {m.compute_key: {"category": m.metric_category, "risk_weight": m.risk_weight}
                for m in db.query(ESGMetric).all()}
        risk = compute_risk(summary, meta)
        breakdown = []
        for c in cycles:
            u = db.query(BusinessUnit).filter(BusinessUnit.id == c.unit_id).first()
            uv = [v for v in vals if v.cycle_id == c.id]
            en = sum(v.computed_value or 0 for v in uv if mmap.get(v.metric_id) and mmap[v.metric_id].compute_key == "total_energy")
            wa = sum(v.computed_value or 0 for v in uv if mmap.get(v.metric_id) and mmap[v.metric_id].compute_key == "water_withdrawal")
            co = sum(v.computed_value or 0 for v in uv if mmap.get(v.metric_id) and mmap[v.metric_id].compute_key in ("scope1_fuel", "scope2_power"))
            breakdown.append({"unit": u.unit_name if u else "N/A",
                "type": u.unit_type if u else "unknown", "state": u.state if u else "",
                "energy": round(en, 2), "water": round(wa, 2), "co2": round(co, 3),
                "contract_value_cr": u.contract_value_cr if u else 0,
                "cycle_status": c.cycle_status})
        return jsonify({"fy_label": fy.fy_label, "completeness": comp,
            "summary": summary, "esg_rating": esg, "risk": risk,
            "breakdown": breakdown, "total_cycles": len(cycles),
            "verified_count": sum(1 for c in cycles if c.cycle_status in ("SUBSIDIARY_CONSOLIDATION", "GROUP_CONSOLIDATION", "FINAL_APPROVAL", "LOCKED")),
            "pending_count": sum(1 for c in cycles if c.cycle_status == "PROJECT_REVIEW"),
            "locked_count": sum(1 for c in cycles if c.cycle_status == "LOCKED"),
            "in_progress_count": sum(1 for c in cycles if c.cycle_status == "DRAFT")})
    finally:
        db.close()


@api.route("/comparison/<int:uid>", methods=["GET"])
@login_required
def get_comp(uid):
    db = SessionLocal()
    try:
        fys = db.query(FinancialYear).order_by(FinancialYear.fy_start).all()
        return jsonify({fy.fy_label: summarize(db, uid, fy.id)[0] for fy in fys})
    finally:
        db.close()


@api.route("/sdg-summary/<int:uid>", methods=["GET"])
@login_required
def get_sdg(uid):
    db = SessionLocal()
    try:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        _, _, vals, mmap = summarize(db, uid, fy.id)
        data = {}
        for v in vals:
            m = mmap.get(v.metric_id)
            if m and m.sdg_number:
                n = m.sdg_number
                if n not in data: data[n] = {"number": n, "name": m.sdg_label, "total": 0, "count": 0}
                data[n]["total"] += v.computed_value or 0; data[n]["count"] += 1
        return jsonify(sorted(data.values(), key=lambda x: x["number"]))
    finally:
        db.close()


@api.route("/activity-log", methods=["GET"])
@login_required
def get_log():
    db = SessionLocal()
    try:
        logs = db.query(ActivityLog).order_by(ActivityLog.created_on.desc()).limit(200).all()
        em = {e.id: e.full_name for e in db.query(Employee).all()}
        return jsonify([{"id": l.id, "employee": em.get(l.employee_id, "?"),
                         "activity": l.activity_type, "note": l.activity_note,
                         "when": l.created_on.isoformat()} for l in logs])
    finally:
        db.close()


@api.route("/why-meil", methods=["GET"])
def why_meil():
    return jsonify({
        "mission": "MEIL is one of India's largest infrastructure companies with 250+ active projects.",
        "portfolio_cr": 30000, "employees": 25000,
        "sectors": ["Water", "Irrigation", "Tunnels", "Metro", "Highways", "Energy"],
        "esg_challenges": ["Fragmented data across 250+ sites", "Manual Excel collection",
            "No standardized format", "Hard to audit", "SEBI BRSR mandatory"],
        "why_our_solution": ["Infrastructure-specific KPIs", "Metric-aware consolidation",
            "Boundary and intercompany controls", "Evidence lineage",
            "6-stage workflow with final lock"],
        "sebi_references": [
            "SEBI Circular SEBI/HO/CFD/CMD-2/P/CIR/2021/562 dated May 10, 2021 (BRSR introduced)",
            "SEBI LODR Regulations 2015, Reg 34(2)(f)",
            "SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 dated July 12, 2023 (BRSR Core)",
            "Master Circular SEBI/HO/CFD/PoD2/CIR/P/2023/120 dated July 11, 2023",
            "MCA National Guidelines on Responsible Business Conduct (NGRBC), March 2019"],
        "timeline": [{"year": "FY 2022-23", "event": "BRSR mandatory top 1,000"},
                     {"year": "FY 2023-24", "event": "BRSR Core top 150"},
                     {"year": "FY 2024-25", "event": "Extends to top 250"},
                     {"year": "FY 2026-27", "event": "Extends to top 1,000"}]
    })


@api.route("/export/excel/<int:uid>", methods=["GET"])
@login_required
def export_xlsx(uid):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    db = SessionLocal()
    try:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        u = db.query(BusinessUnit).filter(BusinessUnit.id == uid).first()
        _, _, vals, mmap = summarize(db, uid, fy.id)
        wb = Workbook(); ws = wb.active; ws.title = "BRSR Report"
        hf = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        ws.append(["BRSR-Report"]); ws["A1"].font = Font(bold=True, size=15)
        ws.append(["Organization", u.unit_name]); ws.append(["Period", fy.fy_label]); ws.append([])
        ws.append(["Section", "Principle", "Category", "Metric", "Unit", "Value", "SDG", "Assurance", "Aggregation"])
        for c in ws[5]: c.fill = hf; c.font = Font(bold=True, color="FFFFFF")
        for v in vals:
            m = mmap.get(v.metric_id)
            if m:
                sdg = "SDG " + str(m.sdg_number) if m.sdg_number else "-"
                ws.append([m.brsr_section, "P" + str(m.ngbrc_principle), m.metric_category,
                           m.metric_name, m.metric_unit, v.computed_value, sdg,
                           "Yes" if m.assurance_required else "No", m.aggregation_rule])
        for col in ws.columns:
            ml = max((len(str(c.value)) if c.value else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(ml + 3, 55)
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         as_attachment=True, download_name="BRSR_Report.xlsx")
    finally:
        db.close()


@api.route("/export/pdf/<int:uid>", methods=["GET"])
@login_required
def export_pdf(uid):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    db = SessionLocal()
    try:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        u = db.query(BusinessUnit).filter(BusinessUnit.id == uid).first()
        summary, _, vals, mmap = summarize(db, uid, fy.id)
        esg = compute_esg_rating(summary)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=0.6*inch, rightMargin=0.6*inch,
                                topMargin=0.6*inch, bottomMargin=0.6*inch)
        styles = getSampleStyleSheet()
        ts = ParagraphStyle("T", parent=styles["Heading1"], fontSize=20, textColor=colors.HexColor("#0F172A"))
        ss = ParagraphStyle("S", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
        story = [Paragraph("BRSR-Report", ts),
                 Paragraph("Organization: " + u.unit_name + " | Period: " + fy.fy_label, ss),
                 Paragraph("ESG Rating: " + str(esg["total"]) + " (Grade " + esg["grade"] + ")", styles["Heading3"]),
                 Spacer(1, 0.2*inch)]
        for cat, cn in [("E", "Environmental"), ("S", "Social"), ("G", "Governance")]:
            cv = [v for v in vals if mmap.get(v.metric_id) and mmap[v.metric_id].metric_category == cat]
            if not cv: continue
            story.append(Paragraph("<b>" + cn + "</b>", styles["Heading3"]))
            data = [["Principle", "Metric", "Unit", "Value"]]
            for v in cv:
                m = mmap.get(v.metric_id)
                if m: data.append(["P" + str(m.ngbrc_principle), m.metric_name[:50],
                                    m.metric_unit, str(v.computed_value or 0)])
            t = Table(data, colWidths=[0.8*inch, 3.2*inch, 0.9*inch, 1.1*inch])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])]))
            story.append(t); story.append(Spacer(1, 0.15*inch))
        doc.build(story); buf.seek(0)
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="BRSR_Report.pdf")
    finally:
        db.close()
