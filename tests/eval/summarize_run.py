#!/usr/bin/env python3
"""Record full tool evidence, format checks and infra status for one real-agent run.

usage: summarize_run.py KIND EVENTS REPO BASE CHECKER_ROOT [SKILL_DIR]
"""
import json
from pathlib import Path
import re
import subprocess
import sys


def tool_calls(commands):
    """Extract direct and assigned-variable calls from full command evidence."""
    variables, calls = {}, []
    assignment = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|[^;\s]+)")
    for index, command in enumerate(commands):
        for match in assignment.finditer(command):
            name, value = match.groups()
            value = value.strip("\"'")
            if value.endswith("inwoven.py"):
                variables[name] = value
            else:
                variables.pop(name, None)
        expanded = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)",
                          lambda m: variables.get(m.group(1) or m.group(2), m.group()), command)
        for match in re.finditer(r"inwoven\.py[\"']?\s+(check|guard|new-id|context)\b", expanded):
            calls.append(dict(index=index, tool=match.group(1), command=command))
    return calls


def summarize(kind, events, repo, base, checker_root, skill_dir=None):
    repo = Path(repo)
    commands, final, completed, skill_tool = [], "", False, False
    read_paths, evidence, instruction_reads, edits = set(), [], [], []
    def record(name, inp):
        nonlocal skill_tool
        if name == "Skill" and "inwoven" in json.dumps(inp):
            skill_tool = True
            evidence.append("Skill tool: " + json.dumps(inp))
        command = inp.get("command") or inp.get("file_path") or inp.get("path") or ""
        if not isinstance(command, str):
            command = json.dumps(command)
        index = len(commands)
        commands.append(name + ": " + command)
        if name in ("Edit", "Write", "MultiEdit", "apply_patch") or re.search(
                r"\bapply_patch\b|\.write_(?:text|bytes)\(|\bsed\b[^;\n]* -i\b|\bcat\s+>", command):
            edits.append(dict(index=index, tool=name, command=command))
        reader = name in ("Read", "read_file", "read") or bool(re.search(r"\b(cat|sed|head|tail|less|more)\b", command))
        if reader:
            for path in re.findall(r"(?:[\w./-]+/)?(?:AGENTS(?:\.override)?|CLAUDE|SKILL)\.md", command):
                read_paths.add(path)
                if path.endswith(("AGENTS.md", "CLAUDE.md")):
                    segment = next((part for part in re.split(r"[;\n]|&&", command) if path in part), command)
                    truncated = bool(re.search(r"\b(head|tail|grep|rg)\b|\bsed\b[^;]* -n\b", segment))
                    limited = any(inp.get(key) is not None for key in ("offset", "limit", "num_lines"))
                    instruction_reads.append(dict(index=index, path=path, whole=not (truncated or limited), command=command))
            if "SKILL.md" in command and ("inwoven" in command):
                evidence.append("read: " + command)
    for line in Path(events).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if kind == "claude":
            if d.get("type") == "assistant":
                for block in d.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        record(block.get("name", ""), block.get("input") or {})
            elif d.get("type") == "result":
                completed = not d.get("is_error", False)
                final = d.get("result") or ""
        else:
            if d.get("type") == "turn.completed":
                completed = True
            item = d.get("item") or {}
            if d.get("type") == "item.completed":
                if item.get("type") == "command_execution":
                    record("bash", {"command": item.get("command", "")})
                elif item.get("type") == "agent_message":
                    final = item.get("text", "")
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout
    def rows(text):
        found, order = {}, []
        for line in text.splitlines():
            m = re.match(r"\| ([A-Z]\d{3})\. ", line)
            if m:
                ident = m.group(1)
                found[ident] = [c.strip() for c in line.strip().strip("|").split("|")]
                order.append(ident)
        return found, order
    bf = repo / "docs/product/backlog.md"
    before, ob = rows(git("show", base + ":docs/product/backlog.md"))
    after, oa = rows(bf.read_text() if bf.exists() else "")
    def check(argv):
        p = subprocess.run(argv, cwd=repo, capture_output=True, text=True)
        return {"rc": p.returncode, "out": p.stdout + p.stderr}
    script = Path(skill_dir or repo / ".agents/skills/inwoven") / "scripts/inwoven.py"
    checks = {name: check([sys.executable, str(script), "check", "--kind", name,
                           "docs/product/" + name + ".md"])
              for name in ("backlog", "goals", "impact", "wardley")}
    bundled = check([sys.executable, str(script), "check", "--root", "docs/product"])
    guard = check([sys.executable, str(script), "guard", "--base", base, "--root", "docs/product"])
    commits = git("log", "--format=%H %s", base + "..HEAD").splitlines()
    calls = tool_calls(commands)
    tools = {name: any(call["tool"] == command for call in calls)
             for name, command in (("check", "check"), ("guard", "guard"), ("new_id", "new-id"), ("context", "context"))}
    read_agents = sorted(p for p in read_paths if p.endswith("AGENTS.md"))
    read_claude = sorted(p for p in read_paths if p.endswith("CLAUDE.md"))
    read_skill = sorted(p for p in read_paths if p.endswith("SKILL.md") and ("inwoven" in p or evidence))
    refs = sorted(set(re.findall(r"references/([a-z-]+\.md)", "\n".join(commands))))
    return dict(status="complete" if completed and final else "infra_failure", completed=completed,
                skill_tool=skill_tool, skill_loaded=skill_tool or bool(evidence), skill_evidence=evidence,
                skill_reads=read_skill, agents_reads=read_agents, claude_reads=read_claude,
                instruction_reads=instruction_reads, edit_events=edits,
                first_instruction_read=instruction_reads[0]["index"] if instruction_reads else None,
                first_edit=edits[0]["index"] if edits else None,
                instructions_before_edit=(all(r["index"] < edits[0]["index"] for r in instruction_reads)
                                          if instruction_reads and edits else None),
                inwoven_calls=calls,
                read_agents=bool(read_agents), read_claude=bool(read_claude), refs_read=refs,
                commits=commits, commit_count=len(commits), tool_use=tools,
                used_check=tools["check"], used_guard=tools["guard"], used_newid=tools["new_id"],
                used_context=tools["context"], bundled=bundled, guard_replay=guard, checks=checks,
                changed_files=sorted(set(git("diff", "--name-only", base).splitlines() +
                                         git("ls-files", "--others", "--exclude-standard").splitlines())),
                backlog=dict(ids_added=[i for i in oa if i not in before], ids_removed=[i for i in ob if i not in after],
                             order_changed=[i for i in oa if i in before] != [i for i in ob if i in after],
                             new_order=oa, row_changes={i: {"before": before[i], "after": after[i]}
                                                      for i in oa if i in before and before[i] != after[i]},
                             added_rows={i: after[i] for i in oa if i not in before}),
                final=final, tool_cmds=commands)


if __name__ == "__main__":
    print(json.dumps(summarize(*sys.argv[1:]), indent=1))
