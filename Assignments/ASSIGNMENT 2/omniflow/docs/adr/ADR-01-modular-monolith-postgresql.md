# ADR-01: Modular application with one relational database for the first release

**Status:** Accepted (R1), extended unchanged for the 12-region redesign (R2)

## Problem
Order, stock reservation, payment confirmation, audit and integration intents must change together (e.g. "mark Paid + write audit + queue shipment"). The team is small and the budget for infrastructure is limited.

## Alternatives
| | A. Modular application + worker + PostgreSQL | B. Independent services + event broker |
|---|---|---|
| Consistency | One ACID transaction covers order, stock, audit, intent | Cross-service sagas, deduplication and compensation needed |
| Scale | Replicate stateless API/worker; one DB is the ceiling | Scale stock/payment/tracking independently |
| Operations | 3 deployables (nginx, api, worker) + DB | 6+ services, broker, per-service DBs, distributed tracing |
| Failure points | DB is a single point of failure | Broker, each service, and the saga logic |

## Decision
Choose **A**: one deployable FastAPI application with enforced module boundaries (identity, order, stock, payment, refund, fulfilment, policy, reporting), PostgreSQL, and a separate worker container.

## Justification
Requirements FR-05, FR-07, FR-17 and FR-18 are all "all-or-nothing" rules; a single transaction is the simplest correct mechanism. At the planned load (about 83 events/s at a 5x peak) one PostgreSQL instance is not the expected bottleneck (to be proved by tests P4/P6). Microservices would add cost and failure modes without an identified bottleneck.

## Consequences
+ Simple deployment, local transactions, easy tests. 
- Central database dependency (accepted risk R-1; mitigated by backups, offline scanner buffering). 
- Module boundaries rely on discipline: enforce with import rules/linting and code review. 
- Re-evaluate splitting a module only when a *measured* independent workload justifies it.
