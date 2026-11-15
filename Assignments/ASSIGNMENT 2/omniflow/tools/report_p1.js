const { D, DATA, P, H1, H2, H3, B, N, BR, SP, NOTE, T, FIG, runs, FONT } = require("./report_lib");
const { Paragraph, TextRun, AlignmentType } = D;

const cover = [
  new Paragraph({ spacing: { before: 1400, after: 120 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "CSA10 SOFTWARE ENGINEERING", bold: true, size: 28, font: FONT })] }),
  new Paragraph({ spacing: { after: 400 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Assignment 2", size: 28, font: FONT })] }),
  new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Design and Validate Requirements and Architecture for the Omnichannel Order Fulfilment Platform", bold: true, size: 36, font: FONT })] }),
  new Paragraph({ spacing: { after: 700 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "CO2 | Individual | 50 marks", size: 22, font: FONT })] }),
  T(["Field", "Entry"], [["Student name", " "], ["Register number", " "], ["Programme and section", " "], ["Submission date", " "], ["Repository (GitHub URL)", " "]], [3000, 6638], { size: 20 }),
  SP(300),
  P("**How to read the evidence labels in this report.** Every result is marked as one of: **Simulated** (stakeholder responses written for this exercise, not interviews); **Assumption** (a planning figure chosen by me, not measured); **Model result** (executed by the Python/SQLite test model in the repository on synthetic data, 29 checks); **Proposed** (designed but not yet executed). Nothing here is evidence of production performance, live inventory control or secure payment handling.", { size: 19 }),
  P("**Method in one line:** Investigate, Specify, Model, Architect, Validate, Redesign, Defend. The specification (35 requirements), the traceability matrix, the diagrams and the validation scenarios are generated from or checked against one data file (tools/spec_data.py) so they cannot silently disagree.", { size: 19 }),
  BR(),
];

const q1 = [
  H1("Q1  Investigate Stakeholder Needs and Resolve Conflicts"),
  H2("1.1  Investigation questions"),
  P("I could not interview real warehouse or finance staff, so the findings below are **Simulated** responses, written from the scenario text and typical retail practice. They are labelled as such and were used only to drive decisions that I then tested."),
  T(["#", "Question (unresolved requirement or conflict)", "Asked of"], [
    ["Q-A", "How long may stock stay reserved for an unpaid order before a customer's checkout becomes more important than a picker's certainty?", "Customer, Picker, Store manager"],
    ["Q-B", "Who may approve a refund, and above what amount must a finance reviewer decide? Can the person who requested a refund approve it?", "Finance reviewer, Support agent"],
    ["Q-C", "Which order details may a support agent see, and which must never be visible to them?", "Support agent, Administrator"],
    ["Q-D", "If the order is stored but the courier request fails, who is responsible and what does the customer see?", "Support agent, Picker, Customer"],
    ["Q-E", "What does a picker do when the scanner cannot reach the server, and who may correct stock counts afterwards?", "Picker, Store manager"],
    ["Q-F", "How fresh must management reports be, and may they slow checkout?", "Store manager, Customer"]],
    [700, 6100, 2838]),
  SP(),
  H2("1.2  Findings (Simulated responses)"),
  T(["Stakeholder", "Simulated finding", "Decision it drove"], [
    ["Customer", "Wants checkout in a few seconds, a clear 'Payment pending' state if the bank is slow, and tracking without calling support. Would accept being told 'out of stock' immediately rather than later.", "Atomic reservation (FR-05), Placed shown as payment pending, tracking (FR-13)"],
    ["Picker", "Needs a pick list that is never wrong. Dislikes finding an empty shelf for a paid order. Wants to fix counts on the spot.", "Reservation with expiry (FR-05/06); counts changed only by scan events, negatives held for a manager (FR-23)"],
    ["Support agent", "Needs order status, return status and a tracking id. Does not need and does not want card or full contact data.", "Masked projection (FR-14, NFR-08)"],
    ["Finance reviewer", "Will not release money without a named approver and an audit entry. Small refunds should not queue behind large ones.", "Amount-based approval, separation of duties (FR-16), audit (FR-18)"],
    ["Store manager", "Wants one consolidated view of sales, stock and refunds across regions; can accept five-minute-old numbers.", "Summary tables (FR-19, NFR-10)"],
    ["Administrator", "Needs to change tax, shipping and refund limits per region without redeploying, and keep the history.", "Versioned regional policy (FR-20)"]],
    [1500, 4700, 3438]),
  NOTE("Simulated. No real stakeholder was interviewed."),
  H2("1.3  Stakeholder analysis"),
  T(["Stakeholder", "Interest", "Influence on design", "Engagement"], [
    ["Finance reviewer", "High (money, audit)", "High (can block release)", "Co-design refund rules; review ADR-04"],
    ["Store manager", "High (reports, stock)", "High", "Agree report freshness and correction authority"],
    ["Customer", "High (speed, status)", "Medium (indirect)", "Usability checks; clear status text"],
    ["Picker", "High (daily use)", "Medium", "Test scanner offline behaviour"],
    ["Support agent", "Medium", "Medium", "Review masked view"],
    ["Administrator", "Medium", "High (policy, access)", "Own the permission matrix"],
    ["Engineering / operations", "High (run it)", "High (small team)", "Own worker monitoring; veto needless services"]],
    [2100, 2300, 2400, 2838]),
  H2("1.4  Conflicts and resolutions"),
  T(["ID", "Conflict", "Resolution and justification", "Acceptance implication"], [
    ["C1", "Checkout speed vs stock accuracy (customer vs picker/manager)", "Reserve stock in the same transaction as the order, with a 15-minute expiry. A conditional update is slightly slower than 'check then insert' but cannot oversell. Accept a checkout latency budget (NFR-01) instead of weakening the rule.", "12 concurrent buyers of the last unit: 1 order, 11 'out of stock'"],
    ["C2", "Support visibility vs customer privacy", "Server-side role projections: support sees status and masked contact, never payment data. Hiding fields in the UI is not enough because the API could still return them.", "Support response has no payments field; cross-customer read is 403"],
    ["C3", "Instant payment confirmation vs availability when partners are down", "An order is recorded locally as Placed (payment pending); it becomes Paid only on a verified callback. Courier and gateway calls are durable intents processed later, so a partner outage never loses an order.", "Lost or repeated callbacks cannot lose the order or show Paid early"],
    ["C4", "Fast refunds vs finance control", "Split request from approval. Up to the regional limit a finance reviewer or store manager may approve; above it only a finance reviewer; the requester never approves. Execution needs prior approval. Small refunds stay fast, large ones stay controlled.", "Agent, customer, requester and over-limit manager approvals are rejected"],
    ["C5", "Picker wants stock held until paid vs customers need availability", "Fixed 15-minute expiry (assumption, open question OQ-2). A late payment is handled explicitly (FR-08) rather than ignored.", "Expiry releases once; late payment re-reserves or opens a refund request"],
    ["C6", "Management wants live consolidated reports vs checkout performance", "Reports read pre-computed summary tables refreshed every 5 minutes; they never scan the order tables during checkout.", "Report totals equal raw totals after refresh; role-protected"],
    ["C7", "Scanners must keep working offline vs one central truth", "Bounded local buffer with unique event ids; server deduplicates; positive receipts apply, negative corrections wait for a manager; offline approvals stay 'queued - not validated'.", "Replay changes stock once; queued approval never shows Approved"]],
    [500, 2000, 4538, 2600], { size: 15 }),
  SP(),
  H3("Requests deliberately not turned into requirements"),
  B("**Support agent sees card data or full contact details:** rejected. No card data is stored at all; contact is masked."),
  B("**Customer wants instant refunds:** modified. A request is instant and its status visible, but money moves only after approval."),
  B("**Picker edits stock counts directly:** modified. Counts change through uniquely identified scan events; reductions need a manager."),
  B("**Administrator 'switch role' button for testing:** rejected. A role selector in the UI cannot change server identity; test accounts are used instead."),
  B("**Support agents approve small refunds:** rejected to keep the requester and approver roles separate."),
  H2("1.5  System boundary, actors and exclusions"),
  P("**Inside the boundary:** storefront/staff interface, REST API with its modules, the relational database, regional policy rules, scanner-ingest endpoint, report summaries and the integration worker. **Outside:** the payment gateway, the courier API, the build server (GitHub/CI) and the people. Warehouse scanners and human reviewers are **input sources** that must be validated, not trusted."),
  P("**Actors:** Customer, Picker, Support agent, Finance reviewer, Store manager, Administrator (human); Payment gateway, Courier API (external systems); Integration worker (internal system actor)."),
  P("**Excluded from the first release:** autonomous refund decisions, demand forecasting or any machine-learning model (the low-stock alert is a fixed threshold rule), public API access, real card handling, multi-currency, fraud scoring, third-party sellers."),
];

// ---------------- Q2 ----------------
const R = DATA.req;
const fr = R.filter((r) => r[1] === "Functional"), nfr = R.filter((r) => r[1] !== "Functional");
const frRows = fr.map((r) => [r[0], "**" + r[2] + ".** " + r[3], r[4], r[6] + "\nrisk " + r[7] * r[8] + "\n" + r[9], r[10]]);
const nfrRows = nfr.map((r) => [r[0], "**" + r[2] + ".** " + r[3], r[4], r[6] + "\nrisk " + r[7] * r[8] + "\n" + r[9], r[10]]);
const W5 = [750, 3800, 1250, 800, 3038];
const q2 = [
  H1("Q2  Prioritized and Testable Requirements Specification"),
  H2("2.1  Tool arrangement and justification"),
  P("I compared two arrangements for requirements tracking, documentation and UML modelling and selected the second."),
  T(["Criterion", "A. Jira + Confluence + draw.io", "B. GitHub (Issues/Projects + Markdown docs) + diagrams as code"], [
    ["Traceability", "Issue links and Confluence macros; requirement-to-test links are manual", "Requirement ids in one data file; a linter checks requirement - UML - component - scenario links (tools/trace_check.py)"],
    ["Collaboration", "Strong: comments, inline review, workflows", "Pull-request review, issue comments; less friendly to non-developers"],
    ["Version history", "Page history; weak linkage to code", "Full Git history of spec, diagrams and tests together"],
    ["Diagram support", "draw.io plugin; diagrams are binary-like and drift easily", "Graphviz/matplotlib sources regenerate PNGs; diffs are reviewable"],
    ["Accessibility", "Web UI, good keyboard support", "Plain text; alt text added to every figure in this report"],
    ["Cost", "Paid beyond small teams", "Free for a student repository"],
    ["Limitation and mitigation", "Spec and code can diverge: export to CSV", "Non-developers may find Git hard: Jira-import CSV and a generated Markdown spec are provided as a bridge"]],
    [1700, 3700, 4238]),
  P("**Selected: B**, because my deliverables already live in a Git repository and the main risk in this assignment is inconsistency between specification, models and tests, which a text-based, linted arrangement handles best. The requirement records are generated as `jira/requirements_github_issues.csv` (and a Jira import file) so they can be loaded into either tracker; `tools/create_github_issues.sh` creates one issue per requirement. **Status: Proposed for the tracker itself** - I have generated the records but have not yet loaded them into a live board in this report; a screenshot of the created issues should be attached by the student after running the script."),
  H2("2.2  Prioritization method"),
  P("MoSCoW sets the class; within a class the **risk score = impact (1-5) x likelihood (1-5)** of the requirement being missed or wrong, judged by customer harm and money at risk, orders the work. Must items are those whose failure loses money, stock integrity or confidentiality. Scores are my judgement (**Assumption**), shown in the tables."),
  H2("2.3  Functional requirements (25)"),
  T(["ID", "Requirement", "Source", "Priority", "Acceptance criterion"], frRows, W5, { size: 15 }),
  SP(),
  H2("2.4  Non-functional requirements (10)"),
  T(["ID", "Requirement", "Source", "Priority", "Acceptance threshold"], nfrRows, W5, { size: 15 }),
  NOTE("NFR-01, NFR-04, NFR-06, NFR-07, NFR-09 and NFR-10 thresholds are Assumptions or Proposed targets; none has been measured. 'Checkout should be fast' is replaced by NFR-01, which states load, hardware, warm-up, duration, percentile and limit."),
  H2("2.5  Order rules"),
  N("**Total** = sum(quantity x server price) + regional tax (basis points, half-up, integer minor units) + regional shipping; client-supplied prices are rejected.", "rules"),
  N("**Stock reservation:** atomic with order creation; free stock = on-hand - reserved and never negative; expires after 15 minutes.", "rules"),
  N("**Ownership:** an order has exactly one owner; only the owner (customer) may read it in full.", "rules"),
  N("**Permitted status changes:** Placed - Paid - Packed - Dispatched - Delivered - Closed; Cancelled only before payment; the single exception is recovery of an expired order by a verified late payment (R1).", "rules"),
  N("**Dispatch deadline:** 24 hours after payment confirmation, measured in UTC; overdue orders are reportable.", "rules"),
  N("**Duplicate callbacks:** the same (gateway id, event id) returns the existing result and has no second effect.", "rules"),
  N("**Refunds:** only for Delivered orders (or system-opened for unfulfillable payments), up to the unrefunded total; approval and execution are separate states; above the current regional limit only a finance reviewer approves.", "rules"),
  H2("2.6  Assumptions and unresolved questions"),
  T(["ID", "Assumption (planning figure, not measured)", "ID", "Unresolved question"], [
    ["A1", "Reservation expiry 15 minutes", "OQ-1", "Should lowering a refund limit also invalidate refunds already approved but not executed?"],
    ["A2", "Default refund limit 50,000 minor units per region (synthetic)", "OQ-2", "Is 15 minutes right for every region and payment method?"],
    ["A3", "Dispatch deadline 24 h after payment", "OQ-3", "Does the courier API support lookup by our correlation key?"],
    ["A4", "Reference host 2 vCPU / 4 GB for NFR-01", "OQ-4", "Regional return windows and retention period for customer addresses"],
    ["A5", "Release 1 workload 50 users, 100 events/min", "OQ-5", "Who owns dead-lettered shipments after 5 failed attempts?"],
    ["A6", "RTO 30 min, RPO 15 min", "OQ-6", "Legal basis for the masked contact data support may see"]],
    [600, 3700, 700, 4638]),
  H2("2.7  How two stakeholder conflicts changed the specification"),
  B("**C1 (speed vs accuracy)** produced FR-05 and FR-06: instead of the first idea (check stock, then insert order), the specification now demands one conditional update inside the order transaction and an expiry, and it moved the speed concern into a measurable NFR-01 threshold."),
  B("**C4 (fast refunds vs control)** produced FR-15 to FR-17: the first draft had one 'process refund' requirement; it is now three, separating request, approval (with separation of duties and a limit evaluated at approval time) and approval-gated execution. A later validation run (Q5, weakness W2) tightened FR-16 further."),
];
module.exports = { cover, q1, q2 };
