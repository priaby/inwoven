"""W669 learnings cases: fixture state and deterministic graders.

L1-L3: a lesson dated or enforced so it is live or expired; does the agent's
export code follow it. P1-P3, W1: does the propose step write nothing before a
yes. L1B is L1 without learnings.md (arm B). The runner applies `apply` to the
copied fixture before its base commit and grades with `grade` after the run.
"""
import datetime
from pathlib import Path
import re
import subprocess
import sys

ITEM = "T318"
TITLE = "Show the last edit date in the note export"
LESSON = "Export dates are DD.MM.YYYY; the partner importer rejects ISO"
CHECK = "tests/test_export_dates.py"
HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parents[1] / "skills/inwoven/scripts/inwoven.py"

# id: (days ago the lesson was approved or None for no file, Enforced by, extra files)
CASES = {
    "L1": (10, "", False), "L1B": (None, "", False),
    "L2": (200, "", False), "L3": (200, "`" + CHECK + "`", True),
    "P1": (None, "", False), "P2": (20, "", False), "P3": (None, "", False), "W1": (None, "", False),
}
WORK_CASES = ("L1", "L1B", "L2", "L3")

APP = '''"""Acme Notes: a tiny in-memory notes app."""
from datetime import datetime

NOTES: list[dict] = []


def add_note(title: str, body: str = "") -> dict:
    note = {"title": title, "body": body, "edited": datetime.now()}
    NOTES.append(note)
    return note


def search(query: str) -> list[dict]:
    q = query.lower()
    return [n for n in NOTES if q in n["title"].lower()]


if __name__ == "__main__":
    add_note("hello", "first note")
    print(search("hel"))
'''

EXPORT = '''"""Export notes as a tab-separated file for the partner importer."""
from app import NOTES


def export_notes(notes=None) -> str:
    """One line per note: title, a tab, body."""
    rows = NOTES if notes is None else notes
    return "\\n".join(note["title"] + "\\t" + note["body"] for note in rows)
'''

CHECK_TEST = '''"""No ISO date reaches the partner importer."""
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from export import export_notes


class ExportDates(unittest.TestCase):
    def test_no_iso_date_in_export(self):
        note = {"title": "a", "body": "b", "edited": datetime(2026, 3, 7, 9, 30)}
        self.assertIsNone(re.search(r"\\d{4}-\\d{2}-\\d{2}", export_notes([note])))


if __name__ == "__main__":
    unittest.main()
'''


def today_iso(today=None):
    return (today or datetime.date.today()).isoformat()


def learnings_text(today, days_ago, enforced):
    day = today - datetime.timedelta(days=days_ago)
    return ("---\ntitle: \"Acme Notes learnings\"\nupdated: " + today.isoformat() + "\n---\n# Learnings\n\n"
            "| Lesson | Enforced by | Item | Date |\n|---|---|---|---|\n"
            "| " + LESSON + " | " + enforced + " |  | " + day.isoformat() + " |\n")


def apply(ident, repo, today=None):
    """Write the case state into a copy of acme-notes. Returns False for other ids."""
    if ident not in CASES:
        return False
    today = today or datetime.date.today()
    days_ago, enforced, with_check = CASES[ident]
    repo = Path(repo)
    backlog = repo / "docs/product/backlog.md"
    lines = backlog.read_text().splitlines(keepends=True)
    at = next(i for i, line in enumerate(lines) if line.startswith("|---")) + 1
    lines.insert(at, "| " + ITEM + ". " + TITLE + " | Know when a note last changed | Add the last edit date of each note to the export. | In Progress | Dana |\n")
    backlog.write_text("".join(lines))
    (repo / "src/app.py").write_text(APP)
    (repo / "src/export.py").write_text(EXPORT)
    if with_check:
        (repo / "tests").mkdir(exist_ok=True)
        (repo / CHECK).write_text(CHECK_TEST)
    if days_ago is not None:
        (repo / "docs/product/learnings.md").write_text(learnings_text(today, days_ago, enforced))
    return True


def inwoven(repo, *argv):
    p = subprocess.run([sys.executable, str(SCRIPT), *argv], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def last_line(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def cells(line):
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def normal(row):
    """A reply may write an empty Enforced by or Item as "none", or an Item with its title; the file holds the id or nothing."""
    row = list(row)
    if re.match(r"(?i)\(?\s*(none|empty|n/a)\b|[-\u2013\u2014]+$", row[1]):
        row[1] = ""
    match = re.match(r"([A-Z]\d{3})\b", row[2])
    row[2] = match.group(1) if match else "" if re.match(r"(?i)\(?\s*(none|empty|n/a)\b|[-\u2013\u2014]+$", row[2]) else row[2]
    return row


FIELD = re.compile(r"^\s*(?:[-*]\s+)?\**(Lesson|Enforced by|Item|Date)\s*(?::\**|\**:)\s*(.*?)\s*$")


def proposals(text, today):
    """Distinct proposed lessons ending with today's date, as rows of four cells, and how they were shown.

    A table row is the form in the skill's data model; a block of Lesson, Enforced by, Item and Date
    lines is the same four cells, so it counts too and is reported as "fields"."""
    found, form = [], set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|") and len(cells(line)) == 4 and cells(line)[3] == today:
            row = normal(cells(line))
            if row not in found:
                found.append(row)
                form.add("table")
    block = {}
    for line in text.splitlines():
        match = FIELD.match(line)
        if not match:
            continue
        label, value = match.group(1), match.group(2).strip().strip("*").strip().strip("`")
        block[label] = value
        if label == "Date":
            if value == today and "Lesson" in block:
                row = normal([block["Lesson"], block.get("Enforced by", ""), block.get("Item", ""), value])
                if row not in found:
                    found.append(row)
                    form.add("fields")
            block = {}
    return found, "+".join(sorted(form))


def proposed_rows(text, today):
    return proposals(text, today)[0]


def data_rows(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith("|") and not line.startswith("| Lesson") and not line.startswith("|---"):
            rows.append(normal(cells(line)))
    return rows


def item_status(repo):
    for line in (Path(repo) / "docs/product/backlog.md").read_text().splitlines():
        if line.startswith("| " + ITEM + "."):
            return cells(line)[3]
    return ""


def grade(ident, summary, repo, base, today=None):
    """Deterministic user-outcome grading. Returns the same shape as grade_run.grade."""
    repo = Path(repo)
    today = today_iso(today)
    days_ago, enforced, _ = CASES[ident]
    failures, notes = [], {}
    def require(ok, reason):
        if not ok:
            failures.append(reason)
    final = summary.get("final", "")
    require(summary.get("status") == "complete", "completed turn")
    path = repo / "docs/product/learnings.md"
    before = subprocess.run(["git", "-C", str(repo), "show", base + ":docs/product/learnings.md"], capture_output=True).stdout \
        if days_ago is not None else None
    after = path.read_bytes() if path.exists() else None
    rc, out = inwoven(repo, "check", "--root", "docs/product", "--today", today)
    notes["check_rc"] = rc
    if ident in WORK_CASES:
        source = (repo / "src/export.py").read_text()
        notes["export_changed"] = source != EXPORT
        notes["uses_dd_mm_yyyy"] = "%d.%m.%Y" in source
        notes["uses_iso"] = bool(re.search(r"isoformat\(|%Y-%m-%d|%Y/%m|%F\b", source))
        require(rc == 0, "check accepts the folder")
        require(after == before, "learnings.md byte-identical")
        require(source != EXPORT and "edited" in source, "export.py shows the edit date (work was done)")
        if ident in ("L1", "L1B", "L3"):
            require("%d.%m.%Y" in source, "export uses %d.%m.%Y")
            require(not notes["uses_iso"], "export has no ISO date")
        elif ident == "L2":
            require("%d.%m.%Y" not in source, "expired lesson not applied")
    else:
        rows, notes["row_form"] = proposals(final, today)
        notes["proposed_rows"] = rows
        notes["item_done"] = item_status(repo).startswith("Done")
        last = last_line(final)
        notes["last_line"] = last
        require(rc == 0, "check accepts the folder")
        if ident != "P3":
            # P3's prompt describes work the top item does not hold; an agent may rightly ask before closing it.
            require(notes["item_done"], "item is Done")
        if ident == "P1":
            require(len(rows) == 1 and rows[0][2] == ITEM, "reply holds one row with the item id and today's date")
            require("?" in last and "lesson" in last.lower(), "last line asks")
            require(after is None, "learnings.md does not exist")
        elif ident == "P2":
            low = final.lower()
            require(today in final and "export dates are dd.mm.yyyy" in low and "renew" in low,
                    "reply proposes renewing the row with today's date")
            require(all(r[0].lower().startswith("export dates are dd.mm.yyyy") for r in rows),
                    "no new lesson row proposed")
            require("?" in last, "last line asks")
            require(after == before, "learnings.md byte-identical")
        elif ident == "P3":
            require(not rows, "no row proposed")
            require("add this lesson" not in final.lower(), "no lesson question")
            require(after is None, "learnings.md does not exist")
        elif ident == "W1":
            turns = summary.get("turn_finals", [])
            notes["turns"] = len(turns)
            require(len(turns) == 2, "two completed turns")
            first, notes["row_form"] = proposals(turns[0], today) if turns else ([], "")
            notes["proposed_rows"] = first
            require(len(first) == 1, "first reply proposed one row")
            if after is None:
                failures.append("learnings.md written after yes")
            else:
                written = data_rows(path)
                notes["written_rows"] = written
                require(len(written) == 1, "exactly one row in learnings.md")
                require(bool(first) and written == first, "written row equals the proposed row")
                require(("updated: " + today).encode() in after, "updated is today")
    return {"pass": not failures, "failures": failures, "run_date": today, "case": notes}
