"""Schema and transaction helper. SQLite stands in for PostgreSQL."""
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, role TEXT NOT NULL, region TEXT NOT NULL, email TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS products(sku TEXT PRIMARY KEY, price_cents INTEGER NOT NULL CHECK(price_cents>0));
CREATE TABLE IF NOT EXISTS stock(
  sku TEXT PRIMARY KEY REFERENCES products(sku),
  on_hand INTEGER NOT NULL, reserved INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
  CHECK(reserved >= 0 AND on_hand >= reserved));
CREATE TABLE IF NOT EXISTS regional_policy(
  region TEXT NOT NULL, version INTEGER NOT NULL, tax_bps INTEGER NOT NULL,
  shipping_cents INTEGER NOT NULL, refund_limit_cents INTEGER NOT NULL, return_days INTEGER NOT NULL,
  PRIMARY KEY(region, version));
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id TEXT NOT NULL REFERENCES users(id), region TEXT NOT NULL,
  state TEXT NOT NULL, subtotal_cents INTEGER NOT NULL, tax_cents INTEGER NOT NULL, shipping_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL, policy_version INTEGER NOT NULL, version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, paid_at TEXT, dispatch_due_at TEXT, delivered_at TEXT, tracking_id TEXT,
  needs_refund INTEGER NOT NULL DEFAULT 0, cancel_reason TEXT);
CREATE TABLE IF NOT EXISTS order_lines(
  order_id INTEGER NOT NULL REFERENCES orders(id), sku TEXT NOT NULL, qty INTEGER NOT NULL CHECK(qty>0),
  unit_price_cents INTEGER NOT NULL, PRIMARY KEY(order_id, sku));
CREATE TABLE IF NOT EXISTS reservations(
  order_id INTEGER NOT NULL REFERENCES orders(id), sku TEXT NOT NULL, qty INTEGER NOT NULL,
  expires_at TEXT NOT NULL, status TEXT NOT NULL,
  PRIMARY KEY(order_id, sku));
CREATE TABLE IF NOT EXISTS idempotency(
  owner_id TEXT NOT NULL, key TEXT NOT NULL, order_id INTEGER NOT NULL, PRIMARY KEY(owner_id, key));
CREATE TABLE IF NOT EXISTS payment_events(
  gateway_id TEXT NOT NULL, event_id TEXT NOT NULL, order_id INTEGER NOT NULL REFERENCES orders(id),
  amount_cents INTEGER NOT NULL, received_at TEXT NOT NULL, PRIMARY KEY(gateway_id, event_id));
CREATE TABLE IF NOT EXISTS refunds(
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id),
  amount_cents INTEGER NOT NULL CHECK(amount_cents>0), state TEXT NOT NULL, reason TEXT,
  requested_by TEXT NOT NULL, approved_by TEXT, approval_policy_version INTEGER,
  needs_finance INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
  needs_manual INTEGER NOT NULL DEFAULT 0, gateway_ref TEXT, version INTEGER NOT NULL DEFAULT 1);
CREATE TRIGGER IF NOT EXISTS refund_no_unapproved_execution
BEFORE UPDATE OF state ON refunds WHEN NEW.state='EXECUTED' AND NEW.approved_by IS NULL
BEGIN SELECT RAISE(ABORT,'refund cannot be executed without approval'); END;
CREATE TABLE IF NOT EXISTS refund_ledger(
  refund_id INTEGER PRIMARY KEY REFERENCES refunds(id), amount_cents INTEGER NOT NULL, executed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox(
  id INTEGER PRIMARY KEY AUTOINCREMENT, correlation_key TEXT NOT NULL UNIQUE, order_id INTEGER NOT NULL,
  purpose TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT, external_id TEXT, last_error TEXT);
CREATE TABLE IF NOT EXISTS scan_events(
  node_id TEXT NOT NULL, event_id TEXT NOT NULL, sku TEXT NOT NULL, delta INTEGER NOT NULL,
  observed_at TEXT NOT NULL, received_at TEXT NOT NULL, policy_version INTEGER, schema_version INTEGER NOT NULL,
  status TEXT NOT NULL, stale INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(node_id, event_id));
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  order_id INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS sales_summary(region TEXT, day TEXT, orders INTEGER, revenue_cents INTEGER, PRIMARY KEY(region, day));
CREATE TABLE IF NOT EXISTS refund_summary(region TEXT PRIMARY KEY, executed INTEGER, executed_cents INTEGER, open_requests INTEGER);
CREATE TABLE IF NOT EXISTS stock_summary(sku TEXT PRIMARY KEY, on_hand INTEGER, reserved INTEGER, low_stock INTEGER);
CREATE TABLE IF NOT EXISTS summary_meta(id INTEGER PRIMARY KEY CHECK(id=1), refreshed_at TEXT);
"""

def connect(path, timeout=30.0):
    conn = sqlite3.connect(path, timeout=timeout, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_schema(conn):
    conn.executescript(SCHEMA)

@contextmanager
def tx(conn):
    """One atomic unit of work (BEGIN IMMEDIATE takes the write lock up front)."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise

def audit(conn, at, actor, action, order_id=None, detail=None):
    conn.execute("INSERT INTO audit(at,actor,action,order_id,detail) VALUES(?,?,?,?,?)",
                 (at.isoformat(), actor, action, order_id, detail))
