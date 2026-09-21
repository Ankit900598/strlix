"""DB access: Postgres with RLS when DATABASE_URL set; else SQLite."""
from __future__ import annotations
import contextlib, json, sqlite3, time, uuid
from pathlib import Path
from typing import Any, Iterator, Optional

from .settings import settings

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT UNIQUE, display_name TEXT, is_anonymous INTEGER NOT NULL DEFAULT 0,
  created_at REAL, deleted_at REAL
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, user_id TEXT, device_id TEXT, plan TEXT,
  amount_cents INTEGER, currency TEXT, provider TEXT, status TEXT,
  provider_ref TEXT, created_at REAL, deleted_at REAL
);
CREATE TABLE IF NOT EXISTS payment_intents (
  id TEXT PRIMARY KEY, user_id TEXT, order_id TEXT, provider TEXT,
  provider_intent_id TEXT, status TEXT, amount_cents INTEGER, currency TEXT,
  created_at REAL, updated_at REAL,
  UNIQUE (provider, provider_intent_id)
);
CREATE TABLE IF NOT EXISTS leases (
  id TEXT PRIMARY KEY, user_id TEXT, order_id TEXT, device_id TEXT, broker_sid TEXT,
  starts_at REAL, ends_at REAL, status TEXT, deleted_at REAL
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT,
  resource_type TEXT, resource_id TEXT, meta TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS waitlist (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  created_at REAL NOT NULL,
  invite_code_hash TEXT
);
"""

def new_id() -> str:
    return str(uuid.uuid4())

def _sqlite_path() -> Path:
    dsn = settings.market_db
    if dsn.startswith("sqlite:///"):
        return Path(dsn.replace("sqlite:///", "", 1)).expanduser().resolve()
    return Path("/workspace/zevi-cloudphone/demo/cloud-phone-market/market-dev.db")

class Conn:
    def __init__(self, raw, kind: str):
        self.raw = raw
        self.kind = kind  # sqlite|pg

    def execute(self, sql: str, params: tuple = ()):
        if self.kind == "sqlite":
            return self.raw.execute(sql.replace("%s", "?"), params)
        cur = self.raw.cursor()
        cur.execute(sql, params)
        return cur

    def set_user(self, user_id: Optional[str]):
        if self.kind != "pg":
            return
        cur = self.raw.cursor()
        cur.execute("SELECT set_config('app.user_id', %s, true)", (user_id or "",))

    def commit(self):
        self.raw.commit()

    def rollback(self):
        try:
            self.raw.rollback()
        except Exception:
            pass

    def close(self):
        self.raw.close()

def fetchone(cur) -> Optional[dict]:
    row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return dict(row)

def fetchall(cur) -> list[dict]:
    rows = cur.fetchall()
    out = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        elif hasattr(row, "keys"):
            out.append({k: row[k] for k in row.keys()})
        else:
            out.append(dict(row))
    return out

@contextlib.contextmanager
def session(user_id: Optional[str] = None) -> Iterator[Conn]:
    if settings.use_postgres:
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(settings.pg_dsn, row_factory=dict_row)
        raw.execute("BEGIN")
        con = Conn(raw, "pg")
        if user_id:
            con.set_user(user_id)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
    else:
        path = _sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(path)
        raw.row_factory = sqlite3.Row
        raw.executescript(SQLITE_SCHEMA)
        # Existing local demo databases predate anonymous sessions. Keep the
        # dev fallback backwards-compatible without requiring a destructive
        # database reset.
        columns = {row[1] for row in raw.execute("PRAGMA table_info(users)").fetchall()}
        if "is_anonymous" not in columns:
            raw.execute("ALTER TABLE users ADD COLUMN is_anonymous INTEGER NOT NULL DEFAULT 0")
        wait_cols = {row[1] for row in raw.execute("PRAGMA table_info(waitlist)").fetchall()}
        if wait_cols and "invite_code_hash" not in wait_cols:
            raw.execute("ALTER TABLE waitlist ADD COLUMN invite_code_hash TEXT")
        con = Conn(raw, "sqlite")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

def audit(con: Conn, user_id: Optional[str], action: str, resource_type: str | None = None,
          resource_id: str | None = None, meta: dict | None = None):
    safe = meta or {}
    if con.kind == "pg":
        con.execute(
            "INSERT INTO market.audit_log(user_id, action, resource_type, resource_id, meta) VALUES (%s::uuid,%s,%s,%s,%s::jsonb)",
            (user_id, action, resource_type, resource_id, json.dumps(safe)),
        )
    else:
        con.execute(
            "INSERT INTO audit_log(user_id, action, resource_type, resource_id, meta, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, action, resource_type, resource_id, json.dumps(safe), time.time()),
        )
