"""Durable integration intents (transactional outbox) and the courier worker."""
from datetime import datetime, timedelta
from .db import tx, audit
from .errors import CourierError

MAX_ATTEMPTS = 5

class FakeCourier:
    """Controlled test interface for the courier API (live access unavailable)."""
    def __init__(self):
        self.mode = "ok"            # ok | down | timeout_after_create
        self.shipments = {}         # correlation key -> tracking id
        self.create_calls = 0
    def find_by_key(self, key):
        if self.mode == "down":
            raise CourierError("courier unavailable")
        return self.shipments.get(key)
    def create_shipment(self, key, payload=None):
        self.create_calls += 1
        if self.mode == "down":
            raise CourierError("courier unavailable")
        tracking = self.shipments.setdefault(key, f"TRK-{len(self.shipments)+1:04d}")
        if self.mode == "timeout_after_create":
            raise CourierError("timeout after shipment was created")
        return tracking

def process_outbox(conn, courier, now):
    done = 0
    due = conn.execute("SELECT * FROM outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=? ORDER BY id",
                       (now.isoformat(),)).fetchall()
    for it in due:
        try:
            tracking = courier.find_by_key(it["correlation_key"])         # reconcile BEFORE creating
            if tracking is None:
                tracking = courier.create_shipment(it["correlation_key"])
        except CourierError as exc:
            attempts = it["attempts"] + 1
            status = "DEAD" if attempts >= MAX_ATTEMPTS else "RETRY"
            nxt = now + timedelta(minutes=2 ** attempts)
            with tx(conn):
                conn.execute("UPDATE outbox SET status=?, attempts=?, last_error=?, next_attempt_at=? WHERE id=?",
                             (status, attempts, str(exc), nxt.isoformat(), it["id"]))
                audit(conn, now, "worker", f"outbox.{status.lower()}", it["order_id"], it["correlation_key"])
            continue
        with tx(conn):
            conn.execute("UPDATE outbox SET status='DONE', external_id=?, last_error=NULL WHERE id=?", (tracking, it["id"]))
            conn.execute("UPDATE orders SET tracking_id=? WHERE id=?", (tracking, it["order_id"]))
            audit(conn, now, "worker", "outbox.done", it["order_id"], tracking)
        done += 1
    return done
