import sqlite3, os
from . import config
SCHEMA = """
CREATE TABLE IF NOT EXISTS donors(id INTEGER PRIMARY KEY, name TEXT, dtype TEXT, lat REAL, lon REAL, synthetic INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS receivers(id INTEGER PRIMARY KEY, name TEXT, lat REAL, lon REAL, capacity_kg REAL, accept_rate REAL);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, donor_id INT, day TEXT, meal TEXT, prepared REAL, sold REAL, surplus REAL, rain INT, event INT, synthetic INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS pickups(id INTEGER PRIMARY KEY, donor_id INT, receiver_id INT, kg REAL, status TEXT, created_at TEXT, hours_left REAL, collected_at TEXT);
"""
def conn():
    d = os.path.dirname(config.DB_PATH)
    if d: os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH); c.row_factory = sqlite3.Row
    return c
def init():
    with conn() as c: c.executescript(SCHEMA)
