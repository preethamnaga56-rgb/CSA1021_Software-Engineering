"""Generate all diagrams (Graphviz for structure, matplotlib for sequences). Black-and-white, print-friendly."""
import html, os, subprocess, textwrap
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "diagrams")
SRC = os.path.join(OUT, "src")
G = 'graph [fontname="Helvetica" fontsize=15 bgcolor=white pad=0.2]; node [fontname="Helvetica" fontsize=14]; edge [fontname="Helvetica" fontsize=12];\n'

def dot(name, body, dpi=170):
    path = os.path.join(SRC, name + ".dot")
    open(path, "w").write(body)
    subprocess.run(["dot", "-Tpng", f"-Gdpi={dpi}", path, "-o", os.path.join(OUT, name + ".png")], check=True)

# ---------------- 1. Use case ----------------
actors = {"Customer": ["UC01 Place order", "UC02 View own order and tracking"],
          "Picker": ["UC04 Confirm pick", "UC05 Dispatch order", "UC13 Sync scanner events"],
          "Support agent": ["UC06 Look up order (masked)", "UC07 Request return / refund"],
          "Finance reviewer": ["UC08 Approve or reject refund"],
          "Store manager": ["UC10 View consolidated reports", "UC14 Approve stock correction", "UC08 Approve or reject refund"],
          "Administrator": ["UC11 Configure regional policy", "UC10 View consolidated reports"]}
ucs = ["UC01 Place order", "UC02 View own order and tracking", "UC04 Confirm pick", "UC05 Dispatch order", "UC13 Sync scanner events",
       "UC06 Look up order (masked)", "UC07 Request return / refund", "UC08 Approve or reject refund", "UC10 View consolidated reports",
       "UC11 Configure regional policy", "UC14 Approve stock correction", "UC03 Confirm payment (gateway callback)",
       "UC12 Book shipment (worker)", "UC09 Execute refund (worker)", "UC15 Authenticate"]
b = "digraph UC {" + G + "rankdir=LR; splines=true; nodesep=0.25; ranksep=1.6;\n"
for a in list(actors) + ["Payment gateway (external)", "Courier API (external)", "Integration worker"]:
    b += f'"{a}" [shape=box style="rounded" label="<<actor>>\\n{a}" fillcolor=white];\n'
b += 'subgraph cluster_sys { label="OmniFlow system boundary"; style=solid; color=black; fontsize=12;\n'
for u in ucs:
    b += f'"{u}" [shape=ellipse style=filled fillcolor="#F2F2F2" label="{u.replace(" (", chr(92) + "n(")}"];\n'
b += "}\n"
for a, us in actors.items():
    for u in us: b += f'"{a}" -> "{u}" [arrowhead=none];\n'
b += '"Payment gateway (external)" -> "UC03 Confirm payment (gateway callback)" [arrowhead=none];\n'
b += '"Integration worker" -> "UC12 Book shipment (worker)" [arrowhead=none];\n"Integration worker" -> "UC09 Execute refund (worker)" [arrowhead=none];\n'
b += '"UC12 Book shipment (worker)" -> "Courier API (external)" [arrowhead=none];\n"UC09 Execute refund (worker)" -> "Payment gateway (external)" [arrowhead=none];\n'
for u in ["UC01 Place order", "UC06 Look up order (masked)", "UC08 Approve or reject refund", "UC11 Configure regional policy"]:
    b += f'"{u}" -> "UC15 Authenticate" [style=dashed label="<<include>>"];\n'
b += '"UC09 Execute refund (worker)" -> "UC08 Approve or reject refund" [style=dashed label="<<include>>\\n(approval first)"];\n'
b += "}"
dot("uml_use_case", b)

# ---------------- 2. Class diagram ----------------
def cls(n, attrs, ops=""):
    rows = "".join(f'<TR><TD ALIGN="LEFT" BORDER="0">{html.escape(a)}</TD></TR>' for a in attrs)
    return f'{n} [shape=plaintext label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3"><TR><TD BGCOLOR="#E6E6E6"><B>{n}</B></TD></TR><HR/>{rows}</TABLE>>];\n'
b = "digraph CLS {" + G + "rankdir=TB; nodesep=0.5; ranksep=0.7;\n"
b += cls("User", ["id", "role", "region", "email"])
b += cls("Order", ["id", "state", "version", "total_cents", "owner_id", "region", "policy_version", "cancel_reason", "dispatch_due_at"])
b += cls("OrderLine", ["sku", "qty", "unit_price_cents"])
b += cls("StockItem", ["sku", "on_hand", "reserved", "version", "CHECK on_hand >= reserved >= 0"])
b += cls("Reservation", ["order_id", "sku", "qty", "expires_at", "status"])
b += cls("PaymentEvent", ["gateway_id", "event_id", "order_id", "amount_cents", "UNIQUE(gateway_id,event_id)"])
b += cls("RefundRequest", ["id", "state", "amount_cents", "requested_by", "approved_by", "approval_policy_version", "attempts", "version"])
b += cls("IntegrationIntent", ["correlation_key (unique)", "purpose", "status", "attempts", "external_id"])
b += cls("AuditEvent", ["actor", "action", "order_id", "at"])
b += cls("RegionalPolicy", ["region", "version", "tax_bps", "shipping_cents", "refund_limit_cents", "return_days"])
b += cls("ScanEvent", ["node_id", "event_id", "sku", "delta", "observed_at", "policy_version", "schema_version", "status", "stale"])
for a, c, l1, l2 in [("User", "Order", "1", "0..*"), ("Order", "OrderLine", "1", "1..*"), ("Order", "Reservation", "1", "1..*"),
                     ("StockItem", "Reservation", "1", "0..*"), ("Order", "PaymentEvent", "1", "0..*"), ("Order", "RefundRequest", "1", "0..*"),
                     ("Order", "IntegrationIntent", "1", "0..*"), ("Order", "AuditEvent", "1", "0..*"),
                     ("RegionalPolicy", "Order", "1", "0..*"), ("StockItem", "ScanEvent", "1", "0..*")]:
    b += f'{a} -> {c} [arrowhead=none taillabel="{l1}" headlabel="{l2}" labeldistance=1.8];\n'
b += 'note [shape=note label="Refund approval limit is derived from RegionalPolicy at approval time (design v2);\\nno stored needs_finance value is used for authorization." fontsize=9];\nRefundRequest -> note [style=dotted arrowhead=none];\n}'
dot("uml_class", b)

# ---------------- 3. State machines ----------------
b = "digraph ST {" + G + 'rankdir=TB; nodesep=0.9; ranksep=1.1; node [shape=box style="rounded,filled" fillcolor="#F2F2F2" width=1.3]; start [shape=circle style=filled fillcolor=black label="" width=0.15]; end [shape=doublecircle style=filled fillcolor=black label="" width=0.12];\n'
b += '{rank=same; start; PLACED; PAID}\n{rank=same; CANCELLED; PACKED; DISPATCHED}\n{rank=same; DELIVERED; CLOSED; end}\n'
b += 'start -> PLACED [label="place order\\n[stock reserved]"];\n'
b += 'PLACED -> PAID [label="verified callback\\n[amount matches]"];\nPAID -> PACKED [label="confirm pick\\n[picker, same region]"];\nPACKED -> DISPATCHED [label="dispatch\\n[payment record exists]"];\n'
b += 'DISPATCHED -> DELIVERED [label="courier delivered"];\nDELIVERED -> CLOSED [label="return window ends\\nor refund executed"];\nCLOSED -> end;\n'
b += 'PLACED -> CANCELLED [label="customer cancel\\nor 15-min expiry"];\n'
b += 'CANCELLED -> PAID [style=dashed label="late payment, reason=EXPIRED\\n[re-reserve succeeds] (revision R1)" constraint=false];\n'
b += 'CANCELLED [label="CANCELLED\\n(late payment without stock:\\nsystem refund request, still Cancelled)"];\n'
b += "}"
dot("uml_state_order", b)
b = "digraph RS {" + G + 'rankdir=TB; nodesep=0.8; ranksep=1.0; node [shape=box style="rounded,filled" fillcolor="#F2F2F2" width=1.3]; start [shape=circle style=filled fillcolor=black label="" width=0.15]; end [shape=doublecircle style=filled fillcolor=black label="" width=0.12];\n'
b += '{rank=same; start; REQUESTED}\n{rank=same; REJECTED; APPROVED}\n{rank=same; FAILED; EXECUTED}\n'
b += 'start -> REQUESTED [label="agent / customer request,\\nor system (unfulfillable payment)"];\nREQUESTED -> APPROVED [label="approve [role OK for CURRENT limit,\\nrequester != approver]"];\nREQUESTED -> REJECTED [label="reject"];\n'
b += 'APPROVED -> EXECUTED [label="gateway ok\\n[approved_by not null]"];\nAPPROVED -> FAILED [label="gateway error: order stays Delivered,\\nno ledger entry (= rollback)"];\nFAILED -> EXECUTED [label="retry succeeds (approval kept)"];\nFAILED -> FAILED [tailport=s headport=s label="retry fails: attempts+1 (>=3: manual handling)"];\nEXECUTED -> end; REJECTED -> end;\n}'
dot("uml_state_refund", b)

# ---------------- 4. Sequence diagrams (matplotlib) ----------------
def sequence(name, title, parts, msgs, notes=(), width=9.8, step=0.66):
    n = len(parts); xs = [1.4 + i * (width - 2.0) / (n - 1) for i in range(n)]
    height = 1.6 + step * (len(msgs) + 1)
    fig, ax = plt.subplots(figsize=(width, height)); ax.set_xlim(0, width); ax.set_ylim(0, height); ax.axis("off")
    ax.text(0.2, height - 0.25, title, fontsize=11, fontweight="bold", va="center")
    top = height - 0.9
    for x, p in zip(xs, parts):
        ax.add_patch(FancyBboxPatch((x - 0.8, top - 0.2), 1.6, 0.55, boxstyle="round,pad=0.02", fc="#E6E6E6", ec="black"))
        ax.text(x, top + 0.075, p, ha="center", va="center", fontsize=9)
        ax.plot([x, x], [top - 0.2, 0.2], color="black", lw=0.8, ls=(0, (5, 4)))
    y = top - 0.7
    for m in msgs:
        kind = m[0]
        if kind == "frame":      # ("frame", text)
            ax.text(0.2, y + 0.05, m[1], fontsize=9, fontweight="bold", style="italic", va="center",
                    bbox=dict(fc="#F2F2F2", ec="black", pad=2)); y -= step * 0.8; continue
        _, a, b, text = m[:4]; dashed = len(m) > 4 and m[4]
        x1, x2 = xs[parts.index(a)], xs[parts.index(b)]
        if a == b:
            ax.annotate("", xy=(x1, y - 0.2), xytext=(x1 + 0.0, y + 0.15), arrowprops=dict(arrowstyle="->", lw=1, connectionstyle="arc3,rad=-1.6"))
            ax.text(x1 + 0.45, y - 0.02, text, fontsize=8.5, va="center")
        else:
            ax.annotate("", xy=(x2, y), xytext=(x1, y), arrowprops=dict(arrowstyle="->", lw=1.1, ls="--" if dashed else "-"))
            ax.text((x1 + x2) / 2, y + 0.08, text, fontsize=8.5, ha="center", va="bottom", bbox=dict(fc="white", ec="none", pad=0.6))
        y -= step
    for t in notes:
        ax.text(0.2, 0.05, t, fontsize=8.5, style="italic", va="bottom")
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)

sequence("uml_seq_payment", "SEQ1  Payment callback -> order confirmation -> shipment booking -> courier synchronisation (with retry)",
 ["Payment gateway", "API (Payment\nCallback)", "PostgreSQL", "Integration\nWorker", "Courier API"],
 [("m", "Payment gateway", "API (Payment\nCallback)", "1 POST /callback {gateway_id,event_id,amount} + signature"),
  ("m", "API (Payment\nCallback)", "API (Payment\nCallback)", "2 verify signature, amount"),
  ("m", "API (Payment\nCallback)", "PostgreSQL", "3 BEGIN; INSERT payment_event ON CONFLICT DO NOTHING"),
  ("m", "API (Payment\nCallback)", "PostgreSQL", "4 order Paid + audit + INSERT outbox intent; COMMIT"),
  ("m", "API (Payment\nCallback)", "Payment gateway", "5 200 OK (order recorded; shipment sync Pending)", True),
  ("frame", "alt  duplicate event id (step 3 inserts 0 rows)"),
  ("m", "API (Payment\nCallback)", "Payment gateway", "3b 200 OK with existing result - no second effect", True),
  ("frame", "loop  worker poll"),
  ("m", "Integration\nWorker", "PostgreSQL", "6 read due intent (Pending/Retry)"),
  ("m", "Integration\nWorker", "Courier API", "7 find shipment by correlation key"),
  ("m", "Integration\nWorker", "Courier API", "8 not found -> create shipment (key=shipment:order)"),
  ("frame", "alt  timeout or error"),
  ("m", "Courier API", "Integration\nWorker", "9a timeout / 5xx (shipment may exist)", True),
  ("m", "Integration\nWorker", "PostgreSQL", "10a status Retry, attempts+1, back-off; order stays Paid"),
  ("m", "Integration\nWorker", "Courier API", "11a later: find by key -> found -> reuse tracking id (no 2nd shipment)"),
  ("frame", "alt  success"),
  ("m", "Courier API", "Integration\nWorker", "9b tracking id", True),
  ("m", "Integration\nWorker", "PostgreSQL", "10b intent Done, order.tracking_id set, audit"),
 ], notes=["Messages 6-11 run after the callback has already been acknowledged: courier availability never blocks recording the order."], width=9.8)

sequence("uml_seq_refund", "SEQ2  Refund request -> approval -> execution -> failure and retry (rollback = no ledger entry, order not closed)",
 ["Support agent", "API (Refund\nApproval)", "Finance reviewer\n/ Manager", "PostgreSQL", "Integration\nWorker", "Payment gateway"],
 [("m", "Support agent", "API (Refund\nApproval)", "1 request refund (order, amount)"),
  ("m", "API (Refund\nApproval)", "PostgreSQL", "2 order Delivered? amount <= unrefunded total? -> Requested + audit"),
  ("m", "Finance reviewer\n/ Manager", "API (Refund\nApproval)", "3 approve (session token only)"),
  ("m", "API (Refund\nApproval)", "PostgreSQL", "4 role vs CURRENT limit; requester != approver; version check"),
  ("frame", "alt  role not allowed / above limit / self-approval"),
  ("m", "API (Refund\nApproval)", "Finance reviewer\n/ Manager", "4a 403 - state unchanged", True),
  ("frame", "alt  allowed"),
  ("m", "API (Refund\nApproval)", "PostgreSQL", "4b Approved, approved_by, policy version, audit"),
  ("m", "Integration\nWorker", "PostgreSQL", "5 read Approved or Failed refund (approved_by not null)"),
  ("m", "Integration\nWorker", "Payment gateway", "6 refund(idempotency key = refund:id)"),
  ("frame", "alt  gateway error"),
  ("m", "Payment gateway", "Integration\nWorker", "6a error / timeout", True),
  ("m", "Integration\nWorker", "PostgreSQL", "7a Failed, attempts+1 (>=3 -> manual); NO ledger row; order stays Delivered"),
  ("m", "Integration\nWorker", "Payment gateway", "8a retry with the same key (approval reused)"),
  ("frame", "alt  success"),
  ("m", "Payment gateway", "Integration\nWorker", "6b reference", True),
  ("m", "Integration\nWorker", "PostgreSQL", "7b Executed + ledger row + order Closed + audit (one transaction)"),
 ], width=9.8)

sequence("uml_seq_offline", "SEQ3  Offline scanner buffering, reconnect, deduplicated sync and a queued refund approval",
 ["Scanner node", "Manager's\nclient", "API", "PostgreSQL"],
 [("frame", "Disconnected"),
  ("m", "Scanner node", "Scanner node", "1 buffer event {node_id, event_id, sku, delta, observed_at, policy_v, schema_v} (bounded)"),
  ("m", "Manager's\nclient", "Manager's\nclient", "2 queue approval locally; UI shows 'queued - not yet validated'"),
  ("frame", "Reconnected"),
  ("m", "Scanner node", "API", "3 POST batch (oldest first, <=500 events)"),
  ("m", "API", "PostgreSQL", "4 INSERT scan_event ON CONFLICT DO NOTHING (node_id,event_id)"),
  ("m", "API", "PostgreSQL", "5 positive delta -> apply; negative -> PendingReview; stale flag if >24 h"),
  ("m", "API", "Scanner node", "6 ack list (applied + duplicates)", True),
  ("m", "Scanner node", "Scanner node", "7 delete only acknowledged events"),
  ("m", "Manager's\nclient", "API", "8 submit queued approval with authenticated session"),
  ("m", "API", "PostgreSQL", "9 re-validate role, requester, CURRENT regional limit, version"),
  ("m", "API", "Manager's\nclient", "10 Approved - or 403 with reason (limit lowered while offline)", True),
 ], width=9.8, notes=["If the acknowledgement (6) is lost, the node resends; step 4 turns every replay into a no-op."])

# ---------------- 5. Architecture alternatives, component, deployment ----------------
b = "digraph ALTB {" + G + 'rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#F2F2F2"]; compound=true;\n'
b += 'UI [label="Web UI / scanners"]; GW [label="API gateway"]; BR [label="Event broker\\n(Kafka / RabbitMQ)" shape=cylinder];\n'
for s in ["Order service\\n(own DB)", "Inventory service\\n(own DB)", "Payment service\\n(own DB)", "Refund service\\n(own DB)", "Shipment service\\n(own DB)", "Reporting service\\n(read store)"]:
    b += f'"{s}" [fillcolor=white];\nGW -> "{s}"; "{s}" -> BR [dir=both];\n'
b += 'UI -> GW; "Payment service\\n(own DB)" -> PG [label="callbacks" dir=both]; PG [label="Payment gateway\\n(external)" fillcolor=white];\n"Shipment service\\n(own DB)" -> CR [dir=both]; CR [label="Courier API\\n(external)" fillcolor=white];\n}'
dot("arch_alternative_b", b)

b = "digraph COMP {" + G + 'rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#F2F2F2"]; newrank=true;\n'
b += 'UI [label="Customer / staff UI\\n(React)"]; SC [label="Warehouse scanner\\nnode"]; RP [label="Reverse proxy\\nTLS, routing"];\n'
b += 'subgraph cluster_app { label="Modular application (FastAPI) - one deployable"; style=solid; fontsize=11;\n'
for m in ["Identity & Access", "Order & Checkout", "Stock & Reservation", "Payment Callback", "Refund Approval", "Fulfilment & Tracking", "Regional Policy", "Reporting"]:
    b += f'"{m}" [fillcolor=white];\n'
b += "}\n"
b += 'DB [label="PostgreSQL\\norders, stock, payment events,\\nrefunds, audit, outbox" shape=cylinder fillcolor=white]; WK [label="Integration Worker\\n(outbox poller)"];\n'
b += 'PGW [label="Payment gateway\\n(external, sandbox)" fillcolor="#D9D9D9"]; CO [label="Courier API\\n(external)" fillcolor="#D9D9D9"]; CI [label="GitHub + CI\\nbuild, test, images" fillcolor="#D9D9D9"];\n'
b += 'UI -> RP [label="HTTPS"]; SC -> RP [label="HTTPS (batch)"]; RP -> "Identity & Access" [label="REST"];\n'
for m in ["Identity & Access", "Order & Checkout", "Stock & Reservation", "Payment Callback", "Refund Approval", "Fulfilment & Tracking", "Regional Policy", "Reporting"]:
    b += f'"{m}" -> DB [arrowhead=none color="#808080"];\n'
b += '"Order & Checkout" -> "Stock & Reservation" [style=dashed label="in-process call"]; "Payment Callback" -> "Order & Checkout" [style=dashed];\n'
b += 'DB -> WK [label="poll outbox" dir=both]; WK -> CO [label="book shipment"]; WK -> PGW [label="refund"]; PGW -> RP [label="signed callback" style=dashed]; CI -> RP [style=dotted label="deploy" arrowhead=none];\n}'
dot("arch_component_v1", b)

b = "digraph DEP {" + G + 'rankdir=TB; node [shape=box style="filled" fillcolor="#F2F2F2"];\n'
b += 'subgraph cluster_c { label="Client devices"; CL [label="Browsers, scanners" fillcolor=white]; }\n'
b += 'subgraph cluster_h { label="Single host (Docker network) - initial release"; fontsize=11;\n'
b += 'NG [label="nginx container\\n:443 -> api"]; A1 [label="api container 1\\nstateless FastAPI"]; A2 [label="api container 2\\n(added only after profiling)" style="dashed,filled" fillcolor=white]; W [label="worker container\\noutbox sender"]; PGC [label="postgres container\\npersistent volume\\nnightly backup" shape=cylinder fillcolor=white];\n}\n'
b += 'subgraph cluster_x { label="External systems"; GWX [label="Payment gateway" fillcolor="#D9D9D9"]; CRX [label="Courier API" fillcolor="#D9D9D9"]; }\n'
b += 'REG [label="Image registry / GitHub Actions" fillcolor="#D9D9D9"];\n'
b += 'CL -> NG [label="HTTPS"]; NG -> A1; NG -> A2 [style=dashed]; A1 -> PGC [label="SQL"]; A2 -> PGC [style=dashed]; W -> PGC [label="SQL"]; W -> CRX; W -> GWX; GWX -> NG [style=dashed label="callback"]; REG -> NG [style=dotted label="docker pull" arrowhead=none constraint=false];\n}'
dot("arch_deployment_v1", b)

b = "digraph DEP2 {" + G + 'rankdir=TB; node [shape=box style="filled" fillcolor="#F2F2F2"];\n'
b += 'subgraph cluster_r { label="12 regions - clients"; fontsize=11; CL [label="Browsers (500 users planned)\\nScanner nodes with bounded local buffer\\n(events: node id + event id + observed_at + policy version)" fillcolor=white]; }\n'
b += 'subgraph cluster_h { label="Central deployment (still one database) - Day-4 redesign"; fontsize=11;\n'
b += 'NG [label="nginx / load balancer\\nrate limits, batch endpoint /scan-events"]; A1 [label="api replica 1"]; A2 [label="api replica 2"]; A3 [label="api replica 3\\n(only if profiling shows CPU-bound)" style="dashed,filled" fillcolor=white];\n'
b += 'PB [label="PgBouncer\\nconnection pool" fillcolor=white]; DB [label="PostgreSQL primary\\n+ regional_policy versions\\n+ scan_events (PK node_id,event_id)\\n+ jobs table (SKIP LOCKED)\\n+ summary tables" shape=cylinder fillcolor=white];\n'
b += 'W [label="worker container(s)\\noutbox + scan-batch jobs"]; RF [label="report refresher\\n(scheduled, every 5 min)"]; BK [label="WAL archive + nightly backup" shape=note fillcolor=white]; RR [label="read replica\\n(ONLY if P5 test fails)" style="dashed,filled" shape=cylinder fillcolor=white];\n}\n'
b += 'subgraph cluster_x { label="External"; GWX [label="Payment gateway" fillcolor="#D9D9D9"]; CRX [label="Courier API" fillcolor="#D9D9D9"]; }\n'
b += 'CL -> NG [label="HTTPS"]; NG -> A1; NG -> A2; NG -> A3 [style=dashed]; A1 -> PB; A2 -> PB; A3 -> PB [style=dashed]; PB -> DB; W -> DB [label="SQL"]; RF -> DB; DB -> BK; DB -> RR [style=dashed label="stream"]; W -> CRX; W -> GWX; GWX -> NG [style=dashed label="callback"];\n}'
dot("arch_deployment_v2", b)
print("diagrams written:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))
