# OmniFlow - Omnichannel Order Fulfilment (CSA10 Software Engineering, Assignment 2)

Requirements, UML models, architecture decisions and an **executable test model** for an order-fulfilment platform
(checkout, stock reservation, payment callbacks, picking, dispatch, courier tracking, refunds), including the
Day-4 redesign for 12 regions, 500 users, 1,000 events/min and disconnected scanners.

> **Honest scope.** `src/omniflow` is a *test model* (Python standard library + SQLite standing in for PostgreSQL) on **synthetic data**.
> It demonstrates rule logic, not production security, throughput or live payment/courier integration.
> Payment gateway and courier are controlled fakes. Stakeholder responses in the report are **simulated**.

## Run it
```bash
python3 run_validation.py          # 29 checks -> docs/validation/validation_results.md
python3 -m unittest discover -s tests -v
python3 tools/trace_check.py       # requirement <-> UML <-> component <-> scenario linter
python3 tools/export_spec.py       # regenerate CSV/Markdown spec from tools/spec_data.py
python3 tools/make_diagrams.py     # regenerate diagrams (needs Graphviz `dot` and matplotlib)
```
Requires Python 3.10+. No third-party packages for the model and tests.

## Layout
| Path | Content |
|---|---|
| `src/omniflow/` | auth, orders, refunds, outbox, offline (scanner), reports, policies, cluster (replica simulation) |
| `tests/` | scenarios S1-S8 (base) and X1-X5 (expansion) |
| `tools/spec_data.py` | single source of truth for the 35 requirements and the traceability matrix |
| `jira/` | CSVs to import requirements into Jira or GitHub Issues |
| `docs/adr/` | architecture decision records ADR-01..05 |
| `docs/diagrams/` | PNG diagrams + Graphviz sources |
| `docs/validation/` | initial (v1) and revised (v2) runs, trace-check output, results |
| `docs/` | requirements.md, traceability.md/csv, the assignment report (docx) |

## Tool arrangement
Specification and decisions live in this repository (docs-as-code, full Git history), requirements are tracked as GitHub Issues
(`jira/requirements_github_issues.csv`, helper `tools/create_github_issues.sh`), with a Jira import file provided as an alternative.
Diagrams are generated from code so they cannot drift from the specification.

## Status of evidence
Executed here: 29 model checks (see `docs/validation/validation_results.md`). **Not executed:** P1-P7 (load, restore drill, usability, PostgreSQL
concurrency, GitHub CI run) - listed in `tools/spec_data.py`.
