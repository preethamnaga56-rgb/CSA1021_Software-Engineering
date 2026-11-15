"""Run every validation scenario and write docs/validation/validation_results.md (+ .json).

    python run_validation.py

Results describe the in-memory/SQLite TEST MODEL on synthetic data only."""
import json, os, platform, re, sys, unittest
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tests")); sys.path.insert(0, os.path.join(HERE, "src")); sys.path.insert(0, os.path.join(HERE, "tools"))
import spec_data as D
from helpers import METRICS

class Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.rows = []
    def addSuccess(self, t): super().addSuccess(t); self.rows.append((t._testMethodName, "PASS"))
    def addFailure(self, t, e): super().addFailure(t, e); self.rows.append((t._testMethodName, "FAIL"))
    def addError(self, t, e): super().addError(t, e); self.rows.append((t._testMethodName, "ERROR"))

def main():
    suite = unittest.defaultTestLoader.discover(os.path.join(HERE, "tests"))
    runner = unittest.TextTestRunner(resultclass=Collect, verbosity=0, stream=open(os.devnull, "w"))
    res = runner.run(suite)
    rows = sorted(res.rows)
    groups = {}
    for name, status in rows:
        sid = re.match(r"test_([SX]\d+)_", name).group(1)
        groups.setdefault(sid, []).append((name, status))
    out = ["# Validation results (test model, synthetic data)", "",
           f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} on Python {platform.python_version()} / SQLite {__import__('sqlite3').sqlite_version} / {platform.system()}.",
           "", "| Scenario | Description | Checks | Result |", "|---|---|---|---|"]
    order = sorted(groups, key=lambda s: (s[0] != "S", int(s[1:])))
    for sid in order:
        st = [s for _, s in groups[sid]]
        out.append(f"| {sid} | {D.EXECUTED.get(sid, '')} | {len(st)} | {'PASS' if all(s == 'PASS' for s in st) else 'FAIL'} |")
    out += ["", f"**{res.testsRun} checks run, {len(res.failures)} failures, {len(res.errors)} errors.**", "", "## Individual checks", ""]
    out += [f"- `{n}` - {s}" for n, s in rows]
    out += ["", "## Local timing (model only - NOT a capacity claim)", ""]
    out += [f"- {k}: {v}" for k, v in METRICS.items()] or ["- none"]
    out += ["", "## Not executed (still required before implementation)", ""]
    out += [f"- {k}: {v}" for k, v in D.NOT_EXECUTED.items()]
    open(os.path.join(HERE, "docs", "validation", "validation_results.md"), "w").write("\n".join(out) + "\n")
    json.dump({"checks": rows, "metrics": METRICS, "failures": len(res.failures), "errors": len(res.errors)},
              open(os.path.join(HERE, "docs", "validation", "validation_results.json"), "w"), indent=2)
    print("\n".join(out[:out.index('## Individual checks')]))
    return 1 if (res.failures or res.errors) else 0

if __name__ == "__main__":
    sys.exit(main())
