"""Generate jira/requirements.csv, jira/github_issues.csv, docs/requirements.md and docs/traceability.{csv,md} from spec_data."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import spec_data as D
ROOT = os.path.join(os.path.dirname(__file__), "..")

def rows():
    for (rid, typ, title, stmt, src, conf, moscow, imp, lik, rel, acc) in D.REQUIREMENTS:
        elems, comps, scens = D.TRACE[rid]
        yield dict(ID=rid, Type=typ, Title=title, Statement=stmt, Source=src, Conflict=conf, MoSCoW=moscow, Impact=imp,
                   Likelihood=lik, RiskScore=imp * lik, Release=rel, Acceptance=acc, UML="; ".join(elems),
                   Components="; ".join(comps), Scenarios="; ".join(scens))

def main():
    rs = list(rows())
    os.makedirs(os.path.join(ROOT, "jira"), exist_ok=True)
    # Jira CSV import: Summary / Issue Type / Priority / Description / Labels
    pri = {"Must": "Highest", "Should": "High", "Could": "Medium", "Won't": "Low"}
    with open(os.path.join(ROOT, "jira", "requirements_jira_import.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Summary", "Issue Type", "Priority", "Description", "Labels", "Custom field (Requirement ID)"])
        for r in rs:
            desc = f"{r['Statement']}\n\nSource: {r['Source']}\nAcceptance: {r['Acceptance']}\nTrace: {r['UML']} | {r['Components']} | {r['Scenarios']}"
            w.writerow([f"{r['ID']} {r['Title']}", "Story" if r["Type"] == "Functional" else "Task", pri[r["MoSCoW"]], desc,
                        f"{r['Type'].replace('-','').lower()} release-{r['Release'].lower()} {r['MoSCoW'].lower()}", r["ID"]])
    with open(os.path.join(ROOT, "jira", "requirements_github_issues.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["title", "body", "labels"])
        for r in rs:
            body = (f"**Statement:** {r['Statement']}\n\n**Source:** {r['Source']}  \n**Conflict:** {r['Conflict']}  \n"
                    f"**Priority:** {r['MoSCoW']} (risk score {r['RiskScore']})  \n**Release:** {r['Release']}\n\n"
                    f"**Acceptance criterion:** {r['Acceptance']}\n\n**Traceability:** UML `{r['UML']}` -> `{r['Components']}` -> scenarios `{r['Scenarios']}`")
            w.writerow([f"{r['ID']}: {r['Title']}", body, f"{r['Type'].lower()},{r['MoSCoW'].lower()},release-{r['Release'].lower()}"])
    with open(os.path.join(ROOT, "docs", "traceability.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Requirement", "UML elements", "Architectural components", "Validation scenarios"])
        for r in rs: w.writerow([r["ID"], r["UML"], r["Components"], r["Scenarios"]])
    with open(os.path.join(ROOT, "docs", "requirements.md"), "w") as f:
        f.write("# Requirements specification (generated from tools/spec_data.py)\n\n")
        f.write("| ID | Title | Source | Priority | Risk | Rel | Acceptance criterion |\n|---|---|---|---|---|---|---|\n")
        for r in rs:
            f.write(f"| {r['ID']} | {r['Title']} | {r['Source']} | {r['MoSCoW']} | {r['RiskScore']} | {r['Release']} | {r['Acceptance']} |\n")
    with open(os.path.join(ROOT, "docs", "traceability.md"), "w") as f:
        f.write("# Traceability matrix: Requirement -> UML element -> Component -> Validation scenario\n\n")
        f.write("| Requirement | UML | Component | Scenario |\n|---|---|---|---|\n")
        for r in rs: f.write(f"| {r['ID']} | {r['UML']} | {r['Components']} | {r['Scenarios']} |\n")
    print(f"exported {len(rs)} requirements")

if __name__ == "__main__":
    main()
