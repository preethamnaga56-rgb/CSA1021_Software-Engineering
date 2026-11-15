"""Report-specific read model: summary tables refreshed on a schedule (keeps reports off the checkout path)."""
from .auth import authenticate, require
from .db import tx

LOW_STOCK_THRESHOLD = 5      # deterministic rule - NOT a machine-learning forecast

def refresh_summaries(conn, now):
    with tx(conn):
        conn.execute("DELETE FROM sales_summary"); conn.execute("DELETE FROM refund_summary"); conn.execute("DELETE FROM stock_summary")
        conn.execute("INSERT INTO sales_summary SELECT region, substr(created_at,1,10), COUNT(*), SUM(total_cents) "
                     "FROM orders WHERE state IN ('PAID','PACKED','DISPATCHED','DELIVERED','CLOSED') GROUP BY 1,2")
        conn.execute("INSERT INTO refund_summary SELECT o.region, "
                     "SUM(CASE WHEN r.state='EXECUTED' THEN 1 ELSE 0 END), "
                     "SUM(CASE WHEN r.state='EXECUTED' THEN r.amount_cents ELSE 0 END), "
                     "SUM(CASE WHEN r.state IN ('REQUESTED','APPROVED','FAILED') THEN 1 ELSE 0 END) "
                     "FROM refunds r JOIN orders o ON o.id=r.order_id GROUP BY o.region")
        conn.execute("INSERT INTO stock_summary SELECT sku,on_hand,reserved,CASE WHEN on_hand-reserved<=? THEN 1 ELSE 0 END FROM stock",
                     (LOW_STOCK_THRESHOLD,))
        conn.execute("INSERT OR REPLACE INTO summary_meta VALUES(1,?)", (now.isoformat(),))

def consolidated_report(conn, token):
    user = authenticate(conn, token)
    require(user, "report.view")
    meta = conn.execute("SELECT refreshed_at FROM summary_meta").fetchone()
    return {"as_of": meta["refreshed_at"] if meta else None,
            "sales": [dict(r) for r in conn.execute("SELECT * FROM sales_summary ORDER BY region,day")],
            "refunds": [dict(r) for r in conn.execute("SELECT * FROM refund_summary ORDER BY region")],
            "stock": [dict(r) for r in conn.execute("SELECT * FROM stock_summary ORDER BY sku")]}
