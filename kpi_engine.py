"""KPI engine"""
from app.config import DIESEL_FACTOR, ELECTRICITY_FACTOR, MANHOURS_PER_PROJECT, GRADE_THRESHOLDS


def compute_metric(key, raw):
    if raw is None: return 0.0
    try: v = float(raw)
    except (ValueError, TypeError): return 0.0
    if key == "scope1_fuel": return round((v * DIESEL_FACTOR) / 1000, 3)
    if key == "scope2_power": return round((v * ELECTRICITY_FACTOR) / 1000, 3)
    if key == "ltifr_input": return round((v * 1000000) / MANHOURS_PER_PROJECT, 3)
    if key in ("fatalities", "posh_complaints", "skilling_beneficiaries", "community_water"): return int(v)
    return round(v, 2)


def compute_esg_rating(m):
    env = [min(100, m.get("tunnel_ventilation", 0)), min(100, m.get("dust_suppression", 0)),
           min(100, m.get("dam_water_quality", 0) * 10), min(100, m.get("renewable_share", 0) * 2.5),
           min(100, m.get("water_recycle_rate", 0) * 2),
           100 - min(100, m.get("scope1_fuel", 0) / 20), 100 - min(100, m.get("scope2_power", 0) / 20)]
    env_s = sum(env) / len(env)
    lt = min(100, m.get("ltifr_input", 0) * 500)
    soc = [100 - lt, 100 - min(100, m.get("fatalities", 0) * 30),
           min(100, m.get("crane_safety", 0)), min(100, m.get("female_wage_pct", 0) * 1.2),
           min(100, m.get("women_workforce_pct", 0) * 4), min(100, m.get("contractor_insurance", 0))]
    soc_s = sum(soc) / len(soc)
    gov = [min(100, m.get("msme_sourcing_pct", 0) * 1.5), min(100, m.get("local_hiring_pct", 0) * 1.2),
           min(100, m.get("csr_spend", 0) / 4), min(100, m.get("abac_coverage", 0)),
           100 - min(100, m.get("grievance_tat", 0) * 5)]
    gov_s = sum(gov) / len(gov)
    total = round((env_s + soc_s + gov_s) / 3, 1)
    grade = "D"
    for g, t in GRADE_THRESHOLDS.items():
        if total >= t: grade = g; break
    return {"environmental": round(env_s, 1), "social": round(soc_s, 1),
            "governance": round(gov_s, 1), "total": total, "grade": grade}


def compute_risk(summary, meta):
    risks = {"E": [], "S": [], "G": []}
    for key, m in meta.items():
        cat = m["category"]; w = m["risk_weight"]; v = summary.get(key, 0)
        if key == "ltifr_input": r = min(100, v * 500)
        elif key == "fatalities": r = min(100, v * 30)
        elif key in ("scope1_fuel", "scope2_power"): r = min(100, v / 20)
        elif key in ("female_wage_pct","women_workforce_pct","renewable_share","water_recycle_rate",
                     "crane_safety","abac_coverage","msme_sourcing_pct","local_hiring_pct",
                     "tunnel_ventilation","dust_suppression","contractor_insurance"):
            r = max(0, 100 - v)
        elif key == "grievance_tat": r = min(100, v * 5)
        else: r = 50
        risks[cat].append(r * w)
    return {c: round(sum(risks[c]) / len(risks[c]), 1) if risks[c] else 0 for c in ("E", "S", "G")}
