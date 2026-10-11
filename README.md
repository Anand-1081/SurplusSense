# SurplusSense (MVP prototype)
Predict surplus. Redistribute before it spoils. An ML forecaster plus a scored receiver matcher for surplus cooked food.

## Run (Python-only screen, recommended)
    pip install -r requirements.txt
    streamlit run streamlit_app.py     # opens http://localhost:8501

No JavaScript and no separate server: `streamlit_app.py` uses the same `app/` code (model, matching, database) directly. Free public link: push the folder to GitHub and deploy it on Streamlit Community Cloud (share.streamlit.io), main file `streamlit_app.py`.

## Run (FastAPI + Material UI screen)
    pip install -r requirements.txt
    uvicorn app.main:app --reload      # open http://127.0.0.1:8000
    pytest -q                          # run tests

First start creates `data/` with a SQLite DB, loads **synthetic** demo donors/receivers/logs, and trains the model.

## UI
Material UI (React) + Chart.js, loaded from a CDN in `app/static/index.html`, so the browser needs internet access. No Node build step: `app/static/app.jsx` is compiled in the browser by Babel. Four tabs: Forecast, Redistribute, Impact, Model. Buttons have a press animation (ripple, squash on click, spinner while a request runs). Logo: `app/static/logo.svg`.

## Graphs and ML in the UI
- **Next 7 days** (`GET /api/forecast/week`): predicted surplus per day with an 80% range band.
- **What-if drivers** (in `GET /api/forecast`): the same model re-run with rain and event toggled, so you see how many portions each adds.
- **Impact: actual and forecast** (`GET /api/impact/series`): cumulative kg rescued from collected pickups, then a projection = model-forecast surplus across all donors x a rescue rate you choose with a slider.
- **Actual vs predicted** (`GET /api/backtest`): out-of-sample days only (the time-held-out 20%), model vs the same-weekday baseline.
- **What drives surplus** (`GET /api/importance`): permutation importance on the held-out rows.
- Match score bars and a pickup-status doughnut.

## What it does
1. **Forecast** (`GET /api/forecast`): gradient-boosted regression (scikit-learn) predicts leftover portions plus an 80% range (quantile models). Features: donor type, weekday, meal, portions prepared, rain, event, 7-log surplus average. Evaluated on a time-based split against a same-weekday-average baseline (`GET /api/metrics`).
2. **Match** (`POST /api/match`): scores receivers by proximity, past acceptance, capacity fit and time margin; excludes receivers that cannot arrive within the safe window.
3. **Pickups** (`/api/pickups`): request, accept, mark collected.
4. **Impact** (`GET /api/impact`): kg, estimated meals and CO2e from collected pickups.

## Honest status
- Verified: unit and API tests pass in the build sandbox (see `pytest`).
- The rescue rate on the Impact slider is an assumption (default 50%), not a measured value. The UI shows the measured rate once pickups exist.
- The weekly forecast assumes no rain/event and each donor's recent average portions prepared; its range is the sum of per-meal 10th to 90th percentiles, so it is conservative.
- NOT real: all data is synthetic. Model scores prove the pipeline works, not real accuracy.
- Placeholders to replace: `KG_PER_PORTION`, `CO2E_PER_KG_FOOD` in `app/config.py`; safe-window hours are entered by the user and are not food-safety advice.
- Differences from the slides: SQLite instead of PostgreSQL/PostGIS, a CDN-loaded React/MUI UI instead of a Next.js build, no WhatsApp or LLM integration, no authentication yet. These are next steps.

## Next steps
Auth and roles, Postgres + PostGIS, WhatsApp notifications, real pilot logs, retraining schedule, drift monitoring.

## Deploy (share a public link)
The app needs a Python server (FastAPI + scikit-learn), so it must go on a host that runs Python. Easiest free route is Render:
1. Put this folder in a GitHub repository.
2. On render.com choose New > Blueprint (or New > Web Service > Docker) and pick the repo. `render.yaml` and `Dockerfile` are already set up.
3. When the build finishes, Render gives you a public `https://...onrender.com` link.

Hugging Face Spaces (Docker) also works with the same `Dockerfile`.

Notes: on free tiers the app sleeps when idle (first load takes about 30 seconds), and the SQLite database and model are recreated on every restart, so pickups you create are not kept. There is no login, so anyone with the link can create pickups or press Retrain; add authentication before using real data.
