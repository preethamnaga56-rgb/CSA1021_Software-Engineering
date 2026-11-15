# ADR-04: Judge refund approval against the policy in force at approval time

**Status:** Accepted - **revised after validation** (weakness W2, scenario X2)

## Problem
Refunds above a regional limit need a finance reviewer. Limits can change (administrator) while an approval is waiting, including approvals captured offline.

## Alternatives
1. Classify the refund once at request time (`needs_finance` flag) - *design v1*. 
2. **Evaluate the limit at approval time and record the policy version used** - *design v2*. 
3. Always require finance approval (simplest, but slows small refunds - conflict C4).

## Decision
Option 2. Approval needs: permission `refund.approve`; requester != approver; if amount > *current* regional limit then role = finance reviewer; state Requested; expected version. Approved refunds store `approval_policy_version`. Offline-queued approvals are re-validated the same way on sync and are displayed as "queued - not yet validated".

## Evidence
Design v1 failed X2: a store manager's queued approval for 34,500 was accepted after the limit was lowered to 20,000 (see `docs/validation/run_v1_expansion_initial.txt`). Design v2 rejects it (`run_v2_all_revised.txt`).

## Consequences
+ No stale authority. 
- A refund approved just before a limit change stays approved (the recorded policy version explains why). 
- Open question: whether a lowered limit should also invalidate already-approved, not-yet-executed refunds (OQ-1).
