# Requirements specification (generated from tools/spec_data.py)

| ID | Title | Source | Priority | Risk | Rel | Acceptance criterion |
|---|---|---|---|---|---|---|
| FR-01 | Session identity | Administrator, Finance reviewer | Must | 20 | R1 | Given a support agent's session, when the request claims role=finance_reviewer, then the server still treats the caller as support agent; a forged token returns 401. |
| FR-02 | Role-based authorization | Finance reviewer, Administrator | Must | 20 | R1 | For each of the 6 roles, every prohibited critical command returns 403 and changes no data. |
| FR-03 | Place order | Customer | Must | 16 | R1 | Quantity 0 or a client-supplied price is rejected; two submissions with key K create exactly one order. |
| FR-04 | Price and tax | Customer, Finance reviewer | Must | 12 | R1 | Synthetic basket 2 x 2,500 in region R1 (18% tax, 5,000 shipping) totals 10,900 and stores policy version 1. |
| FR-05 | Atomic stock reservation | Customer, Picker | Must | 20 | R1 | With 1 unit left and 12 concurrent buyers, exactly 1 order is created and 11 buyers receive 'out of stock'. |
| FR-06 | Reservation expiry | Picker, Store manager | Should | 12 | R1 | Running the expiry job twice releases the reserved units once; free stock equals on-hand. |
| FR-07 | Verified, idempotent payment confirmation | Finance reviewer, Engineering | Must | 25 | R1 | The same callback sent 10 times sequentially and 10 times concurrently yields 1 payment, 1 intent, 1 'paid' audit entry. |
| FR-08 | Payment that cannot be fulfilled | Finance reviewer | Must | 15 | R1 | Late payment with the unit resold leaves stock unchanged and opens one Requested refund by 'system'; with stock available the order becomes Paid. |
| FR-09 | Guarded order lifecycle | Engineering | Must | 16 | R1 | Any jump (e.g. Placed to Dispatched) is rejected; a second picker using a stale version is rejected. |
| FR-10 | Pick list and pick confirmation | Picker | Should | 9 | R1 | A picker of another region receives 403 for the order; own-region paid order appears on the pick list. |
| FR-11 | Dispatch guard and deadline | Picker, Store manager | Must | 15 | R1 | Dispatch of a Placed or Paid-not-picked order is rejected and leaves state and stock unchanged; due time equals paid time + 24 h. |
| FR-12 | Durable shipment booking | Engineering, Customer | Must | 16 | R1 | After a courier outage then a timeout-after-create, exactly one courier shipment exists and the order keeps its Paid state throughout. |
| FR-13 | Customer tracking | Customer | Should | 9 | R1 | Customer B requesting customer A's order receives 403. |
| FR-14 | Masked support view | Support agent | Must | 16 | R1 | Support response contains 'a***@e***' not the e-mail, and no 'payments' field. |
| FR-15 | Return and refund request | Support agent, Customer | Must | 12 | R1 | Request on a non-delivered order or above the order total is rejected. |
| FR-16 | Amount-based refund approval | Finance reviewer, Store manager | Must | 20 | R1 | Manager approval of an amount above the limit returns 403; the same approval queued before the limit was lowered is rejected on sync. |
| FR-17 | Approval-gated refund execution | Finance reviewer | Must | 15 | R1 | Execution of a Requested refund is rejected (also by a database trigger); after one gateway failure the retry succeeds with one ledger row. |
| FR-18 | Audit trail | Finance reviewer, Administrator | Must | 12 | R1 | After the duplicate-callback scenario exactly one 'order.paid' entry exists. |
| FR-19 | Consolidated reports | Store manager | Should | 9 | R1 | After refresh, summary totals equal raw aggregates; a customer calling the report returns 403. |
| FR-20 | Versioned regional policy | Administrator | Should | 9 | R1 | Changing the limit creates version 2; orders keep the version they were priced with. |
| FR-21 | Offline scanner buffer | Picker | Must | 12 | R2 | The 1,001st event on a 1,000-capacity node raises 'buffer full' and the buffer still holds 1,000 events. |
| FR-22 | Scan-event deduplication | Picker, Engineering | Must | 16 | R2 | A 500-event batch replayed after a lost acknowledgement changes stock by 0 the second time. |
| FR-23 | Human-approved stock corrections | Store manager | Must | 12 | R2 | A picker cannot approve; a manager's approval that would drop below reserved is rejected. |
| FR-24 | Queued approvals stay pending | Finance reviewer | Must | 15 | R2 | Before sync the display never reads 'Approved'; after the limit is lowered the server rejects a manager's queued approval. |
| FR-25 | Stale observations | Store manager | Should | 9 | R2 | An event observed 30 h earlier is stored with stale=1. |
| NFR-01 | Checkout response time | Customer | Must | 12 | R1 | Load-test report records host, dataset size, warm-up, duration and p95. |
| NFR-02 | Consistency | Engineering, Picker | Must | 20 | R1 | Zero oversold units and zero duplicate payments in the trial. |
| NFR-03 | Local availability under partner failure | Customer, Engineering | Must | 16 | R1 | Count of recorded callbacks equals callbacks sent; intents remain Pending/Retry. |
| NFR-04 | Recovery | Store manager | Should | 8 | R1 | A restore drill meets both targets and is recorded. |
| NFR-05 | Security | Administrator, Finance reviewer | Must | 15 | R1 | Role matrix test passes; repository scan finds no secrets or card numbers. |
| NFR-06 | Usability and accessibility | Customer, Support agent | Should | 9 | R1 | Keyboard walkthrough passes; 3 of 3 test users meet the time target. |
| NFR-07 | Portability and maintainability | Engineering | Should | 6 | R1 | CI is green on a fresh clone. |
| NFR-08 | Privacy | Support agent, Administrator | Must | 12 | R1 | Field-level response checks pass for both roles. |
| NFR-09 | Scalability (expansion) | Store manager | Must | 12 | R2 | Expansion load-test report records p95 and drain lag. |
| NFR-10 | Report freshness and isolation | Store manager | Should | 9 | R2 | Interference test shows <= 10% change. |
