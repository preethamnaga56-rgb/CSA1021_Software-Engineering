"""Refund request / approval / execution (design v2)."""
from .auth import authenticate, require
from .db import tx, audit
from .errors import (NotFound, ValidationError, InvalidTransition, VersionConflict, Forbidden, GatewayError)
from .policies import current_policy

MAX_ATTEMPTS = 3

def _refund(conn, rid):
    r = conn.execute("SELECT * FROM refunds WHERE id=?", (rid,)).fetchone()
    if r is None:
        raise NotFound(f"refund {rid}")
    return r

def request_refund(conn, token, order_id, amount_cents, reason, now):
    user = authenticate(conn, token)
    require(user, "refund.request")
    with tx(conn):
        o = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if o is None:
            raise NotFound("order")
        if user.role == "customer" and o["owner_id"] != user.id:
            raise Forbidden("not your order")
        if o["state"] != "DELIVERED":
            raise InvalidTransition("returns/refunds apply to delivered orders only")
        used = conn.execute("SELECT COALESCE(SUM(amount_cents),0) s FROM refunds WHERE order_id=? AND state NOT IN ('REJECTED')",
                            (order_id,)).fetchone()["s"]
        if amount_cents <= 0 or amount_cents + used > o["total_cents"]:
            raise ValidationError("refund exceeds the order total")
        limit = current_policy(conn, o["region"])["refund_limit_cents"]
        cur = conn.execute("INSERT INTO refunds(order_id,amount_cents,state,reason,requested_by,needs_finance) VALUES(?,?,?,?,?,?)",
                           (order_id, amount_cents, "REQUESTED", reason, user.id, 1 if amount_cents > limit else 0))
        audit(conn, now, user.id, "refund.requested", order_id, f"refund={cur.lastrowid}")
    return cur.lastrowid

def approve_refund(conn, token, refund_id, expected_version, now):
    user = authenticate(conn, token)
    require(user, "refund.approve")
    with tx(conn):
        r = _refund(conn, refund_id)
        if r["requested_by"] == user.id:
            raise Forbidden("separation of duties: requester cannot approve")
        o = conn.execute("SELECT region FROM orders WHERE id=?", (r["order_id"],)).fetchone()
        pol = current_policy(conn, o["region"])               # R2: judged against the policy in force NOW, not at request time
        if r["amount_cents"] > pol["refund_limit_cents"] and user.role != "finance_reviewer":
            raise Forbidden("amount above the current limit needs a finance reviewer")
        if r["state"] != "REQUESTED":
            raise InvalidTransition(f"refund is {r['state']}")
        n = conn.execute("UPDATE refunds SET state='APPROVED', approved_by=?, approval_policy_version=?, version=version+1 "
                         "WHERE id=? AND state='REQUESTED' AND version=?",
                         (user.id, pol["version"], refund_id, expected_version)).rowcount
        if n == 0:
            raise VersionConflict("refund changed since it was read")
        audit(conn, now, user.id, "refund.approved", r["order_id"], f"refund={refund_id}")

def reject_refund(conn, token, refund_id, reason, now):
    user = authenticate(conn, token)
    require(user, "refund.reject")
    with tx(conn):
        r = _refund(conn, refund_id)
        if r["state"] != "REQUESTED":
            raise InvalidTransition(f"refund is {r['state']}")
        conn.execute("UPDATE refunds SET state='REJECTED', last_error=?, version=version+1 WHERE id=?", (reason, refund_id))
        audit(conn, now, user.id, "refund.rejected", r["order_id"], f"refund={refund_id}")

def execute_refund(conn, refund_id, gateway, now):
    """Approval-gated. Called by the integration worker, never by a user-facing command."""
    r = _refund(conn, refund_id)
    if r["state"] not in ("APPROVED", "FAILED") or r["approved_by"] is None:
        raise InvalidTransition(f"refund in state {r['state']} cannot be executed")
    if r["needs_manual"]:
        raise InvalidTransition("refund needs manual finance handling")
    try:
        ref = gateway.refund(f"refund:{refund_id}", r["amount_cents"])    # idempotent at the gateway
    except GatewayError as exc:
        with tx(conn):
            attempts = r["attempts"] + 1
            conn.execute("UPDATE refunds SET state='FAILED', attempts=?, last_error=?, needs_manual=?, version=version+1 WHERE id=?",
                         (attempts, str(exc), 1 if attempts >= MAX_ATTEMPTS else 0, refund_id))
            audit(conn, now, "worker", "refund.failed", r["order_id"], f"refund={refund_id} attempt={attempts}")
        return "FAILED"
    with tx(conn):
        conn.execute("UPDATE refunds SET state='EXECUTED', gateway_ref=?, version=version+1 WHERE id=?", (ref, refund_id))
        conn.execute("INSERT INTO refund_ledger VALUES(?,?,?)", (refund_id, r["amount_cents"], now.isoformat()))
        o = conn.execute("SELECT state FROM orders WHERE id=?", (r["order_id"],)).fetchone()
        if o["state"] == "DELIVERED":
            conn.execute("UPDATE orders SET state='CLOSED', version=version+1 WHERE id=?", (r["order_id"],))
        audit(conn, now, "worker", "refund.executed", r["order_id"], f"refund={refund_id}")
    return "EXECUTED"

class FakeGateway:
    """Controlled test interface for the payment gateway (live access unavailable)."""
    def __init__(self):
        self.fail_next = 0
        self.refunds = {}          # idempotency key -> reference
        self.calls = 0
    def refund(self, key, amount):
        self.calls += 1
        if self.fail_next > 0:
            self.fail_next -= 1
            raise GatewayError("gateway unavailable")
        return self.refunds.setdefault(key, f"gw-ref-{len(self.refunds)+1}")
