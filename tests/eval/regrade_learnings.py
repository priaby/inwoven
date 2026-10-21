#!/usr/bin/env python3
"""Regrade saved W669 learnings runs from their kept worktrees, without a model call.

usage: regrade_learnings.py OUTPUT_DIR [OUTPUT_DIR ...]
Rewrites each summary.json `behavior` with the current graders and runs-table.md.
The worktree path, base commit and run date come from summary.json.
"""
import json
from pathlib import Path
import sys

from learnings_eval import CASES, grade
import datetime


def regrade(out):
    out, rows = Path(out), []
    for path in sorted(out.glob("run*/*/*/summary.json")):
        summary = json.loads(path.read_text())
        if summary.get("scenario") in CASES and summary.get("worktree") and Path(summary["worktree"]).is_dir():
            today = datetime.date.fromisoformat(summary["run_date"])
            summary["behavior"] = grade(summary["scenario"], summary, summary["worktree"], summary["base"], today)
            summary["regraded"] = True
            path.write_text(json.dumps(summary, indent=1))
        rows.append(summary)
    rows.sort(key=lambda row: (row["repeat"], row["config"], row.get("arm", "with"), row["scenario"]))
    table = ["| Run | Config | Arm | Scenario | Infrastructure | Behavior | check | guard |", "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        table.append("| run{repeat} | {config} | {arm} | {scenario} | {status} | {verdict} | {check} | {guard} |".format(
            **dict({"arm": "with"}, **row), verdict=row.get("behavior", {}).get("pass", False),
            check=row.get("used_check", False), guard=row.get("used_guard", False)))
    (out / "runs-table.md").write_text("\n".join(table) + "\n")
    return rows


if __name__ == "__main__":
    for directory in sys.argv[1:]:
        print(directory, len(regrade(directory)), "runs")
