"""Metric-aware consolidation"""
from app.config import MANHOURS_PER_PROJECT


def aggregate(metric, items):
    rule = getattr(metric, "aggregation_rule", "sum")
    nn = [(v, w, r) for (v, w, r) in items if v is not None]
    if not nn: return 0.0
    if rule == "sum": return round(sum(v for v, _, _ in nn), 2)
    if rule == "weighted":
        tw = sum(w for _, w, _ in nn)
        if tw == 0: return round(sum(v for v, _, _ in nn) / len(nn), 2)
        return round(sum(v * w for v, w, _ in nn) / tw, 2)
    if rule == "ltifr":
        ti = sum(r for _, _, r in nn if r is not None)
        th = MANHOURS_PER_PROJECT * len(nn)
        if th == 0: return 0.0
        return round((ti * 1000000) / th, 3)
    return round(sum(v for v, _, _ in nn), 2)
