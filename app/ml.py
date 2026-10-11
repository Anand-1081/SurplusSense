import numpy as np, pandas as pd, joblib, os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from . import config
from .db import conn
DT = {"restaurant":0,"hostel":1,"caterer":2,"canteen":3}; MEAL = {"lunch":0,"dinner":1}
FEATS = ["dtype","wd","meal","prepared","rain","event","lag7"]

# ---- model cache: reload from disk only when the file changes ----
_CACHE = {"key": None, "obj": None}
def _load():
    p = config.MODEL_PATH
    if not os.path.exists(p): return None
    key = (p, os.path.getmtime(p))
    if _CACHE["key"] != key:
        _CACHE.update(key=key, obj=joblib.load(p))
    return _CACHE["obj"]

def load_frame():
    with conn() as c:
        return pd.read_sql("SELECT l.*, d.dtype FROM logs l JOIN donors d ON d.id=l.donor_id", c)
def featurize(df):
    df = df.sort_values(["donor_id","meal","day"]).copy()
    df["lag7"] = df.groupby(["donor_id","meal"])["surplus"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    df = df.dropna(subset=["lag7"]).copy()
    df["wd"] = pd.to_datetime(df["day"]).dt.weekday
    df["dtype"] = df["dtype"].map(DT); df["meal"] = df["meal"].map(MEAL)
    return df
def wape(y, p): return float(np.abs(y-p).sum()/max(np.abs(y).sum(),1e-9))
def _mk(**k): return GradientBoostingRegressor(random_state=0, n_estimators=200, max_depth=3, learning_rate=.05, **k)

def train():
    df = featurize(load_frame())
    if len(df) < 100: raise ValueError("need at least 100 log rows to train")
    days = sorted(df["day"].unique()); cut = days[int(len(days)*.8)]
    tr, te = df[df.day < cut], df[df.day >= cut]          # time-based split, no shuffling
    base = tr.groupby(["donor_id","meal","wd"])["surplus"].mean()   # naive baseline: same donor, meal, weekday
    bp = te.apply(lambda r: base.get((r.donor_id, r.meal, r.wd), tr["surplus"].mean()), axis=1)
    mid_t = _mk().fit(tr[FEATS], tr["surplus"]); lo_t = _mk(loss="quantile", alpha=.1).fit(tr[FEATS], tr["surplus"]); hi_t = _mk(loss="quantile", alpha=.9).fit(tr[FEATS], tr["surplus"])
    p, plo, phi = mid_t.predict(te[FEATS]), lo_t.predict(te[FEATS]), hi_t.predict(te[FEATS])
    cover = float(((te["surplus"] >= plo) & (te["surplus"] <= phi)).mean())
    m = dict(rows=len(df), test_rows=len(te), wape_model=round(wape(te["surplus"], p),4), wape_baseline=round(wape(te["surplus"], bp),4),
             mae_model=round(float(np.abs(te["surplus"]-p).mean()),2), mae_baseline=round(float(np.abs(te["surplus"]-bp).mean()),2), interval_coverage_80=round(cover,3),
             note="Scored on the time-held-out last 20% of logs. If the logs are synthetic, this only shows the code works.")

    # Explainability: permutation importance on the held-out rows (how much accuracy drops when a feature is shuffled).
    imp = permutation_importance(mid_t, te[FEATS], te["surplus"], n_repeats=5, random_state=0)
    raw = np.clip(imp.importances_mean, 0, None); tot = float(raw.sum())
    importance = {f: (round(float(v)/tot*100, 1) if tot > 0 else 0.0) for f, v in zip(FEATS, raw)}

    # Out-of-sample predictions kept for the "actual vs predicted" chart.
    inv = {v: k for k, v in MEAL.items()}
    bt = pd.DataFrame(dict(day=te["day"].values, donor_id=te["donor_id"].values, meal=te["meal"].map(inv).values,
                           actual=te["surplus"].values, pred=np.maximum(p, 0), lo=np.maximum(plo, 0), hi=np.maximum(phi, 0), baseline=np.asarray(bp, dtype=float)))
    backtest = bt.round(2).to_dict("records")

    # Final models use all data.
    mid = _mk().fit(df[FEATS], df["surplus"]); lo = _mk(loss="quantile", alpha=.1).fit(df[FEATS], df["surplus"]); hi = _mk(loss="quantile", alpha=.9).fit(df[FEATS], df["surplus"])
    os.makedirs(os.path.dirname(config.MODEL_PATH) or ".", exist_ok=True)
    joblib.dump(dict(mid=mid, lo=lo, hi=hi, metrics=m, importance=importance, backtest=backtest), config.MODEL_PATH)
    _CACHE["key"] = None
    return m

def model_ready():
    M = _load()
    return M is not None and "backtest" in M      # older model files without the new fields get retrained
def metrics():
    M = _load(); return M["metrics"] if M else None

def forecast_batch(items):
    """items: list of dict(donor_id, meal, prepared, rain, event, day). One model call for the whole list."""
    M = _load()
    if M is None: raise RuntimeError("model not trained")
    rows, used, dtypes = [], [], {}
    with conn() as c:
        for it in items:
            did = it["donor_id"]
            if did not in dtypes:
                d = c.execute("SELECT dtype FROM donors WHERE id=?", (did,)).fetchone()
                if not d: raise KeyError("donor not found")
                dtypes[did] = d["dtype"]
            hist = c.execute("SELECT surplus FROM logs WHERE donor_id=? AND meal=? AND day<? ORDER BY day DESC LIMIT 7", (did, it["meal"], it["day"])).fetchall()
            lag = float(np.mean([r["surplus"] for r in hist])) if hist else 0.15*it["prepared"]
            used.append(len(hist))
            rows.append([DT[dtypes[did]], pd.Timestamp(it["day"]).weekday(), MEAL[it["meal"]], it["prepared"], it["rain"], it["event"], lag])
    X = pd.DataFrame(rows, columns=FEATS)
    mid, lo, hi = (np.maximum(M[k].predict(X), 0.0) for k in ("mid","lo","hi"))
    return [dict(portions=round(float(mid[i]),1), low=round(float(min(lo[i],mid[i])),1), high=round(float(max(hi[i],mid[i])),1), used_history_rows=used[i]) for i in range(len(items))]

def forecast(donor_id, meal, prepared, rain, event, day):
    return forecast_batch([dict(donor_id=donor_id, meal=meal, prepared=prepared, rain=rain, event=event, day=day)])[0]

def drivers(donor_id, meal, prepared, rain, event, day):
    """What-if analysis with the same model: how many portions do rain / an event add, holding everything else fixed?"""
    r = forecast_batch([dict(donor_id=donor_id, meal=meal, prepared=prepared, rain=rr, event=ee, day=day)
                        for rr, ee in ((0, event), (1, event), (rain, 0), (rain, 1))])
    return dict(rain_effect=round(r[1]["portions"]-r[0]["portions"], 1), event_effect=round(r[3]["portions"]-r[2]["portions"], 1))
