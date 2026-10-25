"""The UnderCover database: SQLite, seeded from data/."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_DB = Path(__file__).resolve().parent / "undercover.db"

SEED_FILES = (
    "claims.json",
    "policies.json",
    "customers.json",
    "plans.json",
    "company.json",
    "handlers.json",
    "policy_wording.md",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    thread_id TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (
    claim_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    reasons TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    signed_off_by TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    claim_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    """Return the database file, from UNDERCOVER_DB or the default."""
    return Path(os.getenv("UNDERCOVER_DB", str(DEFAULT_DB)))


def connect() -> sqlite3.Connection:
    """Open a connection to the database."""
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def load(name: str) -> str:
    """Read one of the seed files from data/."""
    return (DATA_DIR / name).read_text(encoding="utf-8")


def init() -> None:
    """Create the tables and seed them from data/ if the database is empty."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0:
            seed(conn)
    conn.close()


def seed(conn: sqlite3.Connection) -> None:
    """Load the queue and its records from data/."""
    files: dict[str, Any] = {
        name: json.loads(load(name)) for name in SEED_FILES if name.endswith(".json")
    }
    conn.executemany(
        "INSERT INTO claims (claim_id, status, data) VALUES (?, 'waiting', ?)",
        [(c["claim_id"], json.dumps(c)) for c in files["claims.json"]],
    )
    for table, key, name in (
        ("policies", "policy_id", "policies.json"),
        ("customers", "customer_id", "customers.json"),
        ("handlers", "handler_id", "handlers.json"),
    ):
        conn.executemany(
            f"INSERT INTO {table} ({key}, data) VALUES (?, ?)",  # noqa: S608
            [(r[key], json.dumps(r)) for r in files[name]],
        )
    conn.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        [
            ("plans", json.dumps(files["plans.json"])),
            ("company", json.dumps(files["company.json"])),
            ("policy_wording", json.dumps(load("policy_wording.md"))),
        ],
    )


def setting(conn: sqlite3.Connection, key: str) -> Any:
    """Return one of the stored settings."""
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"])
