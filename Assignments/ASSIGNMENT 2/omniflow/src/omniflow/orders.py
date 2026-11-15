"""Order placement, payment callback, lifecycle and read projections (design v2).

v2 revision R1: payments that arrive for orders that are no longer Placed (expired, customer-cancelled, or already paid)
are never ignored - they either recover the order (re-reserve) or open a system refund request.
"""
import hashlib, hmac, json
from datetime import timedelta
from .auth import authenticate, require, mask_email
from .db import tx, audit
from .errors import (NotFound, ValidationError, OutOfStock, InvalidTransition, VersionConflict,
                     BadSignature, AmountMismatch, Forbidden)
from .policies import current_policy

RESERVATION_MINUTES = 15
DISPATCH_HOURS = 24
ALLOWED = {"PLACED": {"PAID", "CANCELLED"}, "PAID": {"PACKED"}, "PACKED": {"DISPATCHED"},
           "DISPATCHED": {"DELIVERED"}, "DELIVERED": {"CLOSED"},
           "CANCELLED": {"PAID"}}      # ONLY reachable through verified late-payment recovery of an EXPIRED order (R1)

def sign(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()

def _transition(conn, order_id, frm, to, expected_version=None):
    if to not in ALLOWED.get(frm, set()):
        raise InvalidTransition(f"{frm} -> {to} is not permitted")
    sql = "UPDATE orders SET state=?, version=version+1 WHERE id=? AND state=?"
    args = [to, order_id, frm]
    if expected_version is not None:
        sql += " AND version=?"; args.append(expected_version)
    if conn.execute(sql, args).rowcount == 0:
        row = conn.execute("SELECT state,version FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise NotFound("order")
        if row["state"] != frm:
            raise InvalidTransition(f"order is {row['state']}, expected {frm}")
        raise VersionConflict("order changed since it was read")

def _order(conn, order_id):
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if row is None:
        raise NotFound(f"order {order_id}")
    return row

def place_order(conn, token, items, now, idem_key=None):
    """items: list of (sku, qty). Prices are NEVER taken from the client."""
    user = authenticate(conn, token)
    require(user, "order.place")
    if not items:
        raise ValidationError("empty order")
    merged = {}
    for item in items:
        if len(item) != 2:
            raise ValidationError("a line is (sku, qty) only; prices are server-side")
        sku, qty = item
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValidationError("quantity must be a positive integer")
        merged[sku] = merged.get(sku, 0) + qty
    with tx(conn):
        if idem_key:
            hit = conn.execute("SELECT order_id FROM idempotency WHERE owner_id=? AND key=?", (user.id, idem_key)).fetchone()
            if hit:
                return hit["order_id"]
        policy = current_policy(conn, user.region)
        subtotal, priced = 0, []
        for sku, qty in sorted(merged.items()):
            p = conn.execute("SELECT price_cents FROM products WHERE sku=?", (sku,)).fetchone()
            if p is None:
                raise ValidationError(f"unknown sku {sku}")
            priced.append((sku, qty, p["price_cents"]))
            subtotal += qty * p["price_cents"]
        tax = (subtotal * policy["tax_bps"] + 5000) // 10000
        total = subtotal + tax + policy["shipping_cents"]
        for sku, qty, _ in priced:   # conditional update: succeeds only if enough free stock remains
            n = conn.execute("UPDATE stock SET reserved=reserved+?, version=version+1 "
                             "WHERE sku=? AND on_hand-reserved>=?", (qty, sku, qty)).rowcount
            if n == 0:
                raise OutOfStock(sku)
        cur = conn.execute("INSERT INTO orders(owner_id,region,state,subtotal_cents,tax_cents,shipping_cents,total_cents,"
                           "policy_version,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                           (user.id, user.region, "PLACED", subtotal, tax, policy["shipping_cents"], total,
                            policy["version"], now.isoformat()))
        oid = cur.lastrowid
        expires = (now + timedelta(minutes=RESERVATION_MINUTES)).isoformat()
        for sku, qty, price in priced:
            conn.execute("INSERT INTO order_lines VALUES(?,?,?,?)", (oid, sku, qty, price))
            conn.execute("INSERT INTO reservations VALUES(?,?,?,?,'ACTIVE')", (oid, sku, qty, expires))
        if idem_key:
            conn.execute("INSERT INTO idempotency VALUES(?,?,?)", (user.id, idem_key, oid))
        audit(conn, now, user.id, "order.placed", oid, f"total={total}")
    return oid

def expire_reservations(conn, now):
    """Release unpaid reservations whose expiry has passed - exactly once per reservation."""
    released = 0
    with tx(conn):
        due = conn.execute("SELECT DISTINCT r.order_id FROM reservations r JOIN orders o ON o.id=r.order_id "
                           "WHERE r.status='ACTIVE' AND r.expires_at<=? AND o.state='PLACED'", (now.isoformat(),)).fetchall()
        for d in due:
            oid = d["order_id"]
            for r in conn.execute("SELECT sku,qty FROM reservations WHERE order_id=? AND status='ACTIVE'", (oid,)).fetchall():
                if conn.execute("UPDATE reservations SET status='RELEASED' WHERE order_id=? AND sku=? AND status='ACTIVE'",
                                (oid, r["sku"])).rowcount:
                    conn.execute("UPDATE stock SET reserved=reserved-?, version=version+1 WHERE sku=?", (r["qty"], r["sku"]))
            _transition(conn, oid, "PLACED", "CANCELLED")
            conn.execute("UPDATE orders SET cancel_reason='EXPIRED' WHERE id=?", (oid,))
            audit(conn, now, "system", "order.expired", oid)
            released += 1
    return released

def handle_payment_callback(conn, body: bytes, signature: str, secret: bytes, now):
    """The ONLY path that can mark an order Paid. A browser 'success' redirect has no effect."""
    if not hmac.compare_digest(signature or "", sign(secret, body)):
        raise BadSignature("callback signature invalid")
    msg = json.loads(body)
    gw, ev, oid, amount = msg["gateway_id"], msg["event_id"], msg["order_id"], msg["amount_cents"]
    with tx(conn):
        order = _order(conn, oid)
        n = conn.execute("INSERT OR IGNORE INTO payment_events VALUES(?,?,?,?,?)",
                         (gw, ev, oid, amount, now.isoformat())).rowcount      # ON CONFLICT DO NOTHING
        if n == 0:
            return {"result": "DUPLICATE", "order_id": oid, "state": order["state"]}
        if amount != order["total_cents"]:
            raise AmountMismatch(f"expected {order['total_cents']} got {amount}")
        if order["state"] == "PLACED":
            _mark_paid(conn, order, now, gw, ev)
            return {"result": "PAID", "order_id": oid, "state": "PAID", "shipment_sync": "PENDING"}
        if order["state"] == "CANCELLED" and order["cancel_reason"] == "EXPIRED" and _try_rereserve(conn, oid):
            _mark_paid(conn, order, now, gw, ev)
            audit(conn, now, "gateway", "order.paid_after_expiry", oid, f"{gw}/{ev}")
            return {"result": "PAID_AFTER_EXPIRY", "order_id": oid, "state": "PAID", "shipment_sync": "PENDING"}
        # R1: money was received but the order cannot proceed -> explicit, approval-gated refund path
        _open_system_refund(conn, order, amount, now, f"{gw}/{ev}")
        kind = "NEEDS_REFUND" if order["state"] == "CANCELLED" else "EXTRA_PAYMENT_REFUND_REQUESTED"
        return {"result": kind, "order_id": oid, "state": order["state"]}

def _mark_paid(conn, order, now, gw, ev):
    oid = order["id"]
    _transition(conn, oid, order["state"], "PAID")
    conn.execute("UPDATE reservations SET status='CONFIRMED' WHERE order_id=?", (oid,))
    due = (now + timedelta(hours=DISPATCH_HOURS)).isoformat()
    conn.execute("UPDATE orders SET paid_at=?, dispatch_due_at=?, cancel_reason=NULL WHERE id=?", (now.isoformat(), due, oid))
    conn.execute("INSERT INTO outbox(correlation_key,order_id,purpose,status,next_attempt_at) VALUES(?,?,?,?,?)",
                 (f"shipment:{oid}", oid, "SHIPMENT_BOOKING", "PENDING", now.isoformat()))
    audit(conn, now, "gateway", "order.paid", oid, f"{gw}/{ev}")

def _try_rereserve(conn, oid):
    """All-or-nothing re-reservation of an expired order's lines (savepoint keeps it atomic)."""
    conn.execute("SAVEPOINT rereserve")
    for ln in conn.execute("SELECT sku,qty FROM order_lines WHERE order_id=?", (oid,)).fetchall():
        if conn.execute("UPDATE stock SET reserved=reserved+?, version=version+1 WHERE sku=? AND on_hand-reserved>=?",
                        (ln["qty"], ln["sku"], ln["qty"])).rowcount == 0:
            conn.execute("ROLLBACK TO rereserve"); conn.execute("RELEASE rereserve")
            return False
    conn.execute("RELEASE rereserve")
    return True

def _open_system_refund(conn, order, amount, now, ref):
    limit = current_policy(conn, order["region"])["refund_limit_cents"]
    conn.execute("UPDATE orders SET needs_refund=1 WHERE id=?", (order["id"],))
    conn.execute("INSERT INTO refunds(order_id,amount_cents,state,reason,requested_by,needs_finance) VALUES(?,?,?,?,?,?)",
                 (order["id"], amount, "REQUESTED", f"payment cannot be fulfilled ({ref})", "system", 1 if amount > limit else 0))
    audit(conn, now, "system", "refund.requested.system", order["id"], ref)

def confirm_pick(conn, token, order_id, expected_version, now):
    user = authenticate(conn, token)
    require(user, "order.pick")
    with tx(conn):
        order = _order(conn, order_id)
        if order["region"] != user.region:
            raise Forbidden("picker works only in own region")
        _transition(conn, order_id, order["state"], "PACKED", expected_version)
        audit(conn, now, user.id, "order.packed", order_id)

def dispatch(conn, token, order_id, expected_version, now):
    user = authenticate(conn, token)
    require(user, "order.dispatch")
    with tx(conn):
        order = _order(conn, order_id)
        if order["region"] != user.region:
            raise Forbidden("picker works only in own region")
        if order["state"] != "PACKED":
            raise InvalidTransition(f"dispatch needs PACKED (payment + pick), order is {order['state']}")
        paid = conn.execute("SELECT 1 FROM payment_events WHERE order_id=?", (order_id,)).fetchone()
        if not paid:
            raise InvalidTransition("no confirmed payment for this order")
        _transition(conn, order_id, "PACKED", "DISPATCHED", expected_version)
        for ln in conn.execute("SELECT sku,qty FROM order_lines WHERE order_id=?", (order_id,)).fetchall():
            conn.execute("UPDATE stock SET on_hand=on_hand-?, reserved=reserved-?, version=version+1 WHERE sku=?",
                         (ln["qty"], ln["qty"], ln["sku"]))
        conn.execute("UPDATE reservations SET status='CONSUMED' WHERE order_id=?", (order_id,))
        audit(conn, now, user.id, "order.dispatched", order_id)

def courier_delivered(conn, order_id, now):
    """Called by the courier-status sync (system actor)."""
    with tx(conn):
        _transition(conn, order_id, "DISPATCHED", "DELIVERED")
        conn.execute("UPDATE orders SET delivered_at=? WHERE id=?", (now.isoformat(), order_id))
        audit(conn, now, "courier-sync", "order.delivered", order_id)

def close_delivered_orders(conn, now):
    closed = 0
    with tx(conn):
        for o in conn.execute("SELECT id,region,delivered_at FROM orders WHERE state='DELIVERED'").fetchall():
            policy = current_policy(conn, o["region"])
            from datetime import datetime
            if datetime.fromisoformat(o["delivered_at"]) + timedelta(days=policy["return_days"]) <= now:
                open_refund = conn.execute("SELECT 1 FROM refunds WHERE order_id=? AND state IN ('REQUESTED','APPROVED','FAILED')",
                                           (o["id"],)).fetchone()
                if not open_refund:
                    _transition(conn, o["id"], "DELIVERED", "CLOSED")
                    audit(conn, now, "system", "order.closed", o["id"])
                    closed += 1
    return closed

def cancel_own_order(conn, token, order_id, now):
    user = authenticate(conn, token)
    require(user, "order.cancel_own")
    with tx(conn):
        order = _order(conn, order_id)
        if order["owner_id"] != user.id:
            raise Forbidden("not your order")
        _transition(conn, order_id, order["state"], "CANCELLED")      # only PLACED -> CANCELLED is permitted
        conn.execute("UPDATE orders SET cancel_reason='CUSTOMER' WHERE id=?", (order_id,))
        for r in conn.execute("SELECT sku,qty FROM reservations WHERE order_id=? AND status='ACTIVE'", (order_id,)).fetchall():
            conn.execute("UPDATE reservations SET status='RELEASED' WHERE order_id=? AND sku=?", (order_id, r["sku"]))
            conn.execute("UPDATE stock SET reserved=reserved-?, version=version+1 WHERE sku=?", (r["qty"], r["sku"]))
        audit(conn, now, user.id, "order.cancelled", order_id)

def view_order(conn, token, order_id):
    """Role-specific projections: privacy is enforced by the server, not by hiding UI controls."""
    user = authenticate(conn, token)
    o = _order(conn, order_id)
    base = {"order_id": o["id"], "state": o["state"], "version": o["version"], "tracking_id": o["tracking_id"]}
    if user.role == "customer":
        require(user, "order.view_own")
        if o["owner_id"] != user.id:
            raise Forbidden("not your order")
        base.update(total_cents=o["total_cents"], dispatch_due_at=o["dispatch_due_at"])
    elif user.role == "support_agent":
        require(user, "order.view_masked")
        owner = conn.execute("SELECT email FROM users WHERE id=?", (o["owner_id"],)).fetchone()
        base.update(contact=mask_email(owner["email"]),
                    refunds=[dict(r) for r in conn.execute("SELECT id,state,amount_cents FROM refunds WHERE order_id=?", (order_id,))])
    elif user.role == "finance_reviewer":
        require(user, "order.view_finance")
        base.update(total_cents=o["total_cents"],
                    payments=[dict(r) for r in conn.execute("SELECT gateway_id,event_id,amount_cents FROM payment_events WHERE order_id=?", (order_id,))])
    elif user.role == "picker":
        require(user, "picklist.view")
        if o["region"] != user.region or o["state"] not in ("PAID", "PACKED"):
            raise Forbidden("picker sees paid orders of own region only")
        base.update(lines=[dict(r) for r in conn.execute("SELECT sku,qty FROM order_lines WHERE order_id=?", (order_id,))])
    elif user.role in ("store_manager", "administrator"):
        base.update(region=o["region"], total_cents=o["total_cents"])
    else:
        raise Forbidden("no access")
    return base
