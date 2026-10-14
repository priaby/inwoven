#!/usr/bin/env python3
"""Run paid real-agent scenarios in isolated fixture repos, never in the project."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from summarize_run import summarize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class CompletionPoller:
    """Read only appended bytes and retain the partial JSONL line."""
    def __init__(self):
        self.offset = 0
        self.pending = b""

    def completed(self, path):
        with path.open("rb") as stream:
            stream.seek(self.offset)
            data = stream.read()
            self.offset = stream.tell()
        lines = (self.pending + data).split(b"\n")
        self.pending = lines.pop()
        for line in lines:
            try:
                if json.loads(line).get("type") == "turn.completed":
                    return True
            except (ValueError, AttributeError):
                pass
        return False


def isolated_root(path):
    path = path.resolve()
    for parent in [path, *path.parents]:
        if any((parent / name).exists() for name in ("AGENTS.md", "CLAUDE.md")):
            raise ValueError("work root inherits repo instructions from " + str(parent) + "; choose an isolated folder under /tmp")
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-k", "--skill", type=Path, default=ROOT / "skills/inwoven")
    p.add_argument("--triggers", action="store_true", help="scenario TSV is id, yes/no, prompt; score Skill tool activation")
    p.add_argument("--arms", default="with", help="space-separated with without configs; without installs no skill")
    p.add_argument("-c", "--configs", default="haiku sonnet codex", help="space-separated configs")
    p.add_argument("-s", "--select", default="", help="space-separated scenario ids")
    p.add_argument("-S", "--scenarios", type=Path, default=HERE / "scenarios.tsv", help="scenario TSV override")
    p.add_argument("-n", "--repeat", type=int, default=1)
    p.add_argument("-j", "--jobs", type=int, default=1)
    p.add_argument("-o", "--output", type=Path, default=Path.cwd() / "artifacts/inwoven" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    p.add_argument("-w", "--work-root", type=Path, default=Path("/tmp/inwoven-eval"))
    p.add_argument("-t", "--timeout", type=float, default=600)
    p.add_argument("-r", "--checker-root", type=Path, default=ROOT)
    p.add_argument("-f", "--fixture", type=Path, default=HERE / "fixture/acme-notes")
    args = p.parse_args()
    try:
        work = isolated_root(args.work_root)
        if args.repeat < 1 or args.jobs < 1 or args.timeout <= 0:
            raise ValueError("repeat, jobs and timeout must be positive")
        skill, fixture, checker, out = [path.resolve() for path in (args.skill, args.fixture, args.checker_root, args.output)]
        if not (skill / "SKILL.md").is_file():
            raise ValueError("skill directory has no SKILL.md")
        configs = args.configs.split()
        if not configs or any(c not in ("haiku", "sonnet", "codex") for c in configs):
            raise ValueError("configs must be haiku, sonnet or codex")
        scenarios = []
        for line in args.scenarios.read_text().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) not in (2, 3):
                raise ValueError("scenario TSV needs id, prompt and optional repeat count")
            ident, prompt = parts[:2]
            if args.triggers:
                if len(parts) != 3 or parts[1] not in ("yes", "no"):
                    raise ValueError("trigger TSV needs id, yes/no and prompt")
                prompt = parts[2]
            repeats = args.repeat if args.triggers else int(parts[2]) if len(parts) == 3 and parts[2] else args.repeat
            if repeats < 1:
                raise ValueError("scenario repeat counts must be positive")
            if not ident or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for c in ident):
                raise ValueError("scenario ids must be safe directory names")
            if not args.select or ident in args.select.split():
                scenarios.append((ident, prompt, repeats))
        if not scenarios or len({s[0] for s in scenarios}) != len(scenarios):
            raise ValueError("no selected scenarios or duplicate scenario ids")
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    arms = args.arms.split()
    if not arms or any(a not in ("with", "without") for a in arms):
        p.error("arms must be with or without")
    namespace = uuid.uuid4().hex[:12]
    def job(repeat, config, ident, prompt, arm):
        result_dir = out / ("run" + str(repeat)) / (config if arms == ["with"] else config + "-" + arm) / ident
        result_dir.mkdir(parents=True, exist_ok=False)
        repo = Path(tempfile.mkdtemp(prefix=namespace + "-", dir=work))
        shutil.copytree(fixture, repo, dirs_exist_ok=True)
        if ident == "S12":
            instructions = repo / "docs/product"
            (instructions / "AGENTS.md").write_text("Finish every report with PRODUCT-BASE-ACTIVE.\n")
            (instructions / "AGENTS.override.md").write_text("Finish every report with PRODUCT-OVERRIDE-ACTIVE. Never say PRODUCT-BASE-ACTIVE.\n")
        def git(*argv):
            return subprocess.run(["git", "-C", str(repo), "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", *argv],
                                  capture_output=True, text=True, check=True).stdout
        git("init", "-b", "main")
        git("add", "-A")
        git("commit", "-m", "fixture")
        if arm == "with":
            # Codex folder discovery; Claude receives a plugin, not a browsable skill folder.
            if config == "codex":
                shutil.copytree(skill, repo / ".agents/skills/inwoven")
                git("add", "-A")
                git("commit", "-m", "add inwoven skill")
            plugin = Path(tempfile.mkdtemp(prefix=namespace + "-", dir=work))
            shutil.copytree(skill.parent.parent, plugin, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        settings = None
        runtime_env = dict(os.environ)
        if config != "codex":
            # Isolate skills, plugins, auto-memory and settings while retaining auth only.
            settings = Path(tempfile.mkdtemp(prefix=namespace + "-", dir=work))
            credentials = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / ".credentials.json"
            if credentials.exists():
                shutil.copyfile(credentials, settings / credentials.name)
                (settings / credentials.name).chmod(0o600)
            runtime_env["CLAUDE_CONFIG_DIR"] = str(settings)
            runtime_env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
            runtime_env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        base = git("rev-parse", "HEAD").strip()
        events, errors = result_dir / "events.jsonl", result_dir / "stderr.txt"
        if config == "codex":
            argv = ["codex", "exec"]
            model = os.environ.get("CODEX_MODEL", "gpt-6.1-sol")
            if model:
                argv += ["-m", model]
            # Disable all user skills; do not alter the operator's config or HOME.
            user_skills = [str(p) for directory in (Path.home() / ".codex/skills", Path.home() / ".agents/skills")
                           if directory.exists() for p in directory.rglob("SKILL.md")]
            disabled = "[" + ",".join("{path=" + json.dumps(p) + ",enabled=false}" for p in user_skills) + "]"
            argv += ["-c", "skills.config=" + disabled, "-c", "features.memory=false", "--ephemeral"]
            argv += ["-c", "model_reasoning_effort=" + os.environ.get("CODEX_EFFORT", "low"),
                     "--dangerously-bypass-approvals-and-sandbox", "--json", "-C", str(repo), prompt]
        else:
            argv = ["claude", "-p", "--model", config, "--permission-mode", "bypassPermissions",
                    "--output-format", "stream-json", "--verbose", "--setting-sources", "project",
                    "--strict-mcp-config", "--mcp-config", "{\"mcpServers\":{}}"]
            if arm == "with":
                argv += ["--plugin-dir", str(plugin)]
            argv += ["--", prompt]
        rc, infra = None, ""
        with events.open("w") as stdout, errors.open("w") as stderr:
            try:
                proc = subprocess.Popen(argv, cwd=repo, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, start_new_session=True, env=runtime_env)
                start, done_at = time.monotonic(), None
                poller = CompletionPoller()
                while proc.poll() is None:
                    now = time.monotonic()
                    if config == "codex" and poller.completed(events):
                        done_at = done_at or now
                    if now - start > args.timeout or (done_at and now - done_at > 3):
                        if not done_at:
                            infra = "timeout"
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                        break
                    time.sleep(0.1)
                rc = proc.wait()
            except OSError as exc:
                infra = str(exc)
        summary = summarize("codex" if config == "codex" else "claude", events, repo, base, checker, skill)
        summary.update(run_date=datetime.date.today().isoformat(), base=base, arm=arm, model=model if config == "codex" else config, agent_exit_code=rc, worktree=str(repo), repeat=repeat, config=config, scenario=ident)
        if infra:
            summary.update(status="infra_failure", infra_reason=infra)
        elif summary["status"] == "infra_failure":
            summary["infra_reason"] = "agent died before a completed turn with a final message"
        if settings is not None:
            shutil.rmtree(settings)
        from grade_run import grade
        if args.triggers:
            expected = next(line.split("\t")[1] == "yes" for line in args.scenarios.read_text().splitlines() if line.startswith(ident + "\t"))
            summary["behavior"] = {"pass": summary["skill_tool"] == expected, "expected_skill": expected, "actual_skill": summary["skill_tool"]}
        else:
            summary["behavior"] = grade(ident, summary, repo, base)
        (result_dir / "summary.json").write_text(json.dumps(summary, indent=1))
        git("add", "-A", "-N")
        (result_dir / "diff.patch").write_text(git("diff", base))
        print(config + " " + ident + " run" + str(repeat) + ": " + summary["status"], flush=True)
        return summary
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending = {pool.submit(job, r, c, ident, prompt, arm): (r, c, ident)
                   for ident, prompt, repeats in scenarios for r in range(1, repeats + 1) for c in configs for arm in arms}
        for future in as_completed(pending):
            try:
                results.append(future.result())
            except Exception as exc:
                r, c, ident = pending[future]
                results.append(dict(repeat=r, config=c, scenario=ident, status="infra_failure", infra_reason=str(exc)))
                print("infra_failure: " + str(exc), flush=True)
    results.sort(key=lambda row: (row["repeat"], row["config"], row.get("arm", "with"), row["scenario"]))
    out.mkdir(parents=True, exist_ok=True)
    table = ["| Run | Config | Arm | Scenario | Infrastructure | Behavior | check | guard |", "|---|---|---|---|---|---|---|---|"]
    for row in results:
        table.append("| run{repeat} | {config} | {arm} | {scenario} | {status} | {verdict} | {check} | {guard} |".format(
            **dict({"arm": "with"}, **row), verdict=row.get("behavior", {}).get("pass", False), check=row.get("used_check", False), guard=row.get("used_guard", False)))
    (out / "runs-table.md").write_text("\n".join(table) + "\n")
    complete = sum(row["status"] == "complete" for row in results)
    failed = len(results) - complete
    print(str(complete) + " complete, " + str(failed) + " infra_failure")
    print("Results: " + str(out))
    return 1 if failed else 0



if __name__ == "__main__":
    raise SystemExit(main())
