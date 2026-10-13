#!/usr/bin/env python3
"""Read and check Inwoven product files. Python 3.9+, standard library only.

All commands preserve files except init, which creates missing files exclusively.
"""
import argparse
import contextlib
import io
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
}
LEGACY = "| Goal | Set | Achieved |"
PREFIXES = ("Sprint:", "Due:", "Accepted:", "Waiting on:")
STATUSES = ("", "To Do", "In Progress", "Done")
HORIZONS = ("Now", "Next", "Later")
STAGES = ("genesis", "custom", "product", "commodity")
FILES = ("backlog", "goals", "impact", "wardley")


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
        errors.append((end + 1, "second item block"))
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
                node["items"] = [s.strip() for s in c[5].split(",") if s.strip()]
                for ident in node["items"]:
                    if not re.fullmatch(ID, ident):
                        errors.append((n, "invalid item id " + ident))
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


def parse(text, kind):
    # Wardley alone permits a BOM. Impact splits only CR/LF, as its lists do.
    if kind == "wardley":
        if text.startswith("\ufeff"):
            text = text[1:]
    lines = re.split(r"\r\n|\r|\n", text) if kind in ("impact", "wardley") else text.splitlines()
    errors = []
    data = globals()["read_" + kind](lines, errors)
    meta = metadata(lines)
    if meta.get("updated") and not iso(meta["updated"]):
        errors.append((1, "updated must be a real date in YYYY-MM-DD form"))
    return data, errors


def load(root, kind):
    path = root / (kind + ".md")
    return parse(path.read_text(encoding="utf-8"), kind) if path.exists() else (None, [])


def check(root, paths, kind=None):
    errors, checked, notes = [], [], []
    targets = [Path(p) for p in paths] if paths else [root / (k + ".md") for k in FILES]
    for path in targets:
        if not path.exists() and not paths and path.stem != "backlog":
            continue
        try:
            detected = kind or path.stem
            if detected not in FILES:
                raise ValueError("use --kind backlog, goals, impact or wardley for another filename")
            if not path.exists():
                raise ValueError("no " + path.name + " in " + str(path.parent) + "; pass --root <folder> or run init")
            data, problems = parse(path.read_text(encoding="utf-8"), detected)
            if detected == "backlog":
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
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def new_ids(root, count):
    if not (root / "backlog.md").is_file():
        raise ValueError("no backlog.md in " + str(root) + "; pass --root <folder> or run init")
    if count < 1:
        raise ValueError("count must be positive")
    used = set()
    for kind in ("backlog", "impact", "wardley"):
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


def context(root, ident):
    if not re.fullmatch(ID, ident):
        raise ValueError("invalid item id " + repr(ident) + "; use one allowed letter and three digits, for example K417")
    if not root.is_dir():
        raise ValueError("no product folder " + str(root) + "; pass --root <folder> or run init")
    documents = {}
    for kind in FILES:
        data, problems = load(root, kind)
        documents[kind] = data
        if data is None:
            print("Missing " + kind + ".md")
        for n, message in problems:
            print("{}:{}: {}".format(root / (kind + ".md"), n, message), file=sys.stderr)
        if problems:
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
    return 0 if row else 1


def guard(root, base):
    repo = Path(git(root, "rev-parse", "--show-toplevel").strip())
    relative = (root / "backlog.md").resolve().relative_to(repo.resolve()).as_posix()
    # Distinguish a genuinely absent base file from an invalid revision.
    git(root, "rev-parse", "--verify", base + "^{commit}")
    exists = git(repo, "ls-tree", "--full-tree", "--name-only", base, "--", relative).strip()
    before, problems = parse(git(root, "show", base + ":" + relative), "backlog") if exists else ([], [])
    path = root / "backlog.md"
    after, issues = parse(path.read_text(encoding="utf-8"), "backlog") if path.exists() else ([], [])
    if problems or issues:
        for n, message in problems + issues:
            print("{}:{}: {}".format(path, n, message), file=sys.stderr)
        return 2
    old, new = {r["id"]: r for r in before}, {r["id"]: r for r in after}
    findings = []
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
    for finding in sorted(findings):
        print(finding)
    if findings:
        print("Confirm each line against the request. Nothing was changed.")
    return 1 if findings else 0


def init(root, kinds):
    root.mkdir(parents=True, exist_ok=True)
    assets = Path(__file__).resolve().parent.parent / "assets"
    for kind in kinds:
        path = root / (kind + ".md")
        try:
            template = (assets / path.name).read_text(encoding="utf-8")
            template = re.sub(r"(?m)^updated: .*", "updated: " + datetime.date.today().isoformat(), template)
            with path.open("x", encoding="utf-8") as output:
                output.write(template)
            print("Created " + str(path))
        except FileExistsError:
            print("Kept " + str(path))
    if "backlog" in kinds:
        print("Next: replace the example row in " + str(root / "backlog.md") +
              "; mint the first real id with new-id, then run check.")
    return 0


def recognizes(text, kind):
    lines = re.split(r"\r\n|\r|\n", text) if kind in ("impact", "wardley") else text.splitlines()
    if kind in ("backlog", "goals"):
        headers = (HEADERS[kind], LEGACY) if kind == "goals" else (HEADERS[kind],)
        return any(line.rstrip() in headers for line in lines)
    if kind == "wardley":
        return any(line.startswith("## ") and line[3:].strip().lower() in ("users", "components") for line in lines)
    return any(re.fullmatch(r"##(?: (.*)|[ \t]*)", line) for line in lines[body_start(lines):])


def hook():
    # Infra and foreign-file events stay silent. Only recognized format errors
    # use exit 2, the Claude PostToolUse stderr feedback contract.
    if not shutil.which("git"):
        return 0
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
            return 0
        value = (event.get("tool_input") or {}).get("file_path", "")
        if not isinstance(value, str) or not value:
            return 0
        path = Path(value)
        if path.name not in [k + ".md" for k in FILES]:
            return 0
        if not path.is_absolute():
            path = Path(event.get("cwd", ".")) / path
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        previous = ""
        try:
            repo = Path(git(path.parent, "rev-parse", "--show-toplevel").strip())
            relative = path.resolve().relative_to(repo.resolve()).as_posix()
            previous = git(repo, "show", "HEAD:" + relative)
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass
        candidates = [path.stem]
        kind = next((k for k in candidates if recognizes(previous, k)), None)
        kind = kind or next((k for k in candidates if recognizes(text, k)), None)
        if kind is None:
            return 0
        diagnostics = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(diagnostics):
            failed = check(path.parent, [str(path)], kind)
        if failed:
            print(diagnostics.getvalue(), end="", file=sys.stderr)
            return 2
        return 0
    except (OSError, UnicodeError, ValueError, AttributeError, TypeError):
        return 0


def main():
    parser = argparse.ArgumentParser(description="Check and read Inwoven product files; create missing templates safely.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "new-id", "context", "guard", "init"):
        descriptions = dict(check="Validate product files", **{"new-id": "Mint random unused item ids"},
                            context="Read an item's goals and maps", guard="Report changes requiring a request",
                            init="Create requested missing product files")
        p = commands.add_parser(name, help=descriptions[name])
        p.add_argument("--root", type=Path, default=Path("docs/product"), help="product files directory; default: docs/product relative to the current folder")
        if name == "check":
            p.add_argument("files", nargs="*", help="explicit files; otherwise the product folder")
            p.add_argument("--kind", choices=FILES, help="format of explicitly named files")
        elif name == "new-id":
            p.add_argument("--count", type=int, default=1, help="number of unused ids; default: 1")
        elif name == "context":
            p.add_argument("id", help="item id, for example K417")
        elif name == "guard":
            p.add_argument("--base", required=True, help="git revision to compare; fetch it first")
        elif name == "init":
            p.add_argument("kinds", nargs="*", help="requested kinds: backlog, goals, impact, wardley; default: backlog")
    commands.add_parser("hook", help="Claude PostToolUse adapter: read event JSON on stdin")
    args = parser.parse_args()
    try:
        if args.command == "hook":
            return hook()
        if args.command == "check":
            if args.kind and not args.files:
                parser.error("--kind requires explicit files")
            return check(args.root, args.files, args.kind)
        if args.command == "new-id":
            return new_ids(args.root, args.count)
        if args.command == "context":
            return context(args.root, args.id)
        if args.command == "guard":
            return guard(args.root, args.base)
        if any(k not in FILES for k in args.kinds):
            parser.error("init kinds must be backlog, goals, impact or wardley")
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
    sys.exit(main())
