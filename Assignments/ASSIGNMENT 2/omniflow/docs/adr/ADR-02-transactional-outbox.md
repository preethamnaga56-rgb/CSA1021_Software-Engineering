# ADR-02: Record external calls as durable intents (transactional outbox) and reconcile before retry

**Status:** Accepted

## Problem
The payment gateway and courier API can be unavailable or send duplicates. Local order recording must not depend on them, and a retry after a timeout must not create a second shipment or refund.

## Alternatives
1. Call the courier synchronously inside the callback request.
2. Fire-and-forget in-memory background task.
3. **Outbox row written in the same transaction as the order change; a worker sends it.**
4. Message broker publishing from the application.

## Decision
Option 3. `payment callback` commits `payment_event + order Paid + audit + outbox(correlation_key=shipment:<order>)` atomically. The worker first calls `find_by_key(correlation_key)` on the courier, creates only if absent, stores the tracking id, and uses exponential back-off (2^n minutes), dead-lettering after 5 attempts. Refund execution uses the same pattern with a gateway idempotency key `refund:<id>`.

## Justification
Option 1 couples availability and loses orders (violates NFR-03). Option 2 loses intents on restart. Option 4 adds a broker without need and still requires an outbox for atomicity. Reconciliation by key handles the "created but response lost" case (test S5).

## Consequences
+ Orders are never lost when partners fail; retries are safe. 
- Needs worker monitoring and a dead-letter view for support; delayed tracking ids are shown as "Pending sync". 
- The partner must support lookup by our key or idempotency keys (open question OQ-3).
