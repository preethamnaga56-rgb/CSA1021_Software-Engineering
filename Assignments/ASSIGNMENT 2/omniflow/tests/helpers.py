import json, os, shutil, sys, tempfile, unittest
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from omniflow import db, orders
from omniflow.orders import sign

NOW = datetime(2026, 11, 14, 10, 0, 0)
SECRET = b"synthetic-gateway-secret"
METRICS = {}

class World:
    """Synthetic data only: no real customers, orders or card numbers."""
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="omniflow_")
        self.path = os.path.join(self.dir, "test.db")
        self.conn = db.connect(self.path)
        db.init_schema(self.conn)
        c = self.conn
        for uid, role, email in [("c1", "customer", "asha.rao@example.com"), ("c2", "customer", "ben.thomas@example.com"),
                                 ("p1", "picker", None), ("s1", "support_agent", None), ("f1", "finance_reviewer", None),
                                 ("m1", "store_manager", None), ("a1", "administrator", None)]:
            c.execute("INSERT INTO users VALUES(?,?,?,?)", (uid, role, "R1", email))
            c.execute("INSERT INTO sessions VALUES(?,?)", (f"tok-{uid}", uid))
        c.execute("INSERT INTO regional_policy VALUES('R1',1,1800,5000,50000,7)")
        for sku, price, qty in [("SKU-LAST", 10000, 1), ("SKU-A", 2500, 50), ("SKU-B", 120000, 10)]:
            c.execute("INSERT INTO products VALUES(?,?)", (sku, price))
            c.execute("INSERT INTO stock(sku,on_hand) VALUES(?,?)", (sku, qty))
    def tok(self, uid): return f"tok-{uid}"
    def callback(self, order_id, amount, event_id="evt-1", gateway="gw-test"):
        body = json.dumps({"gateway_id": gateway, "event_id": event_id, "order_id": order_id,
                           "amount_cents": amount, "status": "succeeded"}).encode()
        return body, sign(SECRET, body)
    def total(self, oid):
        return self.conn.execute("SELECT total_cents FROM orders WHERE id=?", (oid,)).fetchone()[0]
    def pay(self, oid, event_id="evt-1", now=NOW):
        body, sig = self.callback(oid, self.total(oid), event_id)
        return orders.handle_payment_callback(self.conn, body, sig, SECRET, now)
    def version(self, oid):
        return self.conn.execute("SELECT version FROM orders WHERE id=?", (oid,)).fetchone()[0]
    def deliver(self, sku="SKU-A", qty=2, customer="c1", event_id="evt-d"):
        oid = orders.place_order(self.conn, self.tok(customer), [(sku, qty)], NOW)
        self.pay(oid, event_id)
        orders.confirm_pick(self.conn, self.tok("p1"), oid, self.version(oid), NOW)
        orders.dispatch(self.conn, self.tok("p1"), oid, self.version(oid), NOW)
        orders.courier_delivered(self.conn, oid, NOW)
        return oid
    def count(self, table, where="1=1", args=()):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]
    def stock(self, sku):
        r = self.conn.execute("SELECT on_hand,reserved FROM stock WHERE sku=?", (sku,)).fetchone()
        return r["on_hand"], r["reserved"]
    def close(self):
        self.conn.close(); shutil.rmtree(self.dir, ignore_errors=True)

class Base(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()
