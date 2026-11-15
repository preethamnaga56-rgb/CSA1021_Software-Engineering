#!/usr/bin/env bash
# Creates one GitHub Issue per requirement from jira/requirements_github_issues.csv using the GitHub CLI.
# Usage: gh auth login && ./tools/create_github_issues.sh owner/repo
set -euo pipefail
REPO="${1:?usage: $0 owner/repo}"
python3 - "$REPO" <<'PY'
import csv, subprocess, sys
repo = sys.argv[1]
with open("jira/requirements_github_issues.csv", newline="") as f:
    for row in csv.DictReader(f):
        labels = row["labels"].split(",")
        for l in labels:
            subprocess.run(["gh", "label", "create", l, "--repo", repo, "--force"], check=False, capture_output=True)
        cmd = ["gh", "issue", "create", "--repo", repo, "--title", row["title"], "--body", row["body"]]
        for l in labels: cmd += ["--label", l]
        subprocess.run(cmd, check=True)
        print("created", row["title"])
PY
