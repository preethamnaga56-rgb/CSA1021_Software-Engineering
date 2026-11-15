"""Traceability linter: checks that requirements, UML elements, components and validation scenarios agree."""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import spec_data as D

ROOT = os.path.join(os.path.dirname(__file__), "..")
def test_scenarios():
    found = {}
    for f in glob.glob(os.path.join(ROOT, "tests", "test_*.py")):
        for m in re.finditer(r"def (test_([SX]\d+)_\w+)", open(f).read()):
            found.setdefault(m.group(2), []).append(m.group(1))
    return found

def check():
    problems, notes = [], []
    ids = [r[0] for r in D.REQUIREMENTS]
    tests = test_scenarios()
    uml = set(D.USE_CASES) | set(D.CLASSES) | set(D.SEQUENCES) | set(D.STATES)
    for rid in ids:
        if rid not in D.TRACE:
            problems.append(f"{rid}: no traceability row"); continue
        elems, comps, scens = D.TRACE[rid]
        if not elems and not rid.startswith("NFR"):
            problems.append(f"{rid}: functional requirement maps to no UML element")
        for e in elems:
            if e not in uml: problems.append(f"{rid}: unknown UML element {e}")
        for c in comps:
            if c not in D.COMPONENTS: problems.append(f"{rid}: unknown component {c}")
        for s in scens:
            if s not in tests and s not in D.NOT_EXECUTED: problems.append(f"{rid}: scenario {s} is neither an executed test nor a listed pending scenario")
        if not scens:
            problems.append(f"{rid}: no validation scenario")
        elif not any(s in tests for s in scens):
            notes.append(f"{rid}: only pending (not executed) scenarios {scens}")
    for r in D.TRACE:
        if r not in ids: problems.append(f"{r}: traceability row without a requirement")
    used = {s for _, _, sc in D.TRACE.values() for s in sc}
    for s in tests:
        if s not in used: problems.append(f"scenario {s}: executed test not linked to any requirement")
    for s in D.EXECUTED:
        if s not in tests: problems.append(f"scenario {s}: listed as executed but no test found")
    for e in sorted(uml):
        if not any(e in v[0] for v in D.TRACE.values()):
            notes.append(f"UML element {e} is not traced to any requirement")
    return problems, notes

if __name__ == "__main__":
    problems, notes = check()
    print(f"requirements: {len(D.REQUIREMENTS)}  executed scenario groups: {len(test_scenarios())}")
    for p in problems: print("PROBLEM:", p)
    for n in notes: print("NOTE:   ", n)
    print("RESULT:", "FAIL" if problems else "PASS", f"({len(problems)} problems, {len(notes)} notes)")
    sys.exit(1 if problems else 0)
