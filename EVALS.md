# Measured model comparisons

Collected 2026-10-14 at source commit 4275c01; regraded from the saved packet 11
runs with a user-level rubric. These measurements predate the pre-edit reminder.
One run per scenario and configuration. This is a small sample, not a reliability estimate.

| Model | Core rubric + valid file + byte preservation: with / without | New rows with no invented text (S4, S9): with / without |
|---|---:|---:|
| Haiku 5.5 (`claude-haiku-5-5`) | 5/5 / 4/5 | 2/2 / 0/2 |
| Sonnet 5.5 (`claude-sonnet-5-5`) | 5/5 / 5/5 | 2/2 / 0/2 |
| Sol (`gpt-6.1-sol`, low reasoning) | 5/5 / 3/5 | 2/2 / 0/2 |

Core scenarios: S1 work the highest eligible item; S3 accept the top item; S4 add
an item second; S7 move the last To Do item to the top; S9 add three items, one
of which already exists. A run passes when the checker accepts the file, the
requested backlog action is made, and the whole backlog file is byte-identical
outside the requested row change and the frontmatter `updated:` line. For S1,
the rubric checks that goal context was read; it does not grade implementation
correctness. S3 needs Done with the run
day's acceptance date. S7 accepts the top of the table or the top of the To Do
rows. S9 may skip the existing title if the agent says so.
The last column counts runs that left Core Job, Context and Driver empty when
the request gave none. Without the skill, every model wrote its own Core Job
and Context into new rows. Haiku and Sol also picked ids I204 and I924, which
the format forbids; those two files failed the check.
With the skill, all models wrote Inwoven's acceptance form in S3 and updated
the file date on backlog edits in S3, S4, S7 and S9. Those are Inwoven conventions,
reported separately by the grader rather than scored as user-outcome failures.
S1 did not change the backlog date and is not counted as a backlog edit.
Sol's no-skill S1 run added prose outside the requested change and fails the
whole-file check. The rubric reads the resulting files; completion alone is not a pass.

After clarifying mark-done acceptance and batch additions, the complete with-arm
was rerun once. The batch-addition rule was added after the first with-skill run.
The table uses that final with-arm and the original no-skill runs, regraded with
the same user-level rubric. All completed turns in those selected arms are included. Failed Claude
runner setups were fixed and rerun; they are not counted as behavioral outcomes.

Discovery: Haiku, one run per query, installed as a plugin outside the fixture:
10/10 should-trigger queries used the Skill tool; 0/10 near-misses used it.
Discovery does not prove edit correctness.
A separate Sol session with conflicting product-folder instructions read
AGENTS.override.md and returned the override marker, 1/1, measured on the previous
wording; the instruction step was unchanged.

## Rerun from this public repository

Signed-in Claude Code and Codex CLIs are required. Runs incur model-account usage.
Paid runs are manual, outside public CI. Run before a release and review the
transcripts and file diffs. Use a new output directory for each comparison.

```sh
python3 tests/eval/run_eval.py --arms "with without" -c "haiku sonnet codex" -s "S1 S3 S4 S7 S9" --repeat 1 --jobs 3 -w /tmp/inwoven-work -o artifacts/core
python3 tests/eval/run_eval.py --triggers -S tests/eval/triggers.tsv -c haiku --repeat 1 --jobs 3 -w /tmp/inwoven-work -o artifacts/triggers
python3 tests/eval/run_eval.py -c codex -s S12 -w /tmp/inwoven-work -o artifacts/override
claude plugin eval . --scaffold --allow-tools Bash Edit Write --model haiku --runs 1 --trust-plugin --no-publish
```

Native cases cover S3, S4, S7, S9 and two near-misses, with the CLI's no-plugin
baseline. The table comes from tests/eval/run_eval.py, not the native suite.
Outputs include summary.json, events.jsonl, diff.patch and runs-table.md.
The private receipt `tests/connectors/eval/results/2026-10-14.json` records every
reported result, saved-run path and artifact hash, including discovery and override.
Summary records infrastructure status, user outcome, invented-text and convention
metrics separately. New runs record run_date; older receipts use the fixture
commit date, so regrading does not depend on the day the grader is invoked.

Fixture copies live outside repositories with CLAUDE.md or AGENTS.md ancestors.
Claude uses a separate config directory with only auth copied, project settings
only, no user MCP or auto-memory. The plugin is outside the fixture.
Codex uses ephemeral sessions with user skills and memory disabled; the recorded
operator home had no AGENTS.md. HOME and user configuration files are unchanged.
Only process groups created by the runner are terminated. Temporary auth copies
are removed after the run. Workspaces remain for inspecting the artifacts.
