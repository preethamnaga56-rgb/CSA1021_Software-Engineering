"""Day-4 expansion scenarios X1-X5 (design assumptions, not measured capacity)."""
import time
from datetime import timedelta
from helpers import Base, NOW, METRICS
from omniflow import db, orders, refunds, policies, reports
from omniflow.cluster import ApiInstance, Proxy
from omniflow.errors import *
from omniflow.offline import ScannerNode, OfflineApprovalQueue, ingest_scan_events, approve_stock_correction

class X1_ReplayBurst(Base):
    def test_X1_replayed_scan_burst_gives_one_stock_change_per_event(self):
        node = ScannerNode("node-7", capacity=1000)
        for _ in range(600):
            node.record("SKU-A", +1, NOW - timedelta(minutes=30), policy_version=1)
        sent = list(node.buffer)
        self.assertEqual(ingest_scan_events(self.w.conn, "tok-p1", sent[:500], NOW)["applied"], 500)
        again = ingest_scan_events(self.w.conn, "tok-p1", sent[:500], NOW)        # ack lost -> whole batch replayed
        self.assertEqual((again["applied"], again["duplicate"]), (0, 500))
        node.sync(self.w.conn, "tok-p1", NOW, batch=500)
        node.sync(self.w.conn, "tok-p1", NOW, batch=500)
        self.assertEqual(len(node.buffer), 0)
        self.assertEqual(self.w.stock("SKU-A")[0], 50 + 600)
        self.assertEqual(self.w.count("scan_events"), 600)

    def test_X1_bounded_buffer_refuses_instead_of_dropping(self):
        node = ScannerNode("node-8", capacity=1000)
        for _ in range(1000):
            node.record("SKU-A", +1, NOW)
        with self.assertRaises(BufferFull):
            node.record("SKU-A", +1, NOW)
        self.assertEqual(len(node.buffer), 1000)

    def test_X1_local_timing_of_batched_ingest_5000_events(self):
        node = ScannerNode("node-9", capacity=6000)
        for _ in range(5000):
            node.record("SKU-A", +1, NOW)
        evs = list(node.buffer)
        t0 = time.perf_counter()
        for i in range(0, 5000, 500):
            ingest_scan_events(self.w.conn, "tok-p1", evs[i:i + 500], NOW)
        elapsed = time.perf_counter() - t0
        METRICS["X1_5000_events_batched_seconds"] = round(elapsed, 3)
        self.assertEqual(self.w.stock("SKU-A")[0], 5050)

class X2_PolicyChangeWhileOffline(Base):
    def test_X2_queued_approval_is_not_shown_approved_and_is_revalidated_against_new_policy(self):
        oid = self.w.deliver("SKU-A", 10, event_id="evt-x2")
        amount = self.w.total(oid)                       # 34,500 - below the original 50,000 limit
        rid = refunds.request_refund(self.w.conn, "tok-s1", oid, amount, "return", NOW)
        q = OfflineApprovalQueue()
        q.queue(rid, "tok-m1", NOW)
        self.assertEqual(q.display_state(self.w.conn, rid), "APPROVAL QUEUED - NOT YET VALIDATED BY SERVER")
        v = policies.set_policy(self.w.conn, "tok-a1", "R1", 1800, 5000, 20000, 7, NOW)     # limit lowered while offline
        self.assertEqual(v, 2)
        out = q.flush(self.w.conn, NOW)
        self.assertTrue(out[0][1].startswith("REJECTED_BY_SERVER"), out)
        self.assertEqual(self.w.conn.execute("SELECT state FROM refunds WHERE id=?", (rid,)).fetchone()[0], "REQUESTED")
        refunds.approve_refund(self.w.conn, "tok-f1", rid, 1, NOW)                          # finance reviewer can

    def test_X2_scan_events_record_the_policy_version_they_were_captured_under(self):
        node = ScannerNode("node-3")
        node.record("SKU-A", +2, NOW, policy_version=1)
        node.sync(self.w.conn, "tok-p1", NOW)
        self.assertEqual(self.w.conn.execute("SELECT policy_version FROM scan_events").fetchone()[0], 1)

class X3_ReplicaFailure(Base):
    def test_X3_one_api_replica_down_other_serves_and_retry_does_not_duplicate(self):
        a, b = ApiInstance("api-1", self.w.path), ApiInstance("api-2", self.w.path)
        proxy = Proxy([a, b])
        a.up = False
        o1 = proxy.place_order("tok-c1", [("SKU-A", 1)], NOW, idem_key="cart-42")
        self.assertEqual(proxy.served_by, ["api-2"])
        a.up = True
        o2 = proxy.place_order("tok-c1", [("SKU-A", 1)], NOW, idem_key="cart-42")       # client retry lands on api-1
        self.assertEqual(o1, o2)
        self.assertEqual(self.w.count("orders"), 1)
        self.assertEqual(self.w.stock("SKU-A"), (50, 1))
        a.conn.close(); b.conn.close()

class X4_StaleAndCorrections(Base):
    def test_X4_negative_scan_needs_manager_and_never_drops_below_reserved(self):
        orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 40)], NOW)               # reserved 40
        node = ScannerNode("node-4")
        node.record("SKU-A", -5, NOW - timedelta(hours=30))                            # stale + negative
        node.record("SKU-A", -20, NOW)
        res = ingest_scan_events(self.w.conn, "tok-p1", list(node.buffer), NOW)
        self.assertEqual((res["applied"], res["pending_review"], res["stale"]), (0, 2, 1))
        self.assertEqual(self.w.stock("SKU-A")[0], 50)                                 # unchanged until a human decides
        with self.assertRaises(Forbidden):
            approve_stock_correction(self.w.conn, "tok-p1", "node-4", "node-4-00000001", NOW)
        approve_stock_correction(self.w.conn, "tok-m1", "node-4", "node-4-00000001", NOW)   # 50-5=45 >= 40
        self.assertEqual(self.w.stock("SKU-A")[0], 45)
        with self.assertRaises(InvalidTransition):
            approve_stock_correction(self.w.conn, "tok-m1", "node-4", "node-4-00000002", NOW)  # 45-20=25 < 40 reserved

class X5_ReportsAndIsolation(Base):
    def test_X5_summary_tables_reconcile_with_raw_data_and_are_role_protected(self):
        self.w.deliver("SKU-A", 2, event_id="e1"); self.w.deliver("SKU-B", 1, "c2", event_id="e2")
        with self.assertRaises(Forbidden):
            reports.consolidated_report(self.w.conn, "tok-c1")
        self.assertIsNone(reports.consolidated_report(self.w.conn, "tok-m1")["as_of"])
        reports.refresh_summaries(self.w.conn, NOW)
        rep = reports.consolidated_report(self.w.conn, "tok-m1")
        raw = self.w.conn.execute("SELECT COUNT(*), SUM(total_cents) FROM orders WHERE state<>'PLACED' AND state<>'CANCELLED'").fetchone()
        self.assertEqual((sum(r["orders"] for r in rep["sales"]), sum(r["revenue_cents"] for r in rep["sales"])), (raw[0], raw[1]))
        orders.place_order(self.w.conn, "tok-c1", [("SKU-A", 1)], NOW)                  # new activity not yet in the report
        self.assertEqual(sum(r["orders"] for r in reports.consolidated_report(self.w.conn, "tok-m1")["sales"]), raw[0])
