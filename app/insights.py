"""Chart-ready analytics built on the forecasting model: weekly forecast, backtest, feature importance, impact series."""
from datetime import date, timedelta
import pandas as pd
from . import db, ml
from .config import KG_PER_PORTION, PORTIONS_PER_KG, CO2E_PER_KG_FOOD

MEALS = ("lunch", "dinner")
LABELS = {"dtype": "Donor type", "wd": "Day of week", "meal": "Meal", "prepared": "Portions prepared",
          "rain": "Rain", "event": "Nearby event", "lag7": "Last 7 days' surplus"}

def _typical_prepared(c, donor_id, meal, n=14):
    r = c.execute("SELECT AVG(prepared) p FROM (SELECT prepared FROM logs WHERE donor_id=? AND meal=? ORDER BY day DESC LIMIT ?)", (donor_id, meal, n)).fetchone()
    return float(r["p"]) if r and r["p"] is not None else None

def _forecast_days(donor_ids, days, start):
    """Per-day forecast summed over the given donors. Rain and events are assumed absent; portions prepared = each donor's recent average."""
    items, order = [], []
    with db.conn() as c:
        for did in donor_ids:
            prep = {m: _typical_prepared(c, did, m) for m in MEALS}
            if any(v is None for v in prep.values()): continue          # no history -> cannot estimate typical prep
            for i in range(days):
                for m in MEALS:
                    items.append(dict(donor_id=did, meal=m, prepared=prep[m], rain=0, event=0, day=(start + timedelta(days=i)).isoformat())); order.append(i)
    res = ml.forecast_batch(items) if items else []
    tot = [dict(portions=0.0, low=0.0, high=0.0, lunch=0.0, dinner=0.0) for _ in range(days)]
    for it, r, i in zip(items, res, order):
        t = tot[i]; t["portions"] += r["portions"]; t["low"] += r["low"]; t["high"] += r["high"]; t[it["meal"]] += r["portions"]
    out = []
    for i, t in enumerate(tot):
        d = start + timedelta(days=i)
        out.append(dict(date=d.isoformat(), label=d.strftime("%a %d %b"), lunch=round(t["lunch"],1), dinner=round(t["dinner"],1),
                        portions=round(t["portions"],1), low=round(t["low"],1), high=round(t["high"],1),
                        kg=round(t["portions"]*KG_PER_PORTION,1), kg_low=round(t["low"]*KG_PER_PORTION,1), kg_high=round(t["high"]*KG_PER_PORTION,1)))
    return out

def week_forecast(donor_id, days=7, start=None):
    start = start or date.today()
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM donors WHERE id=?", (donor_id,)).fetchone(): raise KeyError("donor not found")
        prep = {m: _typical_prepared(c, donor_id, m) for m in MEALS}
    if any(v is None for v in prep.values()): raise ValueError("this donor has no log history yet")
    return dict(prepared_assumed={m: round(v) for m, v in prep.items()}, days=_forecast_days([donor_id], days, start),
                note="Assumes no rain or event and the donor's recent average portions prepared. Range is the sum of per-meal 10th to 90th percentile forecasts, so it is conservative (wide).")

def backtest(donor_id=None):
    M = ml._load()
    if not M or not M.get("backtest"): return []
    df = pd.DataFrame(M["backtest"])
    if donor_id is not None: df = df[df["donor_id"] == donor_id]
    if df.empty: return []
    g = df.groupby("day")[["actual", "pred", "baseline"]].sum().round(1).reset_index().sort_values("day")
    return [dict(day=str(r.day), actual=float(r.actual), pred=float(r.pred), baseline=float(r.baseline)) for r in g.itertuples()]

def importance():
    M = ml._load()
    if not M or "importance" not in M: return []
    return [dict(feature=k, label=LABELS.get(k, k), importance=float(v)) for k, v in sorted(M["importance"].items(), key=lambda kv: -kv[1])]

def observed_rate():
    with db.conn() as c:
        n = c.execute("SELECT COUNT(*) n FROM pickups").fetchone()["n"]
        k = c.execute("SELECT COUNT(*) n FROM pickups WHERE status='collected'").fetchone()["n"]
    return dict(rate=round(k/n, 3) if n else None, pickups=n, collected=k)

def impact_series(days_back=7, days_ahead=7, rescue_rate=0.5, today=None):
    """Cumulative kg rescued: actual (from collected pickups) then projected = forecast surplus x rescue_rate."""
    today = today or date.today()
    start = today - timedelta(days=days_back - 1)
    with db.conn() as c:
        before = c.execute("SELECT COALESCE(SUM(kg),0) k FROM pickups WHERE status='collected' AND collected_at IS NOT NULL AND substr(collected_at,1,10)<?", (start.isoformat(),)).fetchone()["k"]
        per_day = {r["d"]: r["k"] for r in c.execute("SELECT substr(collected_at,1,10) d, SUM(kg) k FROM pickups WHERE status='collected' AND collected_at IS NOT NULL AND substr(collected_at,1,10)>=? GROUP BY d", (start.isoformat(),))}
    labels, actual, projected, potential = [], [], [], []
    cum = float(before)
    for i in range(days_back):
        d = start + timedelta(days=i); cum += float(per_day.get(d.isoformat(), 0))
        labels.append(d.strftime("%d %b")); actual.append(round(cum, 1)); projected.append(round(cum, 1) if i == days_back - 1 else None); potential.append(None)
    actual_total = cum
    fut = _forecast_days([r["id"] for r in _donor_rows()], days_ahead, today + timedelta(days=1))
    for f in fut:
        cum += f["kg"] * rescue_rate
        labels.append(date.fromisoformat(f["date"]).strftime("%d %b")); actual.append(None); projected.append(round(cum, 1)); potential.append(f["kg"])
    extra = cum - actual_total
    return dict(labels=labels, actual=actual, projected=projected, potential_kg=potential, today_index=days_back - 1,
                summary=dict(horizon_days=days_ahead, rescue_rate=rescue_rate, potential_kg=round(sum(f["kg"] for f in fut), 1), rescued_kg_proj=round(extra, 1),
                             meals_est=round(extra * PORTIONS_PER_KG), co2e_kg_est=round(extra * CO2E_PER_KG_FOOD, 1)),
                observed=observed_rate(),
                note="Projection = model-forecast surplus across all donors x the rescue rate you choose. The rescue rate is an assumption, not a measured value; meals and CO2e use the placeholder factors in app/config.py.")

def _donor_rows():
    with db.conn() as c: return [dict(r) for r in c.execute("SELECT id FROM donors")]
