# ADR-05: Scale to 12 regions with versioned policies, deduplicated batch ingest and summary tables - not more services

**Status:** Accepted (R2)

## Problem
12 regions (local tax, shipping, refund rules), 500 simultaneous users, 1,000 stock/payment/scan events per minute, disconnected warehouse scanners, consolidated reports, limited budget.

## Alternatives
1. Split into microservices per module and add a broker. 
2. Shard the database by region. 
3. **Keep one deployable and one primary database; add versioned regional policy rows, a batch scan-ingest endpoint with `(node_id,event_id)` deduplication, a jobs table consumed with `FOR UPDATE SKIP LOCKED`, connection pooling, pagination and indexes, summary tables for reports, and 2-3 API replicas.**

## Decision
Option 3. Planning arithmetic (assumptions, not measurements): 1,000 events/min = 16.7/s average, 83/s at a 5x peak; 500 users at one request per 10 s = 50 req/s average, about 150 req/s at a 3x peak. These rates are modest for one tuned PostgreSQL instance, so splitting services or sharding is not justified by any identified bottleneck. Each change is tied to a limitation: policies -> FR-20; dedup + bounded buffer -> FR-21/22; human corrections -> FR-23; summary tables -> NFR-10; pooling and replicas -> NFR-09.

## Consequences
+ Small cost increase (one or two extra API containers, PgBouncer); no new technology family. 
- During a central DB outage only offline scanning continues; global approvals do not. 
- Summary tables are up to 5 minutes stale. 
- Revisit (read replica, partitioning, queue) only if tests P4/P5 show a bottleneck.
