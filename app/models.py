"""Database models + seed data"""
from sqlalchemy import (create_engine, Column, Integer, String, Float, Text,
                        ForeignKey, DateTime, Boolean)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import hashlib
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def hash_password(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class BusinessUnit(Base):
    __tablename__ = "business_units"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("business_units.id"), nullable=True)
    unit_type = Column(String(30))
    unit_name = Column(String(250))
    state = Column(String(120), default="")
    lat = Column(Float, default=0)
    lng = Column(Float, default=0)
    contract_value_cr = Column(Float, default=0)
    physical_progress = Column(Float, default=0)
    employee_count = Column(Integer, default=0)
    children = relationship("BusinessUnit", backref="parent", remote_side=[id])


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("business_units.id"))
    designation = Column(String(100))
    email = Column(String(250), unique=True)
    password_hash = Column(String(250))
    full_name = Column(String(250))
    role_title = Column(String(250), default="")


class FinancialYear(Base):
    __tablename__ = "financial_years"
    id = Column(Integer, primary_key=True)
    fy_label = Column(String(30))
    fy_start = Column(String(20))
    fy_end = Column(String(20))
    is_active = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)


class ESGMetric(Base):
    __tablename__ = "esg_metrics"
    id = Column(Integer, primary_key=True)
    ngbrc_principle = Column(Integer)
    metric_category = Column(String(5))
    brsr_section = Column(String(10), default="C")
    metric_name = Column(Text)
    metric_unit = Column(String(60))
    responsible_dept = Column(String(60))
    compute_key = Column(String(60))
    sdg_number = Column(Integer, default=0)
    sdg_label = Column(String(150), default="")
    assurance_required = Column(Boolean, default=False)
    risk_weight = Column(Float, default=1.0)
    aggregation_rule = Column(String(30), default="sum")


class ReportCycle(Base):
    __tablename__ = "report_cycles"
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("business_units.id"))
    fy_id = Column(Integer, ForeignKey("financial_years.id"))
    cycle_status = Column(String(30), default="DRAFT")
    boundary_type = Column(String(20), default="standalone")
    submitted_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    locked_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    submitted_on = Column(DateTime, nullable=True)
    verified_on = Column(DateTime, nullable=True)
    approved_on = Column(DateTime, nullable=True)
    locked_on = Column(DateTime, nullable=True)


class MetricValue(Base):
    __tablename__ = "metric_values"
    id = Column(Integer, primary_key=True)
    cycle_id = Column(Integer, ForeignKey("report_cycles.id"))
    metric_id = Column(Integer, ForeignKey("esg_metrics.id"))
    input_value = Column(Float, nullable=True)
    computed_value = Column(Float, nullable=True)
    evidence_file = Column(String(350), nullable=True)
    source_document = Column(String(250), nullable=True)
    page_number = Column(String(50), nullable=True)
    sheet_name = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    updated_on = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    activity_type = Column(String(60))
    target_type = Column(String(60))
    target_id = Column(Integer)
    activity_note = Column(Text)
    created_on = Column(DateTime, default=datetime.utcnow)


class ReportingBoundary(Base):
    __tablename__ = "reporting_boundaries"
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("business_units.id"))
    fy_id = Column(Integer, ForeignKey("financial_years.id"))
    boundary_type = Column(String(20), default="standalone")
    standalone_included = Column(Boolean, default=True)
    consolidated_included = Column(Boolean, default=False)
    notes = Column(Text, default="")


DEMO_INPUTS = {
    "Hyderabad Water Grid": {"total_energy": 12500, "water_withdrawal": 48000, "waste_total": 340, "scope1_fuel": 4200, "scope2_power": 8500, "tunnel_ventilation": 82, "dam_water_quality": 7.2, "dust_suppression": 88, "renewable_share": 22, "water_recycle_rate": 38, "ltifr_input": 3, "fatalities": 0, "crane_safety": 94, "training_hours": 12, "posh_complaints": 1, "female_wage_pct": 78, "women_workforce_pct": 14, "contractor_insurance": 96, "msme_sourcing_pct": 42, "csr_spend": 180, "local_hiring_pct": 55, "skilling_beneficiaries": 620, "community_water": 340, "abac_coverage": 92, "grievance_tat": 6},
    "Godavari Lift Irrigation": {"total_energy": 18200, "water_withdrawal": 72000, "waste_total": 520, "scope1_fuel": 6800, "scope2_power": 12500, "tunnel_ventilation": 76, "dam_water_quality": 6.8, "dust_suppression": 82, "renewable_share": 18, "water_recycle_rate": 32, "ltifr_input": 5, "fatalities": 1, "crane_safety": 88, "training_hours": 18, "posh_complaints": 2, "female_wage_pct": 74, "women_workforce_pct": 11, "contractor_insurance": 92, "msme_sourcing_pct": 38, "csr_spend": 240, "local_hiring_pct": 48, "skilling_beneficiaries": 890, "community_water": 520, "abac_coverage": 88, "grievance_tat": 8},
    "Metro Phase-3 Tunnels": {"total_energy": 21500, "water_withdrawal": 38000, "waste_total": 780, "scope1_fuel": 9200, "scope2_power": 15800, "tunnel_ventilation": 91, "dam_water_quality": 7.8, "dust_suppression": 94, "renewable_share": 28, "water_recycle_rate": 45, "ltifr_input": 2, "fatalities": 0, "crane_safety": 96, "training_hours": 24, "posh_complaints": 0, "female_wage_pct": 82, "women_workforce_pct": 16, "contractor_insurance": 98, "msme_sourcing_pct": 46, "csr_spend": 320, "local_hiring_pct": 62, "skilling_beneficiaries": 1100, "community_water": 280, "abac_coverage": 96, "grievance_tat": 4},
    "Mahanadi Canal Tunnels": {"total_energy": 9800, "water_withdrawal": 42000, "waste_total": 280, "scope1_fuel": 3100, "scope2_power": 6800, "tunnel_ventilation": 71, "dam_water_quality": 6.5, "dust_suppression": 78, "renewable_share": 15, "water_recycle_rate": 28, "ltifr_input": 4, "fatalities": 0, "crane_safety": 85, "training_hours": 9, "posh_complaints": 1, "female_wage_pct": 71, "women_workforce_pct": 9, "contractor_insurance": 90, "msme_sourcing_pct": 52, "csr_spend": 140, "local_hiring_pct": 72, "skilling_beneficiaries": 480, "community_water": 410, "abac_coverage": 84, "grievance_tat": 10},
    "NH-48 Highway Package": {"total_energy": 14200, "water_withdrawal": 28000, "waste_total": 410, "scope1_fuel": 5400, "scope2_power": 9800, "tunnel_ventilation": 68, "dam_water_quality": 6.2, "dust_suppression": 86, "renewable_share": 20, "water_recycle_rate": 35, "ltifr_input": 3, "fatalities": 1, "crane_safety": 91, "training_hours": 14, "posh_complaints": 0, "female_wage_pct": 76, "women_workforce_pct": 12, "contractor_insurance": 94, "msme_sourcing_pct": 44, "csr_spend": 160, "local_hiring_pct": 58, "skilling_beneficiaries": 720, "community_water": 190, "abac_coverage": 90, "grievance_tat": 7},
}

METRICS = [
    (6, "E", "Total energy consumption", "GJ", "HSE", "total_energy", 7, "Affordable & Clean Energy", True, 1.0, "sum"),
    (6, "E", "Fresh water withdrawal", "KL", "HSE", "water_withdrawal", 6, "Clean Water & Sanitation", True, 1.2, "sum"),
    (6, "E", "Construction waste generated", "MT", "HSE", "waste_total", 12, "Responsible Consumption", True, 0.8, "sum"),
    (6, "E", "Scope 1 GHG emissions", "tCO2e", "HSE", "scope1_fuel", 13, "Climate Action", True, 1.5, "sum"),
    (6, "E", "Scope 2 GHG emissions", "tCO2e", "HSE", "scope2_power", 13, "Climate Action", True, 1.5, "sum"),
    (6, "E", "Tunnel ventilation efficiency", "%", "HSE", "tunnel_ventilation", 9, "Industry & Infrastructure", False, 1.0, "weighted"),
    (6, "E", "Dam water quality index", "score", "HSE", "dam_water_quality", 6, "Clean Water & Sanitation", False, 1.0, "weighted"),
    (6, "E", "Dust suppression coverage", "%", "HSE", "dust_suppression", 11, "Sustainable Cities", False, 0.8, "weighted"),
    (6, "E", "Renewable energy share", "%", "HSE", "renewable_share", 7, "Affordable & Clean Energy", False, 1.0, "weighted"),
    (6, "E", "Water recycling rate", "%", "HSE", "water_recycle_rate", 6, "Clean Water & Sanitation", False, 1.0, "weighted"),
    (3, "S", "Lost time injuries", "count", "HSE", "ltifr_input", 8, "Decent Work", True, 2.0, "ltifr"),
    (3, "S", "Work-related fatalities", "count", "HSE", "fatalities", 8, "Decent Work", True, 3.0, "sum"),
    (3, "S", "Crane safety audit score", "%", "HSE", "crane_safety", 8, "Decent Work", False, 1.5, "weighted"),
    (3, "S", "Safety training manhours", "hours", "HR", "training_hours", 8, "Decent Work", False, 0.8, "sum"),
    (5, "S", "POSH complaints", "count", "HR", "posh_complaints", 5, "Gender Equality", True, 1.2, "sum"),
    (5, "S", "Female wage parity %", "%", "HR", "female_wage_pct", 5, "Gender Equality", True, 1.0, "weighted"),
    (5, "S", "Women in workforce %", "%", "HR", "women_workforce_pct", 5, "Gender Equality", False, 1.0, "weighted"),
    (3, "S", "Contractor insurance %", "%", "HR", "contractor_insurance", 8, "Decent Work", False, 0.6, "weighted"),
    (8, "G", "MSME sourcing %", "%", "Procurement", "msme_sourcing_pct", 8, "Decent Work", True, 0.8, "weighted"),
    (8, "G", "CSR spend (lakhs)", "lakhs", "CSR", "csr_spend", 1, "No Poverty", False, 0.6, "sum"),
    (8, "G", "Local village hiring %", "%", "HR", "local_hiring_pct", 8, "Decent Work", False, 0.8, "weighted"),
    (8, "G", "Skilling beneficiaries", "count", "CSR", "skilling_beneficiaries", 4, "Quality Education", False, 0.5, "sum"),
    (8, "G", "Community water access", "households", "CSR", "community_water", 6, "Clean Water & Sanitation", False, 0.6, "sum"),
    (1, "G", "Anti-bribery coverage %", "%", "Legal", "abac_coverage", 16, "Strong Institutions", True, 1.2, "weighted"),
    (1, "G", "Grievance turnaround (days)", "days", "Legal", "grievance_tat", 16, "Strong Institutions", False, 0.6, "weighted"),
]


def _seed_val(key, raw):
    if key == "scope1_fuel": return round((raw * 2.68) / 1000, 3)
    if key == "scope2_power": return round((raw * 0.82) / 1000, 3)
    if key == "ltifr_input": return round((raw * 1000000) / 500000, 3)
    if key in ("fatalities", "posh_complaints", "skilling_beneficiaries", "community_water"): return int(raw)
    return round(raw, 2)


def bootstrap_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(BusinessUnit).count() > 0:
        db.close()
        return

    group = BusinessUnit(unit_type="group", unit_name="MEIL Group", state="Telangana", employee_count=25000)
    db.add(group); db.flush()
    infra = BusinessUnit(parent_id=group.id, unit_type="subsidiary", unit_name="MEIL Infrastructure", state="Telangana", employee_count=15000)
    energy = BusinessUnit(parent_id=group.id, unit_type="subsidiary", unit_name="MEIL Energy", state="Maharashtra", employee_count=10000)
    db.add_all([infra, energy]); db.flush()
    wb = BusinessUnit(parent_id=infra.id, unit_type="division", unit_name="Water Division", state="Telangana", employee_count=5000)
    tb = BusinessUnit(parent_id=infra.id, unit_type="division", unit_name="Tunnel & Metro", state="Telangana", employee_count=8000)
    rb = BusinessUnit(parent_id=energy.id, unit_type="division", unit_name="Highways", state="Gujarat", employee_count=6000)
    db.add_all([wb, tb, rb]); db.flush()

    projects = [
        BusinessUnit(parent_id=wb.id, unit_type="project", unit_name="Hyderabad Water Grid", state="Telangana", lat=17.385, lng=78.486, contract_value_cr=4200, physical_progress=68, employee_count=800),
        BusinessUnit(parent_id=wb.id, unit_type="project", unit_name="Godavari Lift Irrigation", state="Telangana", lat=18.112, lng=79.594, contract_value_cr=8500, physical_progress=42, employee_count=1200),
        BusinessUnit(parent_id=tb.id, unit_type="project", unit_name="Metro Phase-3 Tunnels", state="Telangana", lat=17.423, lng=78.473, contract_value_cr=6300, physical_progress=75, employee_count=1500),
        BusinessUnit(parent_id=tb.id, unit_type="project", unit_name="Mahanadi Canal Tunnels", state="Odisha", lat=20.296, lng=85.824, contract_value_cr=3100, physical_progress=55, employee_count=600),
        BusinessUnit(parent_id=rb.id, unit_type="project", unit_name="NH-48 Highway Package", state="Gujarat", lat=23.022, lng=72.571, contract_value_cr=2800, physical_progress=82, employee_count=400),
    ]
    db.add_all(projects); db.flush()

    emps = [
        Employee(unit_id=group.id, designation="group_admin", email="director@meil.com", password_hash=hash_password("brsr@2026"), full_name="Rajesh Kumar", role_title="Group ESG Director"),
        Employee(unit_id=infra.id, designation="subsidiary_admin", email="infra.esg@meil.com", password_hash=hash_password("brsr@2026"), full_name="Priya Sharma", role_title="Infrastructure ESG Manager"),
        Employee(unit_id=tb.id, designation="bu_reviewer", email="tunnel.lead@meil.com", password_hash=hash_password("brsr@2026"), full_name="Amit Reddy", role_title="Tunnel Division HSE Lead"),
        Employee(unit_id=projects[2].id, designation="project_user", email="metro.hse@meil.com", password_hash=hash_password("brsr@2026"), full_name="Suresh Patel", role_title="Metro Project HSE Officer"),
    ]
    db.add_all(emps); db.flush()

    db.add_all([
        FinancialYear(fy_label="FY 2024-25", fy_start="2024-04-01", fy_end="2025-03-31", is_active=False, is_closed=True),
        FinancialYear(fy_label="FY 2025-26", fy_start="2025-04-01", fy_end="2026-03-31", is_active=True, is_closed=False)
    ])
    db.flush()

    for p, cat, name, unit, dept, key, sn, sl, a, r, agg in METRICS:
        db.add(ESGMetric(ngbrc_principle=p, metric_category=cat, brsr_section="C",
                         metric_name=name, metric_unit=unit, responsible_dept=dept,
                         compute_key=key, sdg_number=sn, sdg_label=sl,
                         assurance_required=a, risk_weight=r, aggregation_rule=agg))
    db.flush()

    mmap = {m.compute_key: m for m in db.query(ESGMetric).all()}
    for p in projects:
        cyc = ReportCycle(unit_id=p.id, fy_id=2, cycle_status="DRAFT", boundary_type="standalone")
        db.add(cyc); db.flush()
        if p.unit_name == "Metro Phase-3 Tunnels":
            cyc.cycle_status = "LOCKED"
            cyc.submitted_on = cyc.verified_on = cyc.approved_on = cyc.locked_on = datetime.utcnow()
        elif p.unit_name == "Hyderabad Water Grid":
            cyc.cycle_status = "PROJECT_REVIEW"
            cyc.submitted_on = datetime.utcnow()
        for key, raw in DEMO_INPUTS.get(p.unit_name, {}).items():
            m = mmap.get(key)
            if m:
                db.add(MetricValue(cycle_id=cyc.id, metric_id=m.id, input_value=raw,
                                   computed_value=_seed_val(key, raw),
                                   source_document="Demo Data", notes="Seeded"))
    db.commit()
    db.close()
    print("[OK] Database seeded")


if __name__ == "__main__":
    bootstrap_database()
