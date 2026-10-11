from math import radians, sin, cos, asin, sqrt
from .config import TRAVEL_KMH, LOADING_HOURS
def haversine_km(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = radians(a_lat), radians(b_lat); dl = radians(b_lon-a_lon); dp = p2-p1
    h = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*6371*asin(sqrt(h))
def rank_receivers(donor, receivers, kg, hours_left):
    """Score = 0.40 proximity + 0.30 past acceptance + 0.20 capacity fit + 0.10 time margin.
    Receivers that cannot arrive inside hours_left, or have under half the needed capacity, are excluded."""
    out = []
    for r in receivers:
        dist = haversine_km(donor["lat"], donor["lon"], r["lat"], r["lon"])
        eta = dist/TRAVEL_KMH + LOADING_HOURS
        if eta > hours_left or r["capacity_kg"] < 0.5*kg: continue
        prox = max(0.0, 1 - dist/15.0)
        cap = min(1.0, r["capacity_kg"]/kg) if kg > 0 else 1.0
        margin = min(1.0, (hours_left-eta)/hours_left)
        score = .40*prox + .30*r["accept_rate"] + .20*cap + .10*margin
        out.append(dict(receiver_id=r["id"], name=r["name"], distance_km=round(dist,2), eta_hours=round(eta,2), score=round(score,3),
                        why=f"{dist:.1f} km away, reachable in {eta*60:.0f} min, accepts {r['accept_rate']*100:.0f}% of requests, capacity {r['capacity_kg']:.0f} kg"))
    return sorted(out, key=lambda x: -x["score"])
