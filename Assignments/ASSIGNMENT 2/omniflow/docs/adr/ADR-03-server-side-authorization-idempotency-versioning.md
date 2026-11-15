# ADR-03: Server-side authorization, idempotency keys and optimistic versioning

**Status:** Accepted

## Problem
A support agent must not gain finance privileges by choosing another role in the UI; repeated callbacks, double-clicks and two pickers on one screen must not cause double effects or blind overwrites.

## Alternatives
1. Hide controls in the UI by role. 
2. Pass the role in each request. 
3. **Role from the authenticated server-side session; permission matrix checked by every command; idempotency keys; expected-version checks.**

## Decision
Option 3. Commands accept a session token, never a role. Checkout carries a client idempotency key (unique per owner). Payment callbacks are keyed by (gateway id, event id) with a UNIQUE constraint. State-changing commands carry the expected `version` and fail with a conflict when stale. Database defences back up the application: `CHECK(on_hand >= reserved)` and a trigger forbidding `EXECUTED` without `approved_by`.

## Justification
Options 1 and 2 are client-controlled and therefore bypassable (tests S6). Version checks give "stale versions cannot silently overwrite accepted state" (S4).

## Consequences
+ Clear authorization point; replay-safe commands. 
- The UI must handle 409 conflicts; session management and token storage need hardening (NFR-05); secrets must come from the environment.
