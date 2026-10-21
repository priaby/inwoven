#!/usr/bin/env python3
"""Read and check Inwoven product files. Python 3.9+, standard library only.

Product files are preserved except init creates missing files. Hooks write disposable
pre-edit snapshots outside the repository, then remove them.
"""
import argparse
import bisect
import contextlib
import io
import hashlib
import os
import tempfile
import time
import shutil
import datetime
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import unicodedata

ALPHABET = "ABCDEFGHJKLMNPRSTUVWXYZ"
ID = r"[" + ALPHABET + r"][1-9][0-9]{2}"
ROW = re.compile(r"^\| ([A-Z]\d{3})\. ")
HEADERS = {
    "backlog": "| Item (PBI) | Core Job | Context | Status | Driver |",
    "goals": "| Goal | Measure | Horizon | Set | Achieved |",
    "users": "| User | Stage | Needs |",
    "components": "| Component | Stage | Row | Moving to | Depends on | Items |",
    "learnings": "| Lesson | Enforced by | Item | Date |",
}
LEGACY = "| Goal | Set | Achieved |"
PREFIXES = ("Sprint:", "Due:", "Accepted:", "Waiting on:")
STATUSES = ("", "To Do", "In Progress", "Done")
HORIZONS = ("Now", "Next", "Later")
STAGES = ("genesis", "custom", "product", "commodity")
FILES = ("backlog", "goals", "impact", "wardley", "learnings")
LIVE_DAYS = 90
LIVE_CAP = 30
SOON_DAYS = 14
EXPIRED_NOTE_FROM = 30


def cells(line):
    return [s.strip() for s in line.strip().strip("|").split("|")]


def separator(line, count):
    c = cells(line)
    return line.startswith("|") and len(c) == count and all(re.fullmatch(r":?-+:?", x) for x in c)


def metadata(lines):
    result = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip().strip('"')
    return result


def iso(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def key(value):
    return " ".join(value.split())


def allowed_text(value):
    return (bool(value.strip()) and len(value.strip()) <= 200 and
            not value.strip().endswith("\\") and "<br>" not in value.lower() and
            not any(c in value for c in "|\r\n") and
            not any(unicodedata.category(c) in ("Cc", "Cs", "Cf") or c in "\u2028\u2029" for c in value))


def gap_text_ok(text):
    """A Wardley gap: 1 to 80 characters with whitespace collapsed, no | , \\ or <br, no control or invisible characters."""
    return (0 < len(text) <= 80 and not any(c in text for c in "|,\\") and "<br" not in text.lower() and
            not any(unicodedata.category(c) in ("Cc", "Cs", "Cf") for c in text))


def read_backlog(lines, errors):
    start = next((n for n, line in enumerate(lines) if ROW.match(line)), -1)
    if start == -1:
        start = next((n + 2 for n, line in enumerate(lines[:-1])
                      if line.rstrip() == HEADERS["backlog"] and separator(lines[n + 1], 5)), -1)
    if start == -1:
        errors.append((1, "restore backlog header `" + HEADERS["backlog"] + "` and separator `|---|---|---|---|---|`"))
        return []
    end = start
    while end < len(lines) and ROW.match(lines[end]):
        end += 1
    top, bottom = start, end
    while top and lines[top - 1].startswith("|"):
        top -= 1
    while bottom < len(lines) and lines[bottom].startswith("|"):
        bottom += 1
    for n in range(top, bottom):
        if ROW.match(lines[n]) or all(re.fullmatch(r":?-+:?", c) for c in cells(lines[n])):
            continue
        if n + 1 < len(lines) and all(re.fullmatch(r":?-+:?", c) for c in cells(lines[n + 1])):
            continue
        if lines[n].rstrip() == HEADERS["backlog"]:
            errors.append((n + 1, "restore separator `|---|---|---|---|---|` immediately after header `" + HEADERS["backlog"] + "`"))
        else:
            errors.append((n + 1, "row must start with | <id>. <title>"))
    result, seen = [], set()
    for n in range(start, end):
        ident = ROW.match(lines[n]).group(1)
        if not re.fullmatch(ID, ident):
            errors.append((n + 1, "invalid item id " + ident))
            continue
        c = cells(lines[n])
        if len(c) != 5:
            errors.append((n + 1, "expected five cells"))
            c = (c + [""] * 5)[:5]
        if ident in seen:
            errors.append((n + 1, "duplicate id " + ident))
        seen.add(ident)
        title = c[0][5:].strip()
        parts = c[3].split("<br>")
        status, tags = parts[0].strip(), [p.strip() for p in parts[1:] if p.strip()]
        for label, value, limit in (("title", title, 80), ("context", c[2], 280)):
            if len(value) > limit:
                errors.append((n + 1, label + " has " + str(len(value)) + " characters; maximum " + str(limit)))
        for tag in tags:
            if len(tag) > 20 and not tag.startswith(PREFIXES) and tag not in ("Ready", "Reopened"):
                errors.append((n + 1, "plain tag exceeds 20 characters"))
        result.append(dict(id=ident, title=title, status=status, tags=tags, cells=c, row=lines[n], line=n + 1))
    if any(ROW.match(line) for line in lines[end:]):
        errors.append((end + 1, "item row after the table ends; join it to the table or remove the blank line above it"))
    return result


def read_goals(lines, errors):
    start = next((n for n, line in enumerate(lines) if line.rstrip() in (HEADERS["goals"], LEGACY)), -1)
    count = 3 if start >= 0 and lines[start].rstrip() == LEGACY else 5
    if start < 0 or start + 1 >= len(lines) or not separator(lines[start + 1], count):
        if start >= 0:
            errors.append((start + 1, "restore separator `" + "|" + "---|" * count + "` after header `" + lines[start] + "`"))
        else:
            errors.append((1, "restore goals header `" + HEADERS["goals"] + "` and separator `|---|---|---|---|---|`"))
        return []
    result, n = [], start + 2
    while n < len(lines) and lines[n].startswith("|"):
        c, number = cells(lines[n]), n + 1
        n += 1
        if len(c) != count:
            errors.append((number, "expected " + str(count) + " cells"))
            continue
        if count == 3:
            title, set_on, achieved = c
            measure, horizon = "", "" if achieved else "Now"
        else:
            title, measure, horizon, set_on, achieved = c
        if not title:
            errors.append((number, "empty goal"))
        for label, value in (("goal", title), ("measure", measure)):
            if len(value) > 200:
                errors.append((number, label + " exceeds 200 characters"))
        if achieved:
            if not iso(achieved):
                errors.append((number, "Achieved must be a real ISO date"))
            if horizon:
                errors.append((number, "achieved Horizon must be empty"))
        elif horizon not in HORIZONS:
            errors.append((number, "Horizon must be Now, Next or Later"))
        if achieved or horizon == "Now":
            if not iso(set_on):
                errors.append((number, "Set must be a real ISO date"))
        elif set_on:
            errors.append((number, "Next and Later Set must be empty"))
        result.append(dict(title=title, measure=measure, horizon=horizon, achieved=achieved, line=number))
    if any(line.startswith("|") for line in lines[n:]):
        errors.append((n + 1, "second goals table"))
    seen, rank, last_date = set(), -1, "9999-99-99"
    for goal in result:
        h, a, number = goal["horizon"], goal["achieved"], goal["line"]
        current = 3 if a else HORIZONS.index(h) if h in HORIZONS else -1
        if a:
            if a > last_date:
                errors.append((number, "achieved goals must be newest first"))
            last_date = a
        else:
            if h in seen:
                errors.append((number, "more than one goal at " + h))
            seen.add(h)
        if current < rank:
            errors.append((number, "open goals must be first, in Now, Next, Later order"))
        rank = current
    return result


def plural(count, word):
    return str(count) + " " + word + ("" if count == 1 else "s")


def as_today(today):
    if today is None:
        return datetime.date.today()
    return datetime.date.fromisoformat(today) if isinstance(today, str) else today


def read_learnings(lines, errors, today=None):
    """Rows that parse (Lesson and Date usable) are returned even when another cell or row is wrong."""
    today = as_today(today)
    header = HEADERS["learnings"]
    start = next((n for n, line in enumerate(lines) if line.rstrip() == header), -1)
    if start < 0 or start + 1 >= len(lines) or not separator(lines[start + 1], 4):
        if start >= 0:
            errors.append((start + 1, "restore separator `|---|---|---|---|` after header `" + header + "`"))
        else:
            errors.append((1, "restore learnings header `" + header + "` and separator `|---|---|---|---|`"))
        return []
    result, seen, live, n = [], {}, 0, start + 2
    while n < len(lines) and lines[n].startswith("|"):
        c, number = cells(lines[n]), n + 1
        n += 1
        if len(c) != 4:
            errors.append((number, "expected 4 cells"))
            continue
        lesson, enforced, item, date = c
        if not allowed_text(lesson):
            errors.append((number, "Lesson must be 1 to 200 characters on one line, no `|` or `<br>`"))
        if enforced and not allowed_text(enforced):
            errors.append((number, "Enforced by must be at most 200 characters on one line, no `|` or `<br>`"))
        if item and not re.fullmatch(ID, item):
            errors.append((number, "Item must be empty or one item id such as K417"))
        if not iso(date):
            errors.append((number, "Date must be a real ISO date, YYYY-MM-DD"))
        if not allowed_text(lesson) or not iso(date):
            continue
        age = (today - datetime.date.fromisoformat(date)).days
        row = dict(lesson=lesson, enforced=enforced, item=item, date=date, line=number, age=age,
                   live=bool(enforced) or age <= LIVE_DAYS, future=age < 0,
                   left=None if enforced else LIVE_DAYS - age)
        folded = key(lesson).casefold()
        if folded in seen:
            errors.append((number, "duplicate lesson, also line " + str(seen[folded]) +
                           "; renew that row's Date instead"))
        else:
            seen[folded] = number
        if row["live"]:
            live += 1
            if live == LIVE_CAP + 1:
                errors.append((number, str(live) + " live lessons; maximum " + str(LIVE_CAP) +
                               ". Ask the person which lesson to retire"))
        result.append(row)
    if n < len(lines) and lines[n].lstrip().startswith("|"):
        errors.append((n + 1, "table row must start with `|` in column 1"))
    for later in range(n, len(lines)):
        if lines[later].startswith("|"):
            errors.append((later + 1, "second learnings table"))
            break
    return result


def learning_notes(rows, backlog_ids=None):
    """(line, message) notes for parsed learnings rows; never errors."""
    notes = []
    for row in rows:
        if row["future"]:
            notes.append((row["line"], "note: Date is after today; read as live"))
        if backlog_ids is not None and row["item"] and row["item"] not in backlog_ids:
            notes.append((row["line"], "note: item " + row["item"] + " is not in backlog.md"))
        if row["live"] and row["left"] is not None and 0 <= row["left"] <= SOON_DAYS:
            expires = datetime.date.fromisoformat(row["date"]) + datetime.timedelta(days=LIVE_DAYS + 1)
            notes.append((row["line"], "note: expires in " + plural(row["left"] + 1, "day") + " on " +
                          expires.isoformat() + "; renew it or name a check"))
    expired = sum(1 for row in rows if not row["live"])
    if expired > EXPIRED_NOTE_FROM:
        notes.append((1, "note: " + str(expired) + " expired lessons; ask the person whether to delete the oldest"))
    return notes


def lesson_changes(before, after):
    """(action, lesson) per changed row: added, renewed, edited, deleted. Rows pair by folded lesson,
    then by equal other cells (a reworded lesson)."""
    old = {key(r["lesson"]).casefold(): r for r in before}
    new = {key(r["lesson"]).casefold(): r for r in after}
    changes = []
    for folded, row in new.items():
        was = old.get(folded)
        if was is None or (was["lesson"], was["enforced"], was["item"], was["date"]) == (
                row["lesson"], row["enforced"], row["item"], row["date"]):
            continue
        same = (was["lesson"], was["enforced"], was["item"]) == (row["lesson"], row["enforced"], row["item"])
        changes.append(("renewed" if same else "edited", row["lesson"]))
    gone = [r for k, r in old.items() if k not in new]
    fresh = [r for k, r in new.items() if k not in old]
    for row in list(fresh):
        twin = next((g for g in gone if (g["enforced"], g["item"], g["date"]) == (row["enforced"], row["item"], row["date"])), None)
        if twin:
            gone.remove(twin)
            fresh.remove(row)
            changes.append(("edited", row["lesson"]))
    changes.extend(("added", r["lesson"]) for r in fresh)
    changes.extend(("deleted", r["lesson"]) for r in gone)
    return changes


def body_start(lines):
    if lines and lines[0].strip() == "---":
        return next((n + 1 for n in range(1, len(lines)) if lines[n].strip() == "---"), len(lines))
    return 0


def read_impact(lines, errors):
    sections = []
    for n in range(body_start(lines), len(lines)):
        match = re.fullmatch(r"##(?: (.*)|[ \t]*)", lines[n])
        if match:
            sections.append(dict(goal=(match.group(1) or "").strip(), line=n + 1, body=[], actors=[]))
        elif sections:
            sections[-1]["body"].append((n + 1, lines[n]))
    seen = set()
    for section in sections:
        goal, number = section["goal"], section["line"]
        if not goal or key(goal) in seen:
            errors.append((number, "empty or duplicate goal heading"))
        seen.add(key(goal))
        if len(goal) > 200:
            errors.append((number, "goal heading exceeds 200 characters"))
        stack, roots = [], section["actors"]
        for n, line in section["body"]:
            if not line.strip():
                continue
            match = re.fullmatch(r"( *)([-*+]) (.*)", line)
            if not match:
                errors.append((n, "use list lines with spaces, never tabs or prose"))
                break
            indent, value = len(match.group(1)), match.group(3).strip()
            if not value:
                errors.append((n, "empty text"))
                break
            if stack and indent > stack[-1][0]:
                depth = len(stack) + 1
            else:
                while stack and stack[-1][0] > indent:
                    stack.pop()
                if (stack and stack[-1][0] != indent) or (not stack and roots):
                    errors.append((n, "indentation matches no parent"))
                    break
                if stack:
                    stack.pop()
                depth = len(stack) + 1
            if depth > 3:
                errors.append((n, "deeper than three levels"))
                break
            kind = "actor" if depth == 1 else "impact" if depth == 2 else "item"
            if depth == 3:
                if value.startswith("GAP:"):
                    value, kind = value[4:].strip(), "gap"
                elif re.fullmatch(ID + r"(?: .*)?", value):
                    value = value.split(" ", 1)[0]
                else:
                    errors.append((n, "leaf must be an item id, space and text, or GAP: text"))
                    break
            if kind != "item" and (not allowed_text(value) or len(value) > 80):
                errors.append((n, kind + " text is not allowed or exceeds 80 characters"))
            children = stack[-1][1]["children"] if stack else roots
            if kind == "item" and any(c["text"] == value for c in children):
                errors.append((n, "item twice in one impact"))
            node = dict(text=value, kind=kind, children=[], line=n)
            children.append(node)
            limit = (10, 10, 30)[depth - 1]
            if len(children) > limit:
                errors.append((n, "more than " + str(limit) + " " + ("actors", "impacts", "leaves")[depth - 1]))
            stack.append((indent, node))
    return sections


def wardley_cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def read_wardley(lines, errors):
    sections, current = {}, None
    for n in range(body_start(lines), len(lines)):
        line = lines[n]
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections.setdefault(current, [])
        elif line.startswith("# "):
            current = None
        elif current is not None and line.strip():
            sections[current].append((n + 1, line))
    result, seen = [], set()
    for kind in ("users", "components"):
        rows = list(sections.get(kind, []))
        while rows and "|" not in rows[0][1]:
            rows.pop(0)
        if not rows:
            continue
        number, line = rows[0]
        header = wardley_cells(HEADERS[kind])
        if [key(c).lower() for c in wardley_cells(line)] != [h.lower() for h in header]:
            errors.append((number, "restore header `" + HEADERS[kind] + "`"))
            continue
        sep = wardley_cells(rows[1][1]) if len(rows) > 1 else []
        if len(sep) != len(header) or not all(c and set(c) <= set("-: ") for c in sep):
            errors.append((number + 1, "restore separator `" + "|" + "---|" * len(header) + "` after header `" + HEADERS[kind] + "`"))
            continue
        ended = False
        for n, line in rows[2:]:
            if "|" not in line:
                ended = True
                continue
            if ended:
                errors.append((n, "table rows after text"))
            c = wardley_cells(line)
            if len(c) != len(header):
                errors.append((n, "expected " + str(len(header)) + " cells"))
                continue
            name = key(c[0])
            if not name or len(name) > 60 or "," in name or name.casefold() in seen:
                errors.append((n, "empty, duplicate or invalid name"))
            seen.add(name.casefold())
            stage = c[1].lower()
            if stage not in STAGES:
                errors.append((n, "unknown stage"))
            links = c[2] if kind == "users" else c[4]
            node = dict(name=name, kind=kind, stage=stage, links=[s.strip() for s in links.split(",") if s.strip()],
                        items=[], line=n, moving="", row=0)
            if kind == "components":
                if not re.fullmatch(r"[0-9]{1,4}", c[2]) or int(c[2]) < 1:
                    errors.append((n, "Row must be from 1 to 9999, one to four digits"))
                else:
                    node["row"] = int(c[2])
                moving = c[3].lower()
                node["moving"] = moving
                if moving and (moving not in STAGES or stage not in STAGES or STAGES.index(moving) <= STAGES.index(stage)):
                    errors.append((n, "Moving to must be a later stage"))
                node["items"], node["gaps"] = [], []
                for entry in (s.strip() for s in c[5].split(",") if s.strip()):
                    if re.fullmatch(ID, entry):
                        node["items"].append(entry)
                    elif entry.startswith("GAP:"):
                        text = " ".join(entry[4:].split())
                        if not gap_text_ok(text):
                            errors.append((n, "invalid gap text " + entry))
                        elif text.casefold() not in (g.casefold() for g in node["gaps"]):
                            node["gaps"].append(text)
                    else:
                        errors.append((n, "invalid item id " + entry))
            result.append(node)
    index = {key(n["name"]).casefold(): n for n in result}
    for node in result:
        for link in node["links"]:
            target = index.get(key(link).casefold())
            if target is None or target is node or target["kind"] == "users":
                errors.append((node["line"], "unknown, self or user link " + link))
    state = {}
    for root in result:
        name = key(root["name"]).casefold()
        if root["kind"] != "components" or name in state:
            continue
        state[name] = 1
        stack = [(root, iter(root["links"]))]
        while stack:
            node, links = stack[-1]
            for link in links:
                target = index.get(key(link).casefold())
                if target is None or target is node or target["kind"] != "components":
                    continue
                name = key(target["name"]).casefold()
                if state.get(name) == 1:
                    errors.append((node["line"], "dependency cycle"))
                elif name not in state:
                    state[name] = 1
                    stack.append((target, iter(target["links"])))
                    break
            else:
                state[key(node["name"]).casefold()] = 2
                stack.pop()
    return result


def parse(text, kind, today=None):
    # Wardley alone permits a BOM. Impact splits only CR/LF, as its lists do.
    if kind == "wardley":
        if text.startswith("\ufeff"):
            text = text[1:]
    lines = re.split(r"\r\n|\r|\n", text) if kind in ("impact", "wardley") else text.splitlines()
    errors = []
    data = read_learnings(lines, errors, today) if kind == "learnings" else globals()["read_" + kind](lines, errors)
    meta = metadata(lines)
    if meta.get("updated") and not iso(meta["updated"]):
        errors.append((1, "updated must be a real date in YYYY-MM-DD form"))
    return data, errors


def load(root, kind, today=None):
    path = root / (kind + ".md")
    return parse(path.read_text(encoding="utf-8"), kind, today) if path.exists() else (None, [])


def backlog_ids(folder):
    path = Path(folder) / "backlog.md"
    if not path.is_file():
        return None
    try:
        return {r["id"] for r in read_backlog(path.read_text(encoding="utf-8").splitlines(), [])}
    except (OSError, UnicodeError):
        return None


def check(root, paths, kind=None, today=None):
    errors, checked, notes = [], [], []
    targets = [Path(p) for p in paths] if paths else [root / (k + ".md") for k in FILES]
    for path in targets:
        if not path.exists() and not paths and path.stem != "backlog":
            continue
        try:
            detected = kind or path.stem
            if detected not in FILES:
                raise ValueError("use --kind backlog, goals, impact, wardley or learnings for another filename")
            if not path.exists():
                raise ValueError("no " + path.name + " in " + str(path.parent) + "; pass --root <folder> or run init")
            data, problems = parse(path.read_text(encoding="utf-8"), detected, today)
            if detected == "learnings":
                notes.extend((str(path), n, message) for n, message in learning_notes(data, backlog_ids(path.parent)))
            if detected == "backlog":
                notes.extend((str(path), row["line"], "note: example row; replace it with your requested work and a minted id")
                             for row in data if row["title"].startswith("Example:"))
                notes.extend((str(path), row["line"], "note: unknown status " + repr(row["status"]) +
                              "; new edits use To Do, In Progress or Done")
                             for row in data if row["status"] not in STATUSES + ("Ready",))
            errors.extend((str(path), n, msg) for n, msg in problems)
            checked.append(path.name)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append((str(path), 1, str(exc)))
    for path, n, message in notes + errors:
        print("{}:{}: {}".format(path, n, message), file=sys.stderr)
    if not errors:
        print("OK: checked " + ", ".join(checked))
    return 1 if errors else 0


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def new_ids(root, count):
    if not (root / "backlog.md").is_file():
        raise ValueError("no backlog.md in " + str(root) + "; pass --root <folder> or run init")
    if count < 1:
        raise ValueError("count must be positive")
    used = set()
    for kind in ("backlog", "impact", "wardley", "learnings"):
        path = root / (kind + ".md")
        if path.exists():
            used.update(re.findall(r"\b" + ID + r"\b", path.read_text(encoding="utf-8")))
    # History prevents reuse of ids deleted from the current documents.
    try:
        used.update(re.findall(r"\b" + ID + r"\b", git(root, "log", "--all", "--format=", "-p", "--", ".")))
    except (subprocess.CalledProcessError, OSError):
        pass  # A non-git product folder is supported too.
    available = [letter + str(number) for letter in ALPHABET for number in range(100, 1000)
                 if letter + str(number) not in used]
    if count > len(available):
        raise ValueError("not enough unused ids")
    for _ in range(count):
        chosen = secrets.randbelow(len(available))
        print(available.pop(chosen))
    return 0


def lesson_line(row):
    text = "Lesson: " + row["lesson"]
    if row["enforced"]:
        text += " [enforced by " + row["enforced"] + "]"
    text += " (" + (row["item"] or "no item") + ", " + row["date"] + ")"
    if row["live"] and row["left"] is not None and 0 <= row["left"] <= SOON_DAYS:
        text += " expires in " + plural(row["left"] + 1, "day")
    return text


def context(root, ident, today=None):
    if not re.fullmatch(ID, ident):
        raise ValueError("invalid item id " + repr(ident) + "; use one allowed letter and three digits, for example K417")
    if not root.is_dir():
        raise ValueError("no product folder " + str(root) + "; pass --root <folder> or run init")
    documents = {}
    for kind in FILES:
        try:
            data, problems = load(root, kind, today)
        except (OSError, UnicodeError) as exc:
            if kind != "learnings":
                raise
            data, problems = [], [(1, str(exc))]
        documents[kind] = data
        if data is None:
            print("Missing " + kind + ".md")
        for n, message in problems:
            print("{}:{}: {}".format(root / (kind + ".md"), n, message), file=sys.stderr)
        # A lessons file never blocks starting work: its parsed rows still print below.
        if problems and kind != "learnings":
            return 1
    row = next((r for r in documents["backlog"] or [] if r["id"] == ident), None)
    if row:
        print(row["row"])
        print("Status: " + (row["status"] or "To Do") + "; tags: " + (", ".join(row["tags"]) or "none"))
    else:
        print("Missing backlog row for " + ident)
    goals = documents["goals"] or []
    maps = sorted(documents["impact"] or [], key=lambda m: not any(key(g["title"]) == key(m["goal"]) and not g["achieved"] for g in goals))
    linked = False
    for section in maps:
        for actor in section["actors"]:
            for change in actor["children"]:
                if any(leaf["kind"] == "item" and leaf["text"] == ident for leaf in change["children"]):
                    linked = True
                    print("Goal: " + section["goal"])
                    goal = next((g for g in goals if key(g["title"]) == key(section["goal"])), None)
                    print("Measure: " + ((goal["measure"] or "missing") if goal else "missing goal in goals.md"))
                    print("Actor: " + actor["text"] + "; change: " + change["text"])
    if not linked:
        print("Missing impact link for " + ident)
    nodes = [n for n in documents["wardley"] or [] if ident in n["items"]]
    for node in nodes:
        print("Component: " + node["name"] + "; stage: " + node["stage"] +
              "; moving to: " + (node["moving"] or "none") + "; depends on: " + (", ".join(node["links"]) or "none"))
    if not nodes:
        print("Missing Wardley component link for " + ident)
    lessons = documents["learnings"] or []
    for lesson in lessons:
        if lesson["live"]:
            print(lesson_line(lesson))
    expired = sum(1 for lesson in lessons if not lesson["live"])
    if expired:
        print(plural(expired, "expired lesson") + ", not read back")
    return 0 if row else 1


def guard_lessons(root, repo, base, today):
    """Lines for learnings.md changes since base; parse problems go to stderr and rows that parse still count."""
    relative = (root / "learnings.md").resolve().relative_to(repo.resolve()).as_posix()
    exists = git(repo, "ls-tree", "--full-tree", "--name-only", base, "--", relative).strip()
    path = root / "learnings.md"
    if not exists and not path.exists():
        return []
    before, problems = parse(git(root, "show", base + ":" + relative), "learnings", today) if exists else ([], [])
    after, issues = parse(path.read_text(encoding="utf-8"), "learnings", today) if path.exists() else ([], [])
    for n, message in (problems if exists else []) + issues:
        print("{}:{}: {}".format(path, n, message), file=sys.stderr)
    found = ["lesson " + action + ": " + lesson[:60] for action, lesson in lesson_changes(before, after)]
    if issues:
        found.append("lesson rows unreadable: " + plural(len(issues), "format error") + "; run check")
    return found


def guard(root, base, today=None):
    if not shutil.which("git"):
        print("inwoven: guard needs git on PATH", file=sys.stderr)
        return 2
    repo = Path(git(root, "rev-parse", "--show-toplevel").strip())
    relative = (root / "backlog.md").resolve().relative_to(repo.resolve()).as_posix()
    # Distinguish a genuinely absent base file from an invalid revision.
    git(root, "rev-parse", "--verify", base + "^{commit}")
    exists = git(repo, "ls-tree", "--full-tree", "--name-only", base, "--", relative).strip()
    before_text = git(root, "show", base + ":" + relative) if exists else ""
    before, problems = parse(before_text, "backlog") if exists else ([], [])
    path = root / "backlog.md"
    after_text = path.read_text(encoding="utf-8") if path.exists() else ""
    after, issues = parse(after_text, "backlog") if path.exists() else ([], [])
    if problems or issues:
        for n, message in problems + issues:
            print("{}:{}: {}".format(path, n, message), file=sys.stderr)
        return 2
    old, new = {r["id"]: r for r in before}, {r["id"]: r for r in after}
    findings = []
    updated = metadata(after_text.splitlines()).get("updated", "")
    today = as_today(today).isoformat()
    if (before_text != after_text and updated and updated != today
            and updated == metadata(before_text.splitlines()).get("updated")):
        findings.append("updated: unchanged; set updated to " + today + " after this edit")
    for ident, row in new.items():
        was = old.get(ident)
        if was is None:
            findings.append("added: " + ident)
        if row["status"] == "Done" and (was is None or was["status"] != "Done"):
            findings.append("newly Done: " + ident)
        if was is not None:
            if was["status"] == "Done" and row["status"] != "Done":
                findings.append("left Done: " + ident)
            for tag in was["tags"]:
                if (tag.startswith("Accepted:") or tag == "Reopened") and tag not in row["tags"]:
                    findings.append(("Accepted removed: " if tag.startswith("Accepted:") else "Reopened removed: ") + ident)
        for prefix in ("Accepted:", "Reopened"):
            for tag in row["tags"]:
                matches = tag.startswith(prefix) if prefix.endswith(":") else tag == prefix
                if matches and (was is None or tag not in was["tags"]):
                    findings.append("newly " + prefix.rstrip(":") + ": " + ident)
    for ident in old.keys() - new.keys():
        findings.append("deleted: " + ident)
    common = old.keys() & new.keys()
    if [r["id"] for r in before if r["id"] in common] != [r["id"] for r in after if r["id"] in common]:
        findings.append("reordered: " + ", ".join(r["id"] for r in after if r["id"] in common))
    # An id replacement with otherwise identical cells is identifiable, even on a move.
    # With other edits, the added/deleted pair is still reported for confirmation.
    deleted, added_ids = old.keys() - new.keys(), new.keys() - old.keys()
    exact = False
    for ident in deleted:
        for added in added_ids:
            if [old[ident]["title"]] + old[ident]["cells"][1:] == [new[added]["title"]] + new[added]["cells"][1:]:
                findings.append("ids changed: " + ident + " -> " + added)
                exact = True
    if deleted and added_ids and not exact:
        findings.append("ids changed (possible replacements): " + ", ".join(sorted(deleted)) +
                        " -> " + ", ".join(sorted(added_ids)))
    findings.extend(guard_lessons(root, repo, base, today))
    for finding in sorted(findings):
        print(finding)
    if findings:
        print("Confirm each line against the request. Nothing was changed.")
    return 1 if findings else 0


def init(root, kinds):
    root.mkdir(parents=True, exist_ok=True)
    assets = Path(__file__).resolve().parent.parent / "assets"
    created = set()
    for kind in kinds:
        path = root / (kind + ".md")
        try:
            template = (assets / path.name).read_text(encoding="utf-8")
            template = re.sub(r"(?m)^updated: .*", "updated: " + datetime.date.today().isoformat(), template)
            with path.open("x", encoding="utf-8") as output:
                output.write(template)
            created.add(kind)
            print("Created " + str(path))
        except FileExistsError:
            print("Kept " + str(path))
    if "backlog" in created:
        print("Next: replace the example row in " + str(root / "backlog.md") +
              "; mint the first real id with new-id, then run check.")
    elif "backlog" in kinds:
        print("Existing file kept; run check.")
    return 0


def recognizes(text, kind):
    lines = re.split(r"\r\n|\r|\n", text) if kind in ("impact", "wardley") else text.splitlines()
    if kind in ("backlog", "goals", "learnings"):
        headers = (HEADERS[kind], LEGACY) if kind == "goals" else (HEADERS[kind],)
        return any(line.rstrip() in headers for line in lines)
    if kind == "wardley":
        return any(line.startswith("## ") and line[3:].strip().lower() in ("users", "components") for line in lines)
    return any(re.fullmatch(r"##(?: (.*)|[ \t]*)", line) for line in lines[body_start(lines):])


def hook_paths(event):
    # Codex uses PostToolUse and tool_input.command for apply_patch; aliases
    # Edit/Write also match it. Shell-applied patches (Bash) are out of scope.
    # Trust and schema: https://learn.chatgpt.com/docs/hooks
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return []
    if event.get("tool_name") == "apply_patch":
        patch = tool_input.get("command", "")
        if not isinstance(patch, str) or not patch.lstrip("\ufeff \t\r\n").startswith("*** Begin Patch"):
            return []
        return [value.strip() for value in
                re.findall(r"(?m)^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", patch)]
    if event.get("tool_name") in ("Edit", "Write", "MultiEdit"):
        value = tool_input.get("file_path", "")
        return [value] if isinstance(value, str) and value else []
    return []


# Per-call snapshots are local, private and disposable. session_id, tool_use_id
# and hook_event_name are documented by both hosts:
# https://code.claude.com/docs/en/hooks#common-input-fields
# https://learn.chatgpt.com/docs/hooks#common-input-fields
SNAPSHOT_BYTES = 1024 * 1024
SNAPSHOT_LIMIT = 32
SNAPSHOT_TTL = 900


def snapshot_store(event):
    session = event.get("session_id")
    if not isinstance(session, str) or not session:
        return None
    owner = hashlib.sha256(str(Path.home()).encode()).hexdigest()[:16]
    root = Path(tempfile.gettempdir()) / ("inwoven-hooks-" + owner)
    # Never follow a substitute state directory or store inside the product repo.
    if root.is_symlink():
        return None
    # TMPDIR can point into a different checkout from the edited product file.
    # Reject every checkout before creating state, not only the target's repo.
    resolved = root.resolve()
    if any((parent / ".git").exists() for parent in (resolved, *resolved.parents)):
        return None
    root.mkdir(mode=0o700, exist_ok=True)
    if os.name != "nt" and (root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077):
        return None
    now = time.time()
    files = []
    for folder in root.iterdir():
        if folder.is_symlink() or not re.fullmatch(r"[a-f0-9]{64}", folder.name):
            continue
        for saved in folder.iterdir():
            if saved.is_symlink() or not saved.is_file():
                continue
            if now - saved.stat().st_mtime > SNAPSHOT_TTL:
                saved.unlink()
            else:
                files.append(saved)
        if not any(folder.iterdir()):
            folder.rmdir()
    # Leave room for this pre call. Eviction loses a reminder, never user data.
    for saved in sorted(files, key=lambda p: p.stat().st_mtime)[:-SNAPSHOT_LIMIT + 1]:
        saved.unlink(missing_ok=True)
    directory = root / hashlib.sha256(session.encode()).hexdigest()
    if directory.is_symlink():
        return None
    directory.mkdir(mode=0o700, exist_ok=True)
    return directory


def snapshot_path(directory, path):
    return directory / (hashlib.sha256(str(path.resolve()).encode()).hexdigest() + ".json")


def save_snapshot(directory, path, event):
    call = event.get("tool_use_id")
    if not isinstance(call, str) or not call or len(call) > 256:
        return
    saved = snapshot_path(directory, path)
    saved.unlink(missing_ok=True)  # A cancelled earlier call must never be reused.
    if not path.is_file() or path.stat().st_size > SNAPSHOT_BYTES:
        return
    repo = Path(git(path.parent, "rev-parse", "--show-toplevel").strip())
    relative = path.resolve().relative_to(repo.resolve()).as_posix()
    if directory.resolve().is_relative_to(repo.resolve()):
        return
    # Untracked, ignored, unborn and newly staged files get format checks only.
    git(repo, "ls-files", "--error-unmatch", "--", relative)
    git(repo, "cat-file", "-e", "HEAD:" + relative)
    text = path.read_text(encoding="utf-8")
    if not recognizes(text, path.stem):
        return
    payload = json.dumps(dict(tool_use_id=event.get("tool_use_id"), text=text), ensure_ascii=False)
    with saved.open("x", encoding="utf-8") as stream:
        if os.name != "nt":
            os.chmod(saved, 0o600)
        stream.write(payload)


def take_snapshot(directory, path, event):
    if directory is None:
        return None
    saved = snapshot_path(directory, path)
    if not saved.is_file() or saved.is_symlink() or saved.stat().st_size > SNAPSHOT_BYTES * 2 + 1024:
        return None
    try:
        data = json.loads(saved.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved.unlink(missing_ok=True)
        return None
    if not isinstance(data, dict):
        saved.unlink(missing_ok=True)
        return None
    # A different overlapping tool call must not consume this call's snapshot.
    if data.get("tool_use_id") != event.get("tool_use_id"):
        return None
    saved.unlink()
    return data.get("text") if isinstance(data.get("text"), str) else None


def reminder(before_text, after_text):
    before, errors = parse(before_text, "backlog")
    after, issues = parse(after_text, "backlog") if after_text else ([], [])
    if errors or issues:
        return []
    old, new = {r["id"]: r for r in before}, {r["id"]: r for r in after}
    questions = []
    def ask(ident, action):
        questions.append("Did the person ask in this conversation for " + ident + " " + action + "? If not, undo it now.")
    for ident, row in new.items():
        was = old.get(ident)
        if was is None:
            ask(ident, "to be added")
        if row["status"] == "Done" and (was is None or was["status"] != "Done"):
            ask(ident, "to be Done")
        for prefix in ("Accepted:", "Reopened"):
            if any((t.startswith(prefix) if prefix.endswith(":") else t == prefix)
                   and (was is None or t not in was["tags"]) for t in row["tags"]):
                ask(ident, "to be " + prefix.rstrip(":"))
    for ident in old:
        if ident not in new:
            ask(ident, "to be deleted")
    common = old.keys() & new.keys()
    before_order = [r["id"] for r in before if r["id"] in common]
    after_order = [r["id"] for r in after if r["id"] in common]
    # Unique ids reduce LCS to an increasing subsequence of old positions.
    ranks = {ident: n for n, ident in enumerate(before_order)}
    tails, indices, parents = [], [], []
    for n, ident in enumerate(after_order):
        position = bisect.bisect_left(tails, ranks[ident])
        parents.append(indices[position - 1] if position else -1)
        if position == len(tails):
            tails.append(ranks[ident])
            indices.append(n)
        else:
            tails[position], indices[position] = ranks[ident], n
    unchanged = set()
    cursor = indices[-1] if indices else -1
    while cursor >= 0:
        unchanged.add(after_order[cursor])
        cursor = parents[cursor]
    for ident in after_order:
        if ident not in unchanged:
            ask(ident, "to be reordered")
    updated = metadata(after_text.splitlines()).get("updated", "")
    today = datetime.date.today().isoformat()
    if before_text != after_text and updated and updated != today:
        questions.append("Set updated to " + today + " for this edit. This is date housekeeping; keep the person's changes.")
    return questions


def lesson_reminder(before_text, after_text):
    before, _ = parse(before_text, "learnings") if before_text else ([], [])
    after, _ = parse(after_text, "learnings")
    return ["Did the person say yes in this conversation to this lesson (" + action + ": \"" + lesson[:60] +
            "\")? If not, undo it now." for action, lesson in lesson_changes(before, after)]


def hook():
    # Infra and foreign-file events stay silent. Recognized errors use exit 2
    # for the Claude and Codex PostToolUse stderr feedback contract.
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        paths = hook_paths(event)
    except (ValueError, AttributeError, TypeError):
        return 0
    phase = event.get("hook_event_name", "PostToolUse")
    # A patch move changes a path, not the person's row decisions. Check only
    # the destination's format, even when it has a nonstandard basename.
    moves = {}
    if event.get("tool_name") == "apply_patch" and paths:
        patch = (event.get("tool_input") or {}).get("command", "")
        moves = dict(re.findall(r"(?m)^\*\*\* Update File: (.+)\r?\n\*\*\* Move to: (.+)$", patch))
        moves = {source.strip(): target.strip() for source, target in moves.items()}
    kinds = {k + ".md": k for k in FILES}
    selected = {value: kinds.get(Path(value).name) for value in paths if Path(value).name in kinds}
    for source, target in moves.items():
        kind = kinds.get(Path(source).name) or kinds.get(Path(target).name)
        selected.pop(source, None)
        if kind:
            selected[target] = kind
    if not selected and phase != "SessionEnd":
        return 0  # Foreign files never create, sweep or inspect the snapshot store.
    try:
        directory = snapshot_store(event)
    except (OSError, ValueError):
        directory = None  # Snapshot infrastructure never suppresses format checks.
    if phase == "SessionEnd":
        if directory is not None:
            shutil.rmtree(directory)
        return 0
    errors, changes = [], []
    for value, kind in selected.items():
        try:
            path = Path(value)
            if not path.is_absolute():
                path = Path(event.get("cwd", ".")) / path
            moved = value in moves.values()
            if phase == "PreToolUse":
                if directory is not None and not moved:
                    save_snapshot(directory, path, event)
                continue
            try:
                snapshot = take_snapshot(directory, path, event)
            except OSError:
                snapshot = None  # An unreadable snapshot still gets format checks.
            if phase == "PostToolUseFailure":
                continue
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            previous = snapshot or ""
            try:
                repo = Path(git(path.parent, "rev-parse", "--show-toplevel").strip())
                relative = path.resolve().relative_to(repo.resolve()).as_posix()
                if not previous:
                    # HEAD is used only to recognize a damaged format, never for reminders.
                    previous = git(repo, "show", "HEAD:" + relative)
            except (OSError, ValueError, subprocess.CalledProcessError):
                pass
            if not moved and not recognizes(previous, kind) and not recognizes(text, kind):
                continue
            diagnostics = io.StringIO()
            invalid = 0
            if path.exists():
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(diagnostics):
                    invalid = check(path.parent, [str(path)], kind)
            if invalid:
                errors.extend(diagnostics.getvalue().splitlines())
            elif kind == "backlog" and snapshot is not None and not moved:
                # A human edit between PreToolUse and PostToolUse is indistinguishable
                # from this call's edit. Earlier uncommitted edits are preserved.
                changes.extend(reminder(snapshot, text))
            elif kind == "learnings" and snapshot is not None and not moved:
                changes.extend(lesson_reminder(snapshot, text))
            elif kind == "learnings" and not moved:
                # No snapshot (new or untracked file): compare with HEAD, or with nothing.
                changes.extend(lesson_reminder(previous, text))
        except (OSError, UnicodeError, ValueError, AttributeError, TypeError, subprocess.CalledProcessError):
            continue
    try:
        if directory is not None and not any(directory.iterdir()):
            directory.rmdir()
    except OSError:
        pass
    def capped(lines):
        # Bound both count and line width: a reordered import can be one huge line.
        unique = list(dict.fromkeys(lines))
        result = [line[:400] + ("..." if len(line) > 400 else "") for line in unique[:10]]
        if len(unique) > 10:
            result.append(str(len(unique) - 10) + " more lines omitted.")
        return result
    questions = [line for line in changes if line.startswith("Did the person")]
    housekeeping = list(dict.fromkeys(line for line in changes if not line.startswith("Did the person")))
    context = "\n".join(capped(questions) + housekeeping)
    if errors:
        print("\n".join(capped(errors)), file=sys.stderr)
        print("Run inwoven.py check FILE for full diagnostics. Nothing was changed by the hook.", file=sys.stderr)
        # Exit 2 feedback uses stderr; retain valid sibling reminders there too.
        if context:
            print(context, file=sys.stderr)
        return 2
    if changes:
        # Both hosts document this non-blocking PostToolUse schema:
        # https://code.claude.com/docs/en/hooks#posttooluse-decision-control
        # https://learn.chatgpt.com/docs/hooks#posttooluse
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
    return 0


def today_arg(value):
    if not iso(value):
        raise argparse.ArgumentTypeError("use a real date as YYYY-MM-DD")
    return value


def main():
    parser = argparse.ArgumentParser(description="Check and read Inwoven product files; create missing templates safely.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "new-id", "context", "guard", "init"):
        descriptions = dict(check="Validate product files", **{"new-id": "Mint random unused item ids"},
                            context="Read an item's goals, maps and lessons", guard="Report changes requiring a request",
                            init="Create requested missing product files")
        p = commands.add_parser(name, help=descriptions[name])
        p.add_argument("--root", type=Path, default=Path("docs/product"), help="product files directory; default: docs/product relative to the current folder")
        if name == "check":
            p.add_argument("files", nargs="*", help="explicit files; otherwise the product folder")
            p.add_argument("--kind", choices=FILES, help="format of explicitly named files")
            p.add_argument("--today", type=today_arg, help="today as YYYY-MM-DD; default: the local date")
        elif name == "new-id":
            p.add_argument("--count", type=int, default=1, help="number of unused ids; default: 1")
        elif name == "context":
            p.add_argument("id", help="item id, for example K417")
            p.add_argument("--today", type=today_arg, help="today as YYYY-MM-DD; default: the local date")
        elif name == "guard":
            p.add_argument("--base", required=True, help="git revision to compare; fetch it first")
            p.add_argument("--today", type=today_arg, help="today as YYYY-MM-DD; default: the local date")
        elif name == "init":
            p.add_argument("kinds", nargs="*", help="requested kinds: backlog, goals, impact, wardley, learnings; default: backlog")
    commands.add_parser("hook", help="Claude and Codex PostToolUse adapter: read event JSON on stdin")
    args = parser.parse_args()
    try:
        if args.command == "hook":
            return hook()
        if args.command == "check":
            if args.kind and not args.files:
                parser.error("--kind requires explicit files")
            return check(args.root, args.files, args.kind, args.today)
        if args.command == "new-id":
            return new_ids(args.root, args.count)
        if args.command == "context":
            return context(args.root, args.id, args.today)
        if args.command == "guard":
            return guard(args.root, args.base, args.today)
        if any(k not in FILES for k in args.kinds):
            parser.error("init kinds must be backlog, goals, impact, wardley or learnings")
        return init(args.root, args.kinds or ["backlog"])
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as exc:
        if args.command == "hook":
            return 0
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or "").strip()
            print("inwoven: cannot compare; check the git repository and base revision " +
                  repr(getattr(args, "base", "")) + "; fetch the base, for example with fetch-depth: 0. " + detail,
                  file=sys.stderr)
        else:
            print("inwoven: " + str(exc), file=sys.stderr)
        return 2 if args.command == "guard" else 1


if __name__ == "__main__":
    # Pipes on Windows otherwise use the local ANSI code page, even for UTF-8 files.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
