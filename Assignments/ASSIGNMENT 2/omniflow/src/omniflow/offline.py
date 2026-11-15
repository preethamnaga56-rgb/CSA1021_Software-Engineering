"""Disconnected scanner node, bounded buffer, server-side deduplication and queued approvals (design v1)."""
from collections import deque
from datetime import timedelta
from .auth import authenticate, require
from .db import tx, audit
from .errors import BufferFull, OmniFlowError, Forbidden, NotFound, InvalidTransition
from .refunds import approve_refund

SCHEMA_VERSION = 1
STALE_HOURS = 24

class ScannerNode:
    def __init__(self, node_id, capacity=1000):
        self.node_id, self.capacity, self._seq = node_id, capacity, 0
        self.buffer = deque()
    def record(self, sku, delta, observed_at, policy_version=None):
        if len(self.buffer) >= self.capacity:
            raise BufferFull(f"node {self.node_id} buffer full ({self.capacity}); refusing instead of dropping")
        self._seq += 1
        ev = {"node_id": self.node_id, "event_id": f"{self.node_id}-{self._seq:08d}", "sku": sku, "delta": delta,
              "observed_at": observed_at.isoformat(), "policy_version": policy_version, "schema_version": SCHEMA_VERSION}
        self.buffer.append(ev)
        return ev["event_id"]
    def sync(self, conn, token, now, batch=500):
        """Send oldest events first; discard only events the server acknowledged."""
        sent = list(self.buffer)[:batch]
        acked = ingest_scan_events(conn, token, sent, now)["acked"]
        ack = set(acked)
        self.buffer = deque(e for e in self.buffer if e["event_id"] not in ack)
        return len(ack)

def ingest_scan_events(conn, token, events, now):
    user = authenticate(conn, token)
    require(user, "scan.ingest")
    counts = {"applied": 0, "duplicate": 0, "pending_review": 0, "rejected": 0, "stale": 0}
    acked = []
    with tx(conn):
        for ev in events:
            known = conn.execute("SELECT 1 FROM products WHERE sku=?", (ev["sku"],)).fetchone()
            stale = 1 if (now - __import__("datetime").datetime.fromisoformat(ev["observed_at"])) > timedelta(hours=STALE_HOURS) else 0
            if ev["schema_version"] > SCHEMA_VERSION or not known:
                status = "REJECTED"
            elif ev["delta"] > 0:
                status = "APPLIED"
            else:
                status = "PENDING_REVIEW"              # negative corrections need a human (store manager)
            n = conn.execute("INSERT OR IGNORE INTO scan_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                             (ev["node_id"], ev["event_id"], ev["sku"], ev["delta"], ev["observed_at"], now.isoformat(),
                              ev.get("policy_version"), ev["schema_version"], status, stale)).rowcount
            acked.append(ev["event_id"])
            if n == 0:
                counts["duplicate"] += 1
                continue
            if status == "APPLIED":
                conn.execute("UPDATE stock SET on_hand=on_hand+?, version=version+1 WHERE sku=?", (ev["delta"], ev["sku"]))
                counts["applied"] += 1
            elif status == "PENDING_REVIEW":
                counts["pending_review"] += 1
            else:
                counts["rejected"] += 1
            counts["stale"] += stale
    counts["acked"] = acked
    return counts

def approve_stock_correction(conn, token, node_id, event_id, now):
    user = authenticate(conn, token)
    require(user, "stock.correct")
    with tx(conn):
        ev = conn.execute("SELECT * FROM scan_events WHERE node_id=? AND event_id=?", (node_id, event_id)).fetchone()
        if ev is None:
            raise NotFound("scan event")
        if ev["status"] != "PENDING_REVIEW":
            raise InvalidTransition(f"event is {ev['status']}")
        s = conn.execute("SELECT on_hand,reserved FROM stock WHERE sku=?", (ev["sku"],)).fetchone()
        if s["on_hand"] + ev["delta"] < s["reserved"]:
            raise InvalidTransition("correction would drop stock below reserved units")
        conn.execute("UPDATE stock SET on_hand=on_hand+?, version=version+1 WHERE sku=?", (ev["delta"], ev["sku"]))
        conn.execute("UPDATE scan_events SET status='APPROVED_APPLIED' WHERE node_id=? AND event_id=?", (node_id, event_id))
        audit(conn, now, user.id, "stock.correction.approved", None, f"{node_id}/{event_id}")

class OfflineApprovalQueue:
    """Approvals captured while the client is disconnected. They are requests, never decisions."""
    def __init__(self):
        self.items = []
    def queue(self, refund_id, token, queued_at):
        self.items.append({"refund_id": refund_id, "token": token, "queued_at": queued_at, "outcome": "QUEUED"})
    def display_state(self, conn, refund_id):
        r = conn.execute("SELECT state FROM refunds WHERE id=?", (refund_id,)).fetchone()
        queued = any(i["refund_id"] == refund_id and i["outcome"] == "QUEUED" for i in self.items)
        if queued and r["state"] == "REQUESTED":
            return "APPROVAL QUEUED - NOT YET VALIDATED BY SERVER"
        return r["state"]
    def flush(self, conn, now):
        results = []
        for it in self.items:
            if it["outcome"] != "QUEUED":
                continue
            ver = conn.execute("SELECT version FROM refunds WHERE id=?", (it["refund_id"],)).fetchone()["version"]
            try:
                approve_refund(conn, it["token"], it["refund_id"], ver, now)
                it["outcome"] = "VALIDATED_APPROVED"
            except OmniFlowError as exc:
                it["outcome"] = f"REJECTED_BY_SERVER: {exc}"
            results.append((it["refund_id"], it["outcome"]))
        return results
