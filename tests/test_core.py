import os, tempfile, pytest
d = tempfile.mkdtemp(); os.environ["SURPLUS_DB"] = f"{d}/t.db"; os.environ["SURPLUS_MODEL"] = f"{d}/m.joblib"
from fastapi.testclient import TestClient
from app.main import app
from app.matching import haversine_km, rank_receivers
def test_haversine_zero_and_known():
    assert haversine_km(20,78,20,78) == 0
    assert 110 < haversine_km(0,0,1,0) < 112
def test_matching_excludes_unreachable_and_small_capacity():
    donor = dict(lat=20.0, lon=78.0)
    rs = [dict(id=1,name="near",lat=20.01,lon=78.0,capacity_kg=50,accept_rate=.8), dict(id=2,name="far",lat=21.0,lon=78.0,capacity_kg=50,accept_rate=.99), dict(id=3,name="tiny",lat=20.01,lon=78.0,capacity_kg=2,accept_rate=.9)]
    out = rank_receivers(donor, rs, kg=20, hours_left=1.0)
    assert [o["name"] for o in out] == ["near"]
def test_matching_prefers_closer_when_equal():
    donor = dict(lat=20.0, lon=78.0)
    rs = [dict(id=1,name="a",lat=20.05,lon=78.0,capacity_kg=50,accept_rate=.8), dict(id=2,name="b",lat=20.01,lon=78.0,capacity_kg=50,accept_rate=.8)]
    assert rank_receivers(donor, rs, 10, 3)[0]["name"] == "b"
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c: yield c
def test_model_beats_baseline_on_synthetic(client):
    m = client.get("/api/metrics").json()
    assert m["wape_model"] < m["wape_baseline"]
def test_forecast_and_validation(client):
    r = client.get("/api/forecast", params=dict(donor_id=1, meal="lunch", prepared=150, rain=1, event=0, day="2026-10-12"))
    assert r.status_code == 200 and 0 <= r.json()["low"] <= r.json()["portions"] <= r.json()["high"]
    assert client.get("/api/forecast", params=dict(donor_id=999, meal="lunch", prepared=150)).status_code == 404
    assert client.get("/api/forecast", params=dict(donor_id=1, meal="brunch", prepared=150)).status_code == 422
def test_log_validation(client):
    bad = dict(donor_id=1, day="2026-10-12", meal="lunch", prepared=10, sold=20)
    assert client.post("/api/logs", json=bad).status_code == 422
def test_full_flow_pickup_to_impact(client):
    m = client.post("/api/match", json=dict(donor_id=1, kg=20, hours_left=2)).json()
    assert m and m[0]["score"] >= m[-1]["score"]
    pid = client.post("/api/pickups", json=dict(donor_id=1, kg=20, hours_left=2, receiver_id=m[0]["receiver_id"])).json()["pickup_id"]
    assert client.post(f"/api/pickups/{pid}/status/collected").status_code == 200
    i = client.get("/api/impact").json()
    assert i["kg_rescued"] == 20 and i["meals_est"] == 50
def test_bad_status_rejected(client):
    assert client.post("/api/pickups/1/status/exploded").status_code == 422

# ---- chart / insight endpoints ----
def test_forecast_includes_what_if_drivers(client):
    r = client.get("/api/forecast", params=dict(donor_id=1, meal="dinner", prepared=140, day="2026-10-12")).json()
    assert set(r["drivers"]) == {"rain_effect", "event_effect"}
def test_week_forecast_shape(client):
    r = client.get("/api/forecast/week", params=dict(donor_id=2))
    assert r.status_code == 200
    days = r.json()["days"]
    assert len(days) == 7 and all(0 <= d["low"] <= d["portions"] <= d["high"] for d in days)
    assert client.get("/api/forecast/week", params=dict(donor_id=999)).status_code == 404
def test_backtest_and_importance(client):
    bt = client.get("/api/backtest").json()
    assert len(bt) > 5 and {"day", "actual", "pred", "baseline"} <= set(bt[0])
    assert len(client.get("/api/backtest", params=dict(donor_id=1)).json()) > 5
    imp = client.get("/api/importance").json()
    assert imp and abs(sum(i["importance"] for i in imp) - 100) < 1
def test_impact_series(client):
    s = client.get("/api/impact/series", params=dict(rescue_rate=0.6)).json()
    assert len(s["labels"]) == len(s["actual"]) == len(s["projected"]) == 14
    proj = [p for p in s["projected"] if p is not None]
    assert proj == sorted(proj) and s["summary"]["rescued_kg_proj"] > 0
    assert client.get("/api/impact/series", params=dict(rescue_rate=1.5)).status_code == 422
