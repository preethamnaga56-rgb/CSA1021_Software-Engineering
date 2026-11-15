const { D, DATA, P, H1, H2, H3, B, N, BR, SP, NOTE, T, FIG } = require("./report_lib");

const q3a = [
  H1("Q3  UML Models and Traceability"),
  P("Six diagrams are included: use case, class, sequence (three scenarios), state machines for orders and refunds, and the component and deployment views in Q4. They use the same identifiers as the specification (UC01-UC15, class names, SEQ1-SEQ3, STM1-STM2) so the traceability matrix can refer to them. Diagram sources are in docs/diagrams/src."),
  H2("3.1  Use case model"),
  T(["Actor", "Use cases", "Notes on permission"], [
    ["Customer", "UC01 Place order; UC02 View own order and tracking; UC07 Request return (own delivered order)", "Own orders only"],
    ["Picker", "UC04 Confirm pick; UC05 Dispatch order; UC13 Sync scanner events", "Own region only"],
    ["Support agent", "UC06 Look up order (masked); UC07 Request return/refund", "No payment data; cannot approve"],
    ["Finance reviewer", "UC08 Approve or reject refund (any amount)", "Cannot approve own request"],
    ["Store manager", "UC10 View reports; UC14 Approve stock correction; UC08 (up to the current limit)", "Cannot approve above limit"],
    ["Administrator", "UC11 Configure regional policy; UC10 View reports", "Cannot approve refunds"],
    ["Payment gateway / Courier API (external)", "UC03 Confirm payment (callback); UC12 Book shipment; UC09 Execute refund (via worker)", "Signature-verified; never write to the database directly"]],
    [2200, 5000, 2438]),
  P("Authentication (UC15) is included by every protected use case. UC09 includes UC08: execution cannot happen without a prior approval."),
];
const q3land = [
  ...FIG("uml_use_case.png", "Figure 1  Use case model with system boundary (UC ids match the traceability matrix)", 960, 560),
  ...FIG("uml_class.png", "Figure 2  Domain class model. StockItem and PaymentEvent carry the database-level invariants (CHECK, UNIQUE).", 960, 560),
];
const q3b = [
  H2("3.2  Class model"),
  P("Key constraints that the model enforces: `on_hand >= reserved >= 0` on StockItem; a unique `(gateway_id, event_id)` on PaymentEvent; a unique `correlation_key` on IntegrationIntent so there is one logical shipment request per order and purpose; the unique `(node_id, event_id)` on ScanEvent; and an `approved_by` value that must exist before a RefundRequest can be Executed (also a database trigger). The refund limit is **not** a stored attribute of the request: it is derived from RegionalPolicy when approval happens (see inconsistency I2)."),
  H2("3.3  Sequence models"),
  P("SEQ1 traces a payment callback through order confirmation, shipment creation and courier synchronisation, including the duplicate-callback path and a retry after a courier timeout. SEQ2 covers refund approval, rejection, execution, failure and retry. SEQ3 (Q6) covers offline scanner synchronisation and a queued approval."),
  ...FIG("uml_seq_payment.png", "Figure 3  SEQ1: payment callback to shipment synchronisation with duplicate and retry paths", 600, 760),
  ...FIG("uml_seq_refund.png", "Figure 4  SEQ2: refund request, approval, execution, failure and retry", 600, 760),
  H2("3.4  State machines"),
  P("The order lifecycle (STM1) allows Cancelled only from Placed, either by the customer or by expiry. After validation (weakness W1) one extra, guarded transition was added: a verified late payment can move an **expired** order back to Paid if the units can be re-reserved. Authorized return is modelled through the refund machine (STM2): a Delivered order with an executed refund moves to Closed; Closed also follows the regional return window."),
  ...FIG("uml_state_order.png", "Figure 5  STM1: order lifecycle with guards (dashed = revision R1)", 640, 400),
  H3("Refund approval, rejection, execution and rollback (STM2)"),
  B("**Approval:** Requested - Approved only if the caller has `refund.approve`, is not the requester, and (for amounts above the current regional limit) is a finance reviewer; the stored version must match."),
  B("**Rejection:** Requested - Rejected with a reason; no money moves."),
  B("**Execution:** Approved or Failed (with approval retained) - Executed when the gateway succeeds. The ledger row and the order's move to Closed happen in one transaction after gateway success."),
  B("**Rollback:** if the gateway fails, nothing has been changed except the refund becoming Failed (attempts + 1). The order stays Delivered and no ledger entry exists, so there is nothing to undo. A retry reuses the approval and the gateway idempotency key; after three failed attempts the refund is flagged for manual finance handling."),
  ...FIG("uml_state_refund.png", "Figure 6  STM2: refund lifecycle", 560, 400),
  H2("3.5  Traceability matrix (Requirement - UML element - Component - Validation scenario)"),
  P("Generated from tools/spec_data.py and checked by tools/trace_check.py. Scenario ids S1-S8 and X1-X5 are executed model checks; P1-P7 are **Proposed** and not yet executed."),
  T(["Requirement", "UML element(s)", "Architectural component(s)", "Validation scenario(s)"],
    Object.entries(DATA.trace).map(([k, v]) => [k, v[0].join(", ") || "n/a (quality)", v[1].join(", "), v[2].join(", ")]), [1000, 3100, 3338, 2200], { size: 15 }),
  SP(),
  H2("3.6  Inconsistencies found and corrected"),
  T(["#", "Inconsistency", "How it was found", "Correction"], [
    ["I1", "STM1 and rule 'Cancelled only before payment' contradicted the sequence/requirement for a payment that arrives after expiry. Paid money could be ignored.", "Walkthrough of reservation expiry; then checks S7 failed on design v1 (Q5)", "Added guarded transition Cancelled to Paid (reason Expired), Order.cancel_reason in the class model, FR-08, FR-09 updated, STM1 redrawn"],
    ["I2", "Class model stored a 'needs finance' classification on RefundRequest at request time, but FR-16 and the approval state need the limit in force when approving.", "Check X2 failed on design v1: a manager's queued approval passed after the limit was lowered", "Limit derived from RegionalPolicy at approval time; approval_policy_version recorded; ADR-04; class diagram note"],
    ["I3", "NFR-07 (portability) had no validation scenario in the matrix.", "tools/trace_check.py first run reported 1 problem (docs/validation/trace_check_first_run.txt)", "Added pending scenario P7 (CI on a fresh clone) and a documented local fresh-copy run; linter now reports 0 problems"],
    ["I4", "My predicted number of courier 'create' calls in S5 (two) disagreed with SEQ1, which says the worker reconciles by correlation key before creating.", "Check S5 failed on its prediction while the behaviour was correct", "Corrected the prediction (observed 1), not the model; SEQ1 already described this"]],
    [500, 3300, 2700, 3138], { size: 15 }),
  P("Two further classic inconsistencies were **designed out from the start and then tested** rather than discovered: a browser 'payment success' page is not payment (only a verified callback marks Paid; S8), and a UI role selector does not change identity (the API accepts a session token and no role field; S6)."),
];

const q4a = [
  H1("Q4  Alternative Architectures and Justified Design"),
  H2("4.1  Two alternatives"),
  P("**Alternative A: modular application with a worker.** One deployable application with enforced module boundaries (identity, order and checkout, stock and reservation, payment callback, refund approval, fulfilment and tracking, regional policy, reporting), one PostgreSQL database, a transactional outbox and a separate integration worker. **Alternative B: independent services with an event broker.** Separate order, inventory, payment, refund, shipment and reporting services, each with its own data store, communicating through a message broker."),
  ...FIG("arch_alternative_b.png", "Figure 7  Alternative B: independent services with an event broker (structure only)", 560, 300),
  T(["Dimension", "A. Modular application + worker", "B. Services + event broker"], [
    ["Responsibilities", "Modules own rules; worker owns outbound calls", "Each service owns one capability and its data"],
    ["Communication", "In-process calls inside the application; SQL; REST to externals; outbox polling", "Asynchronous events through the broker; REST/gRPC for queries"],
    ["Data ownership", "One schema; each table is written by one module only (convention + review)", "Database per service; others read through events or APIs"],
    ["Duplicate payment prevention", "UNIQUE (gateway_id, event_id) with INSERT ... ON CONFLICT DO NOTHING inside the order transaction", "Payment service dedups by the same key, then publishes PaymentConfirmed; order service must also dedup the event (at-least-once delivery)"],
    ["Overselling the last unit", "Conditional UPDATE (free stock >= qty) in the order transaction", "Inventory service reserves; order service waits for a reservation event; saga with compensation if payment never arrives"],
    ["Scalability", "Replicate stateless API and worker; the single database is the ceiling", "Scale hot services independently; more infrastructure"],
    ["Consistency", "Strong (one ACID transaction)", "Eventual; sagas, idempotent consumers, compensations"],
    ["Availability", "Central DB is a single point of failure; partner failures isolated by outbox", "No single DB, but broker and every service are failure points"],
    ["Security", "One authorization point and one audit log", "Authorization and audit repeated or propagated per service; more trust boundaries"],
    ["Operational complexity", "Three containers and one database", "Six or more services, a broker, tracing, per-service deployment"],
    ["Likely failure points", "Database outage; worker stuck; module boundary erosion", "Lost or duplicated events; saga half-completed; schema drift between services"],
    ["Maintenance", "Schema migrations, worker monitoring, boundary discipline", "Contract versioning, broker operations, distributed debugging"]],
    [1700, 3900, 4038], { size: 15 }),
  SP(),
  H2("4.2  Comparison and selection"),
  P("Weights express the retailer's constraints (small technical team, limited budget, consistency and auditability as hard requirements). Scores (1-5) are my **judgement**, not measurements."),
  T(["Criterion", "Weight", "A", "B"], [
    ["Consistency of order, stock, audit and intents", "25", "5", "3"],
    ["Operational simplicity for a small team", "25", "5", "2"],
    ["Infrastructure cost", "20", "5", "2"],
    ["Independent scalability", "15", "3", "5"],
    ["Availability under component failure", "15", "3", "4"],
    ["**Weighted score**", "100", "**4.4**", "**3.0**"]],
    [5638, 1200, 1400, 1400]),
  P("**Selected: A.** The scenario's hard rules (single effect per callback, no oversell, auditable refunds) are naturally transactional, the team is small, and no measured workload yet needs independent scaling. B is kept as an **evolution path** if tests P4/P5 reveal an independent bottleneck. A is not 'a microservice system in one box': module boundaries are enforced so a module could later be extracted."),
];
const q4land = [
  ...FIG("arch_component_v1.png", "Figure 8  Selected architecture: component view (release 1)", 960, 560),
];
const q4b = [
  H2("4.3  Deployment view and consistency design"),
  P("Release 1 runs on one Docker host: nginx (TLS), one API container (a second only after profiling), one worker, and PostgreSQL with a persistent volume and nightly backup. External systems never write to the database directly: payment callbacks and scanner events enter through the API, which verifies them."),
  ...FIG("arch_deployment_v1.png", "Figure 9  Selected architecture: deployment view (bounded initial release)", 600, 380),
  B("**Duplicate payments:** signature check, amount check, then insert into a table with a unique (gateway id, event id); a zero-row insert means 'already processed' and the stored result is returned."),
  B("**Last unit:** `UPDATE stock SET reserved = reserved + :q WHERE sku = :s AND on_hand - reserved >= :q`; zero rows updated means out of stock. The database also carries `CHECK (on_hand >= reserved)`."),
  B("**Partner failure:** an outbox row is written in the same transaction; the worker reconciles by key before creating, then retries with back-off."),
  B("**Authorization:** server-side role from session; expected-version checks on commands."),
  H2("4.4  Architectural decision records"),
  P("Five ADRs are kept in docs/adr/ (Markdown, versioned with the code); three are required, two more record the validation revision and the redesign. Each has problem, alternatives, decision, justification and consequences."),
  T(["ADR", "Problem", "Alternatives", "Decision and justification", "Consequences"], [
    ["ADR-01 Modular application + PostgreSQL", "Related records must change together; small team; limited budget", "A. modular + worker; B. services + broker", "A: one ACID transaction covers order, stock, audit and intent; no measured need to split", "Central DB dependency; boundary discipline; revisit only with measured need"],
    ["ADR-02 Transactional outbox", "Partners fail or duplicate; retries must not duplicate effects", "Synchronous call; in-memory task; outbox; broker", "Outbox row in the order transaction + reconcile by correlation key before retry", "Worker monitoring, dead-letter handling, delayed tracking ids"],
    ["ADR-03 Server-side authorization, idempotency keys, versions", "Role switching in UI; replays; blind overwrites", "Hide controls; role in request; session role + keys + versions", "Session role and permission matrix; unique keys; expected versions; DB check and trigger as second defence", "UI handles conflicts; session and secret hardening needed"],
    ["ADR-04 Approval judged at decision time (revised)", "Refund limit can change while an approval waits", "Classify at request; evaluate at approval; always finance", "Evaluate against current policy and store the version used (X2 failed v1)", "OQ-1 remains: effect on already-approved refunds"],
    ["ADR-05 Expand without new services", "12 regions, 500 users, 1,000 events/min, tight budget", "Microservices + broker; shard by region; one DB with targeted changes", "Versioned policies, deduplicated batch ingest, jobs table, pooling, summary tables, 2-3 replicas", "Central outage limits global approvals; reports up to 5 min old"]],
    [1300, 1900, 1900, 2738, 1800], { size: 14 }),
];
module.exports = { q3a, q3land, q3b, q4a, q4land, q4b };
