"""Synthetic data so the pipeline can run before real pilot data exists.
It is NOT real data: model scores on it only prove the code works."""
import numpy as np, pandas as pd
DONORS = [("Sunrise Hostel Mess","hostel",20.010,78.010),("Spice Garden Restaurant","restaurant",20.025,78.030),("Grand Banquet Hall","caterer",19.990,78.020),
          ("Tech Park Canteen","canteen",20.040,78.000),("City Cafe","restaurant",20.005,77.985),("Green Valley Mess","hostel",20.030,78.050)]
RECEIVERS = [("Asha Community Kitchen",20.015,78.015,60,0.9),("Hope Shelter",20.050,78.040,40,0.7),("Seva Trust",19.985,78.000,120,0.8),("Annapurna Kitchen",20.035,78.025,80,0.6),("Old Age Home Care",20.000,78.060,30,0.95)]
def make_logs(n_days=150, seed=7):
    rng = np.random.default_rng(seed); rows = []
    days = pd.date_range("2026-04-01", periods=n_days)
    for di, (_, dt, _, _) in enumerate(DONORS):
        base = {"hostel":150,"restaurant":90,"caterer":220,"canteen":180}[dt] * rng.uniform(.8,1.2)
        for d in days:
            wd = d.weekday()
            for meal, mf in (("lunch",1.0),("dinner",0.9)):
                rain = int(rng.random() < .2); event = int(rng.random() < .08)
                prep = base*mf*(1+rng.normal(0,.05))*(1.15 if event else 1)
                rate = .82 + .05*(wd>=5) - .10*rain - .15*event + (.04 if dt=="restaurant" and wd>=4 else 0) + rng.normal(0,.03)
                sold = float(np.clip(prep*rate, 0, prep))
                rows.append(dict(donor_id=di+1, day=d.strftime("%Y-%m-%d"), meal=meal, prepared=round(prep,1), sold=round(sold,1), surplus=round(prep-sold,1), rain=rain, event=event))
    return rows

def seed(c):
    """Insert demo donors, receivers and logs if the donors table is empty. `c` is an open sqlite connection."""
    if c.execute("SELECT COUNT(*) FROM donors").fetchone()[0] != 0:
        return False
    for n, t, la, lo in DONORS:
        c.execute("INSERT INTO donors(name,dtype,lat,lon,synthetic) VALUES(?,?,?,?,1)", (n, t, la, lo))
    for n, la, lo, cap, ar in RECEIVERS:
        c.execute("INSERT INTO receivers(name,lat,lon,capacity_kg,accept_rate) VALUES(?,?,?,?,?)", (n, la, lo, cap, ar))
    c.executemany("INSERT INTO logs(donor_id,day,meal,prepared,sold,surplus,rain,event,synthetic) VALUES(?,?,?,?,?,?,?,?,1)",
                  [(r["donor_id"], r["day"], r["meal"], r["prepared"], r["sold"], r["surplus"], r["rain"], r["event"]) for r in make_logs()])
    return True
