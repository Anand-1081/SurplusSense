import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import db, ml, synth, matching, insights
from .config import KG_PER_PORTION, PORTIONS_PER_KG, CO2E_PER_KG_FOOD
@asynccontextmanager
async def lifespan(app):
    db.init()
    with db.conn() as c: synth.seed(c)
    if not ml.model_ready(): ml.train()
    yield
app = FastAPI(title="SurplusSense MVP", lifespan=lifespan)
class LogIn(BaseModel):
    donor_id: int; day: str; meal: str = Field(pattern="^(lunch|dinner)$"); prepared: float = Field(gt=0); sold: float = Field(ge=0); rain: int = 0; event: int = 0
class MatchIn(BaseModel):
    donor_id: int; kg: float = Field(gt=0); hours_left: float = Field(gt=0, le=12)
class PickupIn(MatchIn):
    receiver_id: int
@app.get("/api/donors")
def donors():
    with db.conn() as c: return [dict(r) for r in c.execute("SELECT * FROM donors")]
@app.get("/api/receivers")
def receivers():
    with db.conn() as c: return [dict(r) for r in c.execute("SELECT * FROM receivers")]
@app.post("/api/logs")
def add_log(l: LogIn):
    if l.sold > l.prepared: raise HTTPException(422, "sold cannot exceed prepared")
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM donors WHERE id=?", (l.donor_id,)).fetchone(): raise HTTPException(404, "donor not found")
        c.execute("INSERT INTO logs(donor_id,day,meal,prepared,sold,surplus,rain,event) VALUES(?,?,?,?,?,?,?,?)", (l.donor_id,l.day,l.meal,l.prepared,l.sold,l.prepared-l.sold,l.rain,l.event))
    return {"ok": True, "surplus": l.prepared-l.sold}
@app.post("/api/train")
def train(): return ml.train()
@app.get("/api/metrics")
def metrics(): return ml.metrics()
@app.get("/api/forecast")
def forecast(donor_id: int, meal: str, prepared: float, rain: int = 0, event: int = 0, day: str = None):
    if meal not in ("lunch","dinner") or prepared <= 0: raise HTTPException(422, "bad meal or prepared")
    day = day or datetime.now().strftime("%Y-%m-%d")
    try: f = ml.forecast(donor_id, meal, prepared, rain, event, day)
    except KeyError: raise HTTPException(404, "donor not found")
    f.update(kg=round(f["portions"]*KG_PER_PORTION,1), kg_low=round(f["low"]*KG_PER_PORTION,1), kg_high=round(f["high"]*KG_PER_PORTION,1))
    f["drivers"] = ml.drivers(donor_id, meal, prepared, rain, event, day); return f
@app.get("/api/forecast/week")
def forecast_week(donor_id: int):
    try: return insights.week_forecast(donor_id, 7)
    except KeyError: raise HTTPException(404, "donor not found")
    except ValueError as e: raise HTTPException(422, str(e))
@app.get("/api/backtest")
def backtest(donor_id: int = None): return insights.backtest(donor_id)
@app.get("/api/importance")
def importance(): return insights.importance()
@app.get("/api/impact/series")
def impact_series(rescue_rate: float = 0.5, days_ahead: int = 7):
    if not 0 <= rescue_rate <= 1 or not 1 <= days_ahead <= 14: raise HTTPException(422, "rescue_rate must be 0-1 and days_ahead 1-14")
    return insights.impact_series(days_ahead=days_ahead, rescue_rate=rescue_rate)
@app.post("/api/match")
def match(m: MatchIn):
    with db.conn() as c:
        d = c.execute("SELECT * FROM donors WHERE id=?", (m.donor_id,)).fetchone()
        if not d: raise HTTPException(404, "donor not found")
        rs = [dict(r) for r in c.execute("SELECT * FROM receivers")]
    return matching.rank_receivers(dict(d), rs, m.kg, m.hours_left)
@app.post("/api/pickups")
def create_pickup(p: PickupIn):
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM receivers WHERE id=?", (p.receiver_id,)).fetchone(): raise HTTPException(404, "receiver not found")
        cur = c.execute("INSERT INTO pickups(donor_id,receiver_id,kg,status,created_at,hours_left) VALUES(?,?,?,?,?,?)", (p.donor_id,p.receiver_id,p.kg,"requested",datetime.now().isoformat(timespec="seconds"),p.hours_left))
    return {"pickup_id": cur.lastrowid, "status": "requested"}
@app.get("/api/pickups")
def pickups():
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT p.*, d.name donor, r.name receiver FROM pickups p JOIN donors d ON d.id=p.donor_id JOIN receivers r ON r.id=p.receiver_id ORDER BY p.id DESC LIMIT 20")]
@app.post("/api/pickups/{pid}/status/{status}")
def set_status(pid: int, status: str):
    if status not in ("accepted","declined","collected"): raise HTTPException(422, "bad status")
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM pickups WHERE id=?", (pid,)).fetchone(): raise HTTPException(404, "pickup not found")
        c.execute("UPDATE pickups SET status=?, collected_at=? WHERE id=?", (status, datetime.now().isoformat(timespec="seconds") if status=="collected" else None, pid))
    return {"ok": True}
@app.get("/api/impact")
def impact():
    with db.conn() as c:
        r = c.execute("SELECT COUNT(*) n, COALESCE(SUM(kg),0) kg FROM pickups WHERE status='collected'").fetchone()
        t = c.execute("SELECT COUNT(*) n FROM pickups").fetchone()["n"]
    kg = r["kg"]
    return dict(collected_pickups=r["n"], total_pickups=t, kg_rescued=round(kg,1), meals_est=round(kg*PORTIONS_PER_KG), co2e_kg_est=round(kg*CO2E_PER_KG_FOOD,1),
                note="Meals and CO2e use placeholder conversion factors in app/config.py")
HERE = os.path.dirname(__file__)
@app.get("/")
def home(): return FileResponse(os.path.join(HERE, "static", "index.html"))
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
