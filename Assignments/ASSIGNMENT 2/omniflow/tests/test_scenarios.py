"""Base-release validation scenarios S1-S8. Each test name starts with its scenario id."""
import json, sqlite3, threading
from datetime import timedelta
from helpers import Base, NOW, SECRET
from omniflow import db, orders, refunds, outbox
from omniflow.errors import *
from omniflow.outbox import FakeCourier
from omniflow.refunds import FakeGateway

def run_threads(n, fn):
    barrier, results = threading.Barrier(n), []
    lock = threading.Lock()
    def target(i):
        barrier.wait()
        try:
            out = ("ok", fn(i))
        except Exception as exc:
            out = ("err", exc)
        with lock:
            results.append(out)
    ts = [threading.Thread(target=target, args=(i,)) for i in range(n)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return results

class S1_LastUnit(Base):
    def test_S1_last_unit_sequential(self):
        a = orders.place_order(self.w.conn, "tok-c1", [("SKU-LAST", 1)], NOW)
        with self.assertRaises(OutOfStock):
            orders.place_order(self.w.conn, "tok-c2", [("SKU-LAST", 1)], NOW)
        self.assertEqual(self.w.stock("SKU-LAST"), (1, 1))
        self.assertEqual(self.w.count("orders"), 1)

    def test_S1_last_unit_twelve_concurrent_buyers(self):
        def buy(i):
            conn = db.connect(self.w.path)
            try:
                return orders.place_order(conn, "tok-c1" if i % 2 else "tok-c2", [("SKU-LAST", 1)], NOW)
            finally:
                conn.close()
        res = run_threads(12, buy)
        ok = [r for r in res if r[0] == "ok"]
        self.assertEqual(len(ok), 1)
        self.assertTrue(all(isinstance(r[1], OutOfStock) for r in res if r[0] == "err"))
        self.assertEqual(self.w.stock("SKU-LAST"), (1, 1))
        self.assertEqual(self.w.count("orders"), 1)

class S2_DuplicateCallback(Base):
    def _assert_single_effect(self, oid):
        self.assertEqual(self.w.count("payment_events"), 1)
        self.assertEqual(self.w.count("outbox"), 1)
        self.assertEqual(self.w.count("audit", "action='order.paid'"), 1)
        self.assertEqual(self.w.version(oid), 2)         # placed(1) -> paid(2) once

    def test_S2_duplicate_callback_ten_sequential_repeats(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        results = [self.w.pay(oid, "evt-77")["result"] for _ in range(10)]
        self.assertEqual(results.count("PAID"), 1)
        self.assertEqual(results.count("DUPLICATE"), 9)
        self._assert_single_effect(oid)

    def test_S2_duplicate_callback_arrives_while_original_in_flight(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        body, sig = self.w.callback(oid, self.w.total(oid), "evt-88")
        def hit(i):
            conn = db.connect(self.w.path)
            try:
                return orders.handle_payment_callback(conn, body, sig, SECRET, NOW)["result"]
            finally:
                conn.close()
        res = run_threads(10, hit)
        self.assertTrue(all(r[0] == "ok" for r in res), [r for r in res if r[0] == "err"])
        outcomes = [r[1] for r in res]
        self.assertEqual(outcomes.count("PAID"), 1)
        self.assertEqual(outcomes.count("DUPLICATE"), 9)
        self._assert_single_effect(oid)

class S3_RefundFailure(Base):
    def test_S3_approved_refund_fails_then_retries_without_new_approval(self):
        oid = self.w.deliver()
        rid = refunds.request_refund(self.w.conn, "tok-s1", oid, 3000, "damaged", NOW)
        refunds.approve_refund(self.w.conn, "tok-m1", rid, 1, NOW)
        gw = FakeGateway(); gw.fail_next = 1
        self.assertEqual(refunds.execute_refund(self.w.conn, rid, gw, NOW), "FAILED")
        r = self.w.conn.execute("SELECT * FROM refunds WHERE id=?", (rid,)).fetchone()
        self.assertEqual((r["state"], r["approved_by"], r["attempts"]), ("FAILED", "m1", 1))
        self.assertEqual(self.w.count("refund_ledger"), 0)
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "DELIVERED")
        self.assertEqual(refunds.execute_refund(self.w.conn, rid, gw, NOW), "EXECUTED")
        self.assertEqual(self.w.count("refund_ledger"), 1)
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "CLOSED")
        self.assertEqual(len(gw.refunds), 1)              # same idempotency key both times

    def test_S3_unapproved_refund_cannot_execute(self):
        oid = self.w.deliver()
        rid = refunds.request_refund(self.w.conn, "tok-s1", oid, 3000, "damaged", NOW)
        with self.assertRaises(InvalidTransition):
            refunds.execute_refund(self.w.conn, rid, FakeGateway(), NOW)
        with self.assertRaises(sqlite3.IntegrityError):    # database-level second line of defence
            self.w.conn.execute("UPDATE refunds SET state='EXECUTED' WHERE id=?", (rid,))
        self.assertEqual(self.w.count("refund_ledger"), 0)

class S4_DispatchGuards(Base):
    def test_S4_dispatch_without_payment_or_pick_is_rejected(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        before = self.w.stock("SKU-A")
        with self.assertRaises(InvalidTransition):
            orders.dispatch(self.w.conn, "tok-p1", oid, 1, NOW)            # Placed, unpaid
        self.w.pay(oid)
        with self.assertRaises(InvalidTransition):
            orders.dispatch(self.w.conn, "tok-p1", oid, 2, NOW)            # Paid, not picked
        self.assertEqual(self.w.stock("SKU-A"), before)
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "PAID")

    def test_S4_second_guard_checks_payment_record_even_if_state_were_forged(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        self.w.conn.execute("UPDATE orders SET state='PACKED' WHERE id=?", (oid,))   # simulated corruption
        with self.assertRaises(InvalidTransition):
            orders.dispatch(self.w.conn, "tok-p1", oid, 1, NOW)

    def test_S4_stale_version_cannot_overwrite_accepted_state(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        self.w.pay(oid)
        orders.confirm_pick(self.w.conn, "tok-p1", oid, 2, NOW)
        with self.assertRaises(InvalidTransition):                          # second picker, same screen
            orders.confirm_pick(self.w.conn, "tok-p1", oid, 2, NOW)

class S5_CourierRetry(Base):
    def test_S5_courier_failure_then_timeout_after_create_then_success(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        self.w.pay(oid)
        courier = FakeCourier(); courier.mode = "down"
        t = NOW
        outbox.process_outbox(self.w.conn, courier, t)
        i = self.w.conn.execute("SELECT * FROM outbox").fetchone()
        self.assertEqual((i["status"], i["attempts"]), ("RETRY", 1))
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "PAID")
        courier.mode = "timeout_after_create"          # shipment IS created but the response is lost
        t += timedelta(minutes=5)
        outbox.process_outbox(self.w.conn, courier, t)
        self.assertEqual(len(courier.shipments), 1)
        courier.mode = "ok"
        t += timedelta(minutes=10)
        self.assertEqual(outbox.process_outbox(self.w.conn, courier, t), 1)
        i = self.w.conn.execute("SELECT * FROM outbox").fetchone()
        self.assertEqual(i["status"], "DONE")
        self.assertEqual(len(courier.shipments), 1)                          # never a second shipment
        self.assertEqual(courier.create_calls, 1)    # reconciliation found the shipment, so no second create call
        self.assertEqual(self.w.conn.execute("SELECT tracking_id FROM orders WHERE id=?", (oid,)).fetchone()[0], i["external_id"])

class S6_Authorization(Base):
    def setUp(self):
        super().setUp()
        self.oid = self.w.deliver()
        self.rid = refunds.request_refund(self.w.conn, "tok-s1", self.oid, 3000, "damaged", NOW)

    def test_S6_customer_and_agent_cannot_approve_refund(self):
        for tok in ("tok-c1", "tok-s1"):
            with self.assertRaises(Forbidden):
                refunds.approve_refund(self.w.conn, tok, self.rid, 1, NOW)
        self.assertEqual(self.w.conn.execute("SELECT state FROM refunds WHERE id=?", (self.rid,)).fetchone()[0], "REQUESTED")

    def test_S6_ui_role_selector_has_no_effect_on_server_identity(self):
        # the API accepts a session token only; a client-claimed role is not a parameter and is not read
        with self.assertRaises(TypeError):
            refunds.approve_refund(self.w.conn, "tok-s1", self.rid, 1, NOW, claimed_role="finance_reviewer")
        with self.assertRaises(Forbidden):
            refunds.approve_refund(self.w.conn, "tok-s1", self.rid, 1, NOW)
        with self.assertRaises(Unauthenticated):
            refunds.approve_refund(self.w.conn, "forged-token", self.rid, 1, NOW)

    def test_S6_cross_customer_read_rejected_and_support_view_is_masked(self):
        with self.assertRaises(Forbidden):
            orders.view_order(self.w.conn, "tok-c2", self.oid)
        sv = orders.view_order(self.w.conn, "tok-s1", self.oid)
        self.assertNotIn("asha.rao@example.com", json.dumps(sv))
        self.assertNotIn("payments", sv)
        self.assertEqual(sv["contact"], "a***@e***")
        fv = orders.view_order(self.w.conn, "tok-f1", self.oid)
        self.assertIn("payments", fv)

    def test_S6_manager_cannot_approve_above_limit_and_requester_cannot_self_approve(self):
        big = self.w.deliver("SKU-B", 1, event_id="evt-big")
        rid = refunds.request_refund(self.w.conn, "tok-s1", big, 100000, "return", NOW)      # > 50,000 limit
        with self.assertRaises(Forbidden):
            refunds.approve_refund(self.w.conn, "tok-m1", rid, 1, NOW)
        refunds.approve_refund(self.w.conn, "tok-f1", rid, 1, NOW)
        self.w.conn.execute("INSERT INTO users VALUES('f2','finance_reviewer','R1',NULL)")
        self.w.conn.execute("INSERT INTO sessions VALUES('tok-f2','f2')")
        rid2 = refunds.request_refund(self.w.conn, "tok-c1", self.oid, 1000, "x", NOW)
        self.w.conn.execute("UPDATE refunds SET requested_by='f2' WHERE id=?", (rid2,))
        with self.assertRaises(Forbidden):
            refunds.approve_refund(self.w.conn, "tok-f2", rid2, 1, NOW)

class S7_LatePayment(Base):
    def test_S7_late_payment_after_expiry_when_unit_was_resold(self):
        a = orders.place_order(self.w.conn, "tok-c1", [("SKU-LAST", 1)], NOW)
        later = NOW + timedelta(minutes=16)
        self.assertEqual(orders.expire_reservations(self.w.conn, later), 1)
        self.assertEqual(self.w.stock("SKU-LAST"), (1, 0))
        b = orders.place_order(self.w.conn, "tok-c2", [("SKU-LAST", 1)], later)      # unit resold
        res = self.w.pay(a, "evt-late", later)
        self.assertEqual(res["result"], "NEEDS_REFUND")
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (a,)).fetchone()[0], "CANCELLED")
        self.assertEqual(self.w.stock("SKU-LAST"), (1, 1))                              # not oversold
        rf = self.w.conn.execute("SELECT * FROM refunds WHERE order_id=?", (a,)).fetchone()
        self.assertEqual((rf["state"], rf["requested_by"]), ("REQUESTED", "system"))
        self.assertEqual(self.w.count("outbox", "order_id=?", (a,)), 0)

    def test_S7_late_payment_after_expiry_when_stock_remains_re_reserves(self):
        a = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 2)], NOW)
        later = NOW + timedelta(minutes=16)
        orders.expire_reservations(self.w.conn, later)
        res = self.w.pay(a, "evt-late2", later)
        self.assertEqual(res["result"], "PAID_AFTER_EXPIRY")
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (a,)).fetchone()[0], "PAID")
        self.assertEqual(self.w.stock("SKU-A"), (50, 2))

    def test_S7_second_distinct_payment_for_an_already_paid_order_opens_refund_request(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        self.w.pay(oid, "evt-1")
        res = self.w.pay(oid, "evt-2")                     # different event identity = a genuine second charge
        self.assertEqual(res["result"], "EXTRA_PAYMENT_REFUND_REQUESTED")
        self.assertEqual(self.w.count("outbox"), 1)
        self.assertEqual(self.w.count("refunds", "order_id=? AND requested_by='system'", (oid,)), 1)

    def test_S7_reservation_expiry_releases_exactly_once(self):
        orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 3)], NOW)
        later = NOW + timedelta(minutes=16)
        self.assertEqual(orders.expire_reservations(self.w.conn, later), 1)
        self.assertEqual(orders.expire_reservations(self.w.conn, later), 0)
        self.assertEqual(self.w.stock("SKU-A"), (50, 0))

class S8_PaymentIntegrity(Base):
    def test_S8_bad_signature_and_amount_mismatch_rejected_without_effect(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        body, sig = self.w.callback(oid, self.w.total(oid))
        with self.assertRaises(BadSignature):
            orders.handle_payment_callback(self.w.conn, body, "0" * 64, SECRET, NOW)
        body2, sig2 = self.w.callback(oid, 1, "evt-cheap")
        with self.assertRaises(AmountMismatch):
            orders.handle_payment_callback(self.w.conn, body2, sig2, SECRET, NOW)
        self.assertEqual(self.w.count("payment_events"), 0)
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "PLACED")

    def test_S8_browser_success_redirect_cannot_mark_paid(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)
        with self.assertRaises(InvalidTransition):
            orders.confirm_pick(self.w.conn, "tok-p1", oid, 1, NOW)       # no API path other than the callback marks Paid
        self.assertEqual(self.w.conn.execute("SELECT state FROM orders WHERE id=?", (oid,)).fetchone()[0], "PLACED")

    def test_S8_price_and_tax_server_side_and_client_price_rejected(self):
        oid = orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 2)], NOW)
        o = self.w.conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        self.assertEqual((o["subtotal_cents"], o["tax_cents"], o["shipping_cents"], o["total_cents"]), (5000, 900, 5000, 10900))
        with self.assertRaises(ValidationError):
            orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1, 1)], NOW)       # client-supplied price
        with self.assertRaises(ValidationError):
            orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 0)], NOW)
