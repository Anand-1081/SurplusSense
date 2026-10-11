import os
DB_PATH = os.environ.get("SURPLUS_DB", "data/surplussense.db")
MODEL_PATH = os.environ.get("SURPLUS_MODEL", "data/model.joblib")
# ASSUMPTIONS (placeholders, replace with sourced values before reporting impact)
KG_PER_PORTION = 0.4        # average cooked portion weight
PORTIONS_PER_KG = 1 / KG_PER_PORTION
CO2E_PER_KG_FOOD = 2.5      # kg CO2e avoided per kg food rescued (placeholder assumption)
TRAVEL_KMH = 20.0           # average pickup speed in city traffic
LOADING_HOURS = 0.25        # time to pack and hand over
