"""SurplusSense: pure-Python UI (Streamlit + Plotly). Run from this folder:  streamlit run streamlit_app.py
Uses the same model, matching and database code as the FastAPI version (no JavaScript, no web server to start)."""
import base64
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

from app import db, ml, synth, matching, insights
from app.config import KG_PER_PORTION, PORTIONS_PER_KG, CO2E_PER_KG_FOOD

GREEN, LEAF, AMBER, RED, INK, MUTED = "#1F5F4A", "#2E8B6A", "#F2A33A", "#C8553D", "#17332B", "#5B6B65"

st.set_page_config(page_title="SurplusSense", page_icon="🌿", layout="wide")


@st.cache_resource(show_spinner="Setting up demo data and training the model (first run only)...")
def boot():
    db.init()
    with closing(db.conn()) as c:
        synth.seed(c); c.commit()
    if not ml.model_ready():
        ml.train()
    return True


boot()


# ---------------- small data helpers ----------------
def q(sql, args=()):
    with closing(db.conn()) as c:
        return [dict(r) for r in c.execute(sql, args)]


def run(sql, args=()):
    with closing(db.conn()) as c:
        cur = c.execute(sql, args); c.commit()
        return cur.lastrowid


# ---------------- look and feel: logo, Material-style cards, button press animation ----------------
LOGO = Path(__file__).parent / "app" / "static" / "logo.svg"
logo_uri = "data:image/svg+xml;base64," + base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""

st.markdown("""
<style>
  .block-container{padding-top:1.2rem;max-width:1150px}
  .ss-header{display:flex;align-items:center;gap:16px;padding:18px 24px;border-radius:18px;margin-bottom:14px;
             background:linear-gradient(135deg,#0F2A22,#1F5F4A);color:#fff;box-shadow:0 6px 20px rgba(15,42,34,.25)}
  .ss-header img{width:56px;height:56px;transition:transform .35s cubic-bezier(.3,1.6,.5,1)}
  .ss-header:hover img{transform:rotate(-8deg) scale(1.1)}
  .ss-title{font-size:30px;font-weight:700;line-height:1.1}.ss-title span{color:#F2A33A}
  .ss-tag{opacity:.85;font-size:14px}
  /* buttons: lift on hover, squash on press */
  .stButton>button{border-radius:12px;font-weight:600;border:0;transition:transform .12s ease,box-shadow .2s ease,background-color .2s ease}
  .stButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(31,95,74,.28)}
  .stButton>button:active{transform:translateY(1px) scale(.94);box-shadow:inset 0 1px 3px rgba(0,0,0,.25)}
  div[data-testid="stMetric"]{background:linear-gradient(180deg,#fff,#F1F7F3);border:1px solid #d3e0d7;border-radius:14px;padding:12px 16px;
             transition:transform .2s ease,box-shadow .2s ease}
  div[data-testid="stMetric"]:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(23,51,43,.1)}
  button[role="tab"]{font-weight:600}
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="ss-header"><img src="{logo_uri}" alt="SurplusSense logo">
  <div><div class="ss-title">Surplus<span>Sense</span></div><div class="ss-tag">Predict surplus. Redistribute before it spoils.</div></div></div>
""", unsafe_allow_html=True)


def style(fig, ytitle, height=340):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.22),
                      yaxis_title=ytitle, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ---------------- shared selection ----------------
donors = q("SELECT * FROM donors")
names = {d["id"]: d["name"] for d in donors}
st.session_state.setdefault("kg", 10.0)
st.session_state.setdefault("hours", 2.0)

with st.sidebar:
    st.markdown("### Donor")
    st.selectbox("Choose a donor", list(names), format_func=lambda i: names[i], key="donor_id", label_visibility="collapsed")
    st.warning("Prototype on **synthetic demo data**. Accuracy shown proves the code works, not real-world performance.")
donor_id = st.session_state.donor_id

tab_fc, tab_match, tab_impact, tab_model = st.tabs(["📈 Forecast", "🤝 Redistribute", "🌍 Impact", "🧠 Model"])


# ================= FORECAST =================
def do_forecast():
    did, meal = st.session_state.donor_id, st.session_state.meal
    prep = float(st.session_state[f"prep_{did}_{meal}"])
    rain, event, day = int(st.session_state.rain), int(st.session_state.event), date.today().isoformat()
    f = ml.forecast(did, meal, prep, rain, event, day)
    f["drivers"] = ml.drivers(did, meal, prep, rain, event, day)
    f.update(kg=round(f["portions"] * KG_PER_PORTION, 1), kg_low=round(f["low"] * KG_PER_PORTION, 1), kg_high=round(f["high"] * KG_PER_PORTION, 1), key=(did, meal))
    st.session_state.fc = f
    st.session_state.kg = max(0.5, float(f["kg"]))     # pre-fills the Redistribute tab


with tab_fc:
    left, right = st.columns([5, 7], gap="large")
    week, week_err = None, None
    try:
        week = insights.week_forecast(donor_id)
    except ValueError as e:
        week_err = str(e)
    with left:
        st.subheader("Forecast surplus")
        st.selectbox("Meal", ["lunch", "dinner"], key="meal")
        meal = st.session_state.meal
        default_prep = float(week["prepared_assumed"][meal]) if week else 100.0
        st.number_input("Portions prepared", min_value=1.0, value=default_prep, step=1.0, key=f"prep_{donor_id}_{meal}")
        c1, c2 = st.columns(2)
        c1.checkbox("Rain", key="rain"); c2.checkbox("Event nearby", key="event")
        st.button("Run forecast", type="primary", key="run_fc", on_click=do_forecast)
        fc = st.session_state.get("fc")
        if fc and fc["key"] == (donor_id, meal):
            m1, m2 = st.columns(2)
            m1.metric("Portions left over", f"{fc['portions']:.0f}", f"range {fc['low']:.0f} to {fc['high']:.0f}", delta_color="off")
            m2.metric("Food to rescue", f"{fc['kg']} kg", f"{fc['kg_low']} to {fc['kg_high']} kg", delta_color="off")
            d = fc["drivers"]
            st.caption(f"What-if from the same model: rain changes surplus by {d['rain_effect']:+.1f} portions, a nearby event by {d['event_effect']:+.1f}.")
            st.info(f"{fc['kg']} kg is pre-filled in the Redistribute tab.")
    with right:
        st.subheader("Next 7 days: predicted surplus")
        if week_err:
            st.warning(week_err)
        else:
            days = week["days"]; x = [r["label"] for r in days]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x, y=[r["low"] for r in days], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=x, y=[r["high"] for r in days], mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(46,139,106,.2)", name="Likely range (80%)", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=x, y=[r["portions"] for r in days], mode="lines+markers", line=dict(color=GREEN, width=3, shape="spline"), marker=dict(size=9), name="Forecast surplus (portions)"))
            st.plotly_chart(style(fig, "Portions left over (lunch + dinner)", 360))
            st.caption(week["note"])


# ================= REDISTRIBUTE =================
def find():
    did = st.session_state.donor_id
    donor = q("SELECT * FROM donors WHERE id=?", (did,))[0]
    st.session_state.matches = dict(donor=did, items=matching.rank_receivers(donor, q("SELECT * FROM receivers"), float(st.session_state.kg), float(st.session_state.hours)))


def request_pickup(receiver_id):
    run("INSERT INTO pickups(donor_id,receiver_id,kg,status,created_at,hours_left) VALUES(?,?,?,?,?,?)",
        (st.session_state.donor_id, receiver_id, float(st.session_state.kg), "requested", datetime.now().isoformat(timespec="seconds"), float(st.session_state.hours)))
    st.toast("Pickup requested", icon="✅")


def set_status(pid, status):
    run("UPDATE pickups SET status=?, collected_at=? WHERE id=?", (status, datetime.now().isoformat(timespec="seconds") if status == "collected" else None, pid))


with tab_match:
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Find the best receiver")
        a, b = st.columns(2)
        a.number_input("Food to give (kg)", min_value=0.5, step=0.5, key="kg")
        b.number_input("Hours left (safe window)", min_value=0.5, max_value=12.0, step=0.5, key="hours")
        st.button("Find receivers", type="primary", key="find", on_click=find)
        st.caption("Safe-window hours are entered by the donor; follow your food-safety guidance.")
        mt = st.session_state.get("matches")
        if mt and mt["donor"] == donor_id:
            if not mt["items"]:
                st.info("No receiver can reach in time. Try a longer window or a smaller quantity.")
            for i, m in enumerate(mt["items"]):
                with st.container(border=True):
                    st.markdown(f"**{m['name']}**" + ("  ⭐ best match" if i == 0 else ""))
                    st.progress(min(1.0, max(0.0, m["score"])), text=f"Match score {round(m['score'] * 100)}%")
                    st.caption(m["why"])
                    st.button("Request pickup", key=f"req_{m['receiver_id']}", on_click=request_pickup, args=(m["receiver_id"],))
    with right:
        st.subheader("Pickups")
        pk = q("SELECT p.*, d.name donor, r.name receiver FROM pickups p JOIN donors d ON d.id=p.donor_id JOIN receivers r ON r.id=p.receiver_id ORDER BY p.id DESC LIMIT 20")
        if not pk:
            st.info("No pickups yet. Request one from a matched receiver.")
        colors = {"requested": "orange", "accepted": "blue", "collected": "green", "declined": "red"}
        for p in pk:
            with st.container(border=True):
                st.markdown(f"**{p['donor']}** → **{p['receiver']}** · {p['kg']} kg · :{colors.get(p['status'], 'gray')}[{p['status']}]")
                cols = st.columns(3)
                if p["status"] == "requested":
                    cols[0].button("Accept", key=f"acc_{p['id']}", on_click=set_status, args=(p["id"], "accepted"))
                    cols[1].button("Decline", key=f"dec_{p['id']}", on_click=set_status, args=(p["id"], "declined"))
                if p["status"] in ("requested", "accepted"):
                    cols[2].button("Collected", key=f"col_{p['id']}", on_click=set_status, args=(p["id"], "collected"))


# ================= IMPACT =================
with tab_impact:
    r = q("SELECT COUNT(*) n, COALESCE(SUM(kg),0) kg FROM pickups WHERE status='collected'")[0]
    total = q("SELECT COUNT(*) n FROM pickups")[0]["n"]
    kg_done = float(r["kg"])
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("kg rescued", f"{kg_done:.1f}")
    k2.metric("Meals (est.)", f"{round(kg_done * PORTIONS_PER_KG)}")
    k3.metric("CO2e avoided kg (est.)", f"{kg_done * CO2E_PER_KG_FOOD:.1f}")
    k4.metric("Pickups done", f"{r['n']} / {total}")

    left, right = st.columns([8, 4], gap="large")
    with left:
        st.subheader("Impact: actual and forecast")
        rate = st.slider("Rescue rate assumption (% of forecast surplus that gets collected)", 0, 100, 50, 5, key="rate")
        s = insights.impact_series(rescue_rate=rate / 100)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=s["labels"], y=s["potential_kg"], name="Forecast surplus available (kg/day)", marker_color="rgba(46,139,106,.28)"))
        fig.add_trace(go.Scatter(x=s["labels"], y=s["actual"], mode="lines+markers", name="Actual rescued (cumulative kg)", line=dict(color=GREEN, width=3), connectgaps=False))
        fig.add_trace(go.Scatter(x=s["labels"], y=s["projected"], mode="lines+markers", name="Projected (ML forecast x rescue rate)", line=dict(color=AMBER, width=3, dash="dash"), connectgaps=False))
        st.plotly_chart(style(fig, "kg of food", 380))
        obs = s["observed"]
        st.caption(("No pickups recorded yet, so there is no measured rescue rate. " if obs["rate"] is None else f"Pickups collected so far: {round(obs['rate'] * 100)}% of {obs['pickups']} requested. ") + s["note"])
    with right:
        sm = s["summary"]
        st.subheader(f"Next {sm['horizon_days']} days")
        st.metric("Surplus forecast", f"{sm['potential_kg']} kg")
        st.metric("Meals if rescued (est.)", f"{sm['meals_est']}")
        st.metric("CO2e avoided kg (est.)", f"{sm['co2e_kg_est']}")
        st.subheader("Pickup status")
        statuses = ["requested", "accepted", "collected", "declined"]
        counts = [q("SELECT COUNT(*) n FROM pickups WHERE status=?", (x,))[0]["n"] for x in statuses]
        if sum(counts):
            pie = go.Figure(go.Pie(labels=statuses, values=counts, hole=0.6, marker=dict(colors=[AMBER, "#4C9BC9", LEAF, RED])))
            pie.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h"))
            st.plotly_chart(pie)
        else:
            st.info("Pickups will appear here.")


# ================= MODEL =================
with tab_model:
    met = ml.metrics()
    if met:
        better = round((1 - met["wape_model"] / met["wape_baseline"]) * 100)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Model error (WAPE)", f"{met['wape_model'] * 100:.1f}%", "lower is better", delta_color="off")
        m2.metric("Baseline error", f"{met['wape_baseline'] * 100:.1f}%", "same-weekday average", delta_color="off")
        m3.metric("Error reduction", f"{better}%", "vs baseline", delta_color="off")
        m4.metric("80% range coverage", f"{met['interval_coverage_80'] * 100:.0f}%", "target is 80%", delta_color="off")
    left, right = st.columns([7, 5], gap="large")
    with left:
        st.subheader("Actual vs predicted (held-out days)")
        pick = st.selectbox("Donor filter", ["all"] + list(names), format_func=lambda i: "All donors" if i == "all" else names[i], key="bt_filter")
        bt = insights.backtest(None if pick == "all" else pick)
        fig = go.Figure()
        x = [d["day"][5:] for d in bt]
        fig.add_trace(go.Scatter(x=x, y=[d["actual"] for d in bt], name="Actual surplus", line=dict(color=INK, width=3)))
        fig.add_trace(go.Scatter(x=x, y=[d["pred"] for d in bt], name="ML model", line=dict(color=LEAF, width=3)))
        fig.add_trace(go.Scatter(x=x, y=[d["baseline"] for d in bt], name="Simple baseline (same weekday average)", line=dict(color="#9AA8A1", width=2, dash="dash")))
        st.plotly_chart(style(fig, "Portions left over per day", 360))
        st.caption("These days were never used for training, so the gap between the lines is honest out-of-sample error.")
    with right:
        st.subheader("What drives surplus?")
        imp = insights.importance()
        bar = go.Figure(go.Bar(x=[i["importance"] for i in imp], y=[i["label"] for i in imp], orientation="h", marker_color=[GREEN, LEAF] + ["#8CC3AC"] * max(0, len(imp) - 2)))
        bar.update_layout(template="plotly_white", height=360, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="% importance (permutation, held-out data)", yaxis=dict(autorange="reversed"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(bar)
    st.subheader("About the model")
    st.write("Gradient-boosted regression (scikit-learn) predicts leftover portions, plus two quantile models for the 80% range. "
             "Features: donor type, weekday, meal, portions prepared, rain, event and the last 7 logs' average surplus. " + (met["note"] if met else ""))
    if st.button("Retrain model", type="primary", key="retrain"):
        with st.spinner("Training..."):
            ml.train()
        st.rerun()
