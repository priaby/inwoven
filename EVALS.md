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
rows. On 2026-10-14 S9 accepted either adding the existing title or skipping it with a note;
those S9 results are from the earlier rule and are superseded by the rerun below.
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

## S9 rerun under the ask-before-duplicate rule

S9 was rerun on 2026-10-15 after the skill changed: when a requested title already
exists, the agent asks before adding that one, naming the existing id, and still
adds the others. The S9 numbers in the table above predate this rule. S1, S3, S4
and S7 were not rerun. Two runs per model and arm, 12 runs, all completed turns.
A run passes only if it added exactly CSV import and SSO, left everything else
byte-identical except the `updated:` line, kept the formats valid, and its final
message names Dark mode and D883 and asks a question (a question mark).
This is a small sample, not a reliability estimate.

| Model | S9 pass: with / without | New rows with no invented text: with / without |
|---|---:|---:|
| Haiku 5.5 (`claude-haiku-5-5`) | 1/2 / 0/2 | 2/2 / 0/2 |
| Sonnet 5.5 (`claude-sonnet-5-5`) | 2/2 / 0/2 | 2/2 / 0/2 |
| Sol (`gpt-6.1-sol`, low reasoning) | 0/2 / 0/2 | 2/2 / 0/2 |

Why runs failed. With the skill, every run left Dark mode out and added both new
rows with empty Core Job, Context and Driver. Haiku run 1 and both Sol runs did
not ask: they said the item exists (Sol: "clarification is pending") without a
question, so they fail the ask check. Without the skill, no run asked; all six
skipped Dark mode and stated it exists, wrote their own Core Job, Context and
Status, and some picked ids by hand; Sol's two files and Sonnet's second also
failed the format check. The no-skill arm was not told the rule, so it shows what
the model does unaided, not a failure to follow the skill.
The per-run record, with the final messages and artifact hashes, is
`tests/connectors/eval/results/2026-10-15.json` (private repository).

### S9 follow-up: the question is the last line

In the rerun above, Haiku run 1 and both Sol runs reported that Dark mode exists
but did not end by asking; the held-back item was a statement in the middle of a
report that closed with check and guard output. The skill now requires the last
line of the reply to be the question, after the check and guard output, with an
example naming the existing id. The grader now requires the last line of the final
message to contain a question mark and the id D883. That is stricter than the
rubric above, which accepted a question mark anywhere. Only the with-skill arm was
rerun on 2026-10-15 against the reworded skill (v0.4.2): Haiku 3 runs, Sol 3 runs,
Sonnet 2 runs, all completed turns, one wording, no iteration. The earlier runs
and the without-skill arm are unchanged. Small sample, not a reliability estimate.

| Model | S9 pass, last line asks: with | New rows with no invented text: with |
|---|---:|---:|
| Haiku 5.5 (`claude-haiku-5-5`) | 3/3 | 3/3 |
| Sonnet 5.5 (`claude-sonnet-5-5`) | 2/2 | 2/2 |
| Sol (`gpt-6.1-sol`, low reasoning) | 3/3 | 3/3 |

An earlier identical batch of 8 passed 8 before a redundant bullet was cut from the
skill to keep it within its line cap, then 104 lines. The cap is now 120 lines (SKILL.md
in 0.6.1 is 120 lines, 8820 bytes), pinned by `tests/connectors/test_inwoven_skill.py`.
The numbers above are from the 0.4.2 text and were not rerun for 0.6.0 or 0.6.1.
Every run left Dark mode out, added only CSV import and SSO, and ended with the
line "D883 Dark mode already exists. Add another Dark mode item anyway?", which
copies the example in the skill. The record is the `round` r16 entries in the same
results file.

Discovery: Haiku, one run per query, installed as a plugin outside the fixture:
10/10 should-trigger queries used the Skill tool; 0/10 near-misses used it.
Discovery does not prove edit correctness. Those 10 and 10 are the 0.4.2 text; the 0.6.1 numbers
are in the section "Coverage pass, skill 0.6.1" below.
A separate Sol session with conflicting product-folder instructions read
AGENTS.override.md and returned the override marker, 1/1, measured on the previous
wording; the instruction step was unchanged.

## Learnings (W669), skill 0.6.0

Run on 2026-10-21 against the final skill 0.6.0 text (SKILL.md is 120 lines, 8814 bytes):
the review fix (commit 5696ea6c) plus one tightening pass on step 13. The L1 to L3 runs
and the 0.5.0 arm ran on the text after the review fix and before the tightening; the
tightening only touches step 13, which L1 to L3 and 0.5.0 do not reach, and the new-skill
propose cases (P1, P2, P3, W1) were rerun on the final text. The comparison skill is 0.5.0 from `origin/main` at ef083bff.
Models: Haiku 5.5 (`claude-haiku-5-5`) and Sonnet 5.5 (`claude-sonnet-5-5`); Sol was not
available. Three runs per model, arm and case, all completed turns, no iteration on the
skill between runs. A small sample, not a reliability estimate: three runs cannot tell
2/3 from 3/3. Arms B and C do not depend on the text that changed (B has no file, C runs
the old skill), so their numbers are the runs made before the review fix.

Fixture: `acme-notes` plus the top item T318 "Show the last edit date in the note export"
(In Progress), `src/export.py` writing title and body, and `src/app.py` storing a
`datetime` in `edited`. `learnings.md` is written at run time with dates relative to the
run day. The lesson is "Export dates are DD.MM.YYYY; the partner importer rejects ISO".
Graders are deterministic: they read `src/export.py`, `learnings.md`, the backlog row and
the reply, and run `check`. A work case passes only if `check` accepts the folder and
`learnings.md` is byte-identical afterwards.

### A lesson prevents a mistake

Prompt "Start the top item." Pass for L1 and L3: `src/export.py` has `%d.%m.%Y` and no ISO
form. Pass for L2: it does not have `%d.%m.%Y`, and the date was still added.

| Case | Lesson state | Arm | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|---:|---:|
| L1 | dated 10 days ago, no check | A: 0.6.0 with the file | 3/3 | 3/3 |
| L1 | no file | B: 0.6.0 without the file | 0/3 | 0/3 |
| L1 | dated 10 days ago, no check | C: 0.5.0 with the file | 3/3 | 3/3 |
| L2 | dated 200 days ago, no check | A | 3/3 | 3/3 |
| L3 | dated 200 days ago, Enforced by an existing test | A | 3/3 | 3/3 |

The hypothesis that C fails L1 was wrong. 0.5.0 knows nothing about `learnings.md`, but
all six C runs read `docs/product/learnings.md` themselves, and Sonnet's reply says
"because `docs/product/learnings.md` says the partner importer rejects ISO dates". The
fixture's AGENTS.md says product docs live in `docs/product/`, and an agent that lists
that folder finds the file. C passes because the fixture AGENTS.md points at
`docs/product/`. So L1 shows that a lesson file helps (B against A and C); it does not show
that the skill's read-back is needed. In arm A the skill ran
`context` in all six L1 runs and all six L2 runs, and in 4 of 6 L3 runs (Haiku 1 of 3).
In L2, three runs saw the expired row through a grep or a cat and still did not apply it;
the other three never saw it, since `context` does not print expired rows. In L3 four of six
runs ran the existing test, which passes until an ISO date is written and then fails, so the
test may carry some of the pass besides the lesson. Neither a ten-day-old nor a 200-day-old
lesson without a check separated the skill from a plain file read here.

### The propose step writes nothing before yes

Prompt P1, P2, W1: "Mark the top item done. It took two tries: ISO dates broke the partner
importer, it needs DD.MM.YYYY." P3: "Mark the top item done. It only renamed a button
label." W1 sends "yes" as a second turn that resumes the same session.

| Case | Fixture | Pass | Arm | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|---|---:|---:|
| P1 | no file | one row with the item id and today's date, last line asks, no file, item Done | 0.6.0 | 2/3 | 3/3 |
| P1 | no file | same | 0.5.0 | 0/3 | 0/3 |
| P2 | live lesson, same text | proposes renewing with a new Date, no new row, file byte-identical | 0.6.0 | 1/3 | 3/3 |
| P2 | live lesson, same text | same | 0.5.0 | 0/3 | 0/3 |
| P3 | no file | no row, no lesson question, no file | 0.6.0 | 3/3 | 3/3 |
| P3 | no file | same | 0.5.0 | 3/3 | 3/3 |
| W1 | P1 state, then "yes" | one new row equal to the proposed row, `check` passes, `updated` is today | 0.6.0 | 3/3 | 2/3 |
| W1 | P1 state, then "yes" | same | 0.5.0 | 0/3 | 0/3 |

No run of either skill wrote `learnings.md` before a yes: P1 and P3 end with no file, P2
with the file byte-identical, and no W1 first turn contains a write to it. The 0.6.0
failures on the final text:

- P1, Haiku, 1 run: no proposal at all; the reply ends "I did not commit. Nothing else in
  the backlog changed."
- P2, Haiku, 2 runs: no renewal offer. One reply ends on an unrelated note about the
  `Accepted:` tag; the other says "a new row would repeat it. If you want that lesson linked
  to T318 or given an enforced check, tell me and I'll make the change", a statement and
  not the "Renew this lesson?" question.
- W1, Sonnet, 1 run: no proposal in the first reply ("I'm not proposing one, so there is
  nothing to approve"). After "yes" it said there was nothing to answer, showed the row and
  wrote nothing.

0.5.0 fails P1, P2 and W1 as expected: it never proposes. In one earlier P1 run Haiku said
"The DD.MM.YYYY detail isn't recorded anywhere yet" and did not offer a lesson.

The step 13 tightening pass. After the review fix, the failures were: a yes asked with no
row shown and a row written that the person never saw (W1 Sonnet), the question not the last
line (P1 Haiku), no renewal offered for a live lesson (P2 Haiku), and written text that
differed from the proposal (W1 Haiku). Step 13 then said plainly: never ask without the
full table row in the same reply, the question is the last line, after yes write exactly
the row shown, compare with every row first. One pass, no second iteration. Before and
after, same cases, three runs each, Haiku and Sonnet:

| Case | Before the pass | After the pass |
|---|---:|---:|
| P1 | 2/3, 3/3 | 2/3, 3/3 |
| P2 | 0/3, 3/3 | 1/3, 3/3 |
| P3 | 3/3, 3/3 | 3/3, 3/3 |
| W1 | 2/3, 2/3 | 3/3, 2/3 |

The pass fixed W1 Haiku's mismatch (three written rows equal their proposals) and no run
wrote a row the person had not seen. Haiku still skips the proposal or the renewal in 3 of
12 runs and Sonnet in 1 of 12; three runs per cell cannot tell the two texts apart.

Before the review fix (commit a948f52c, SKILL.md 120 lines, 8542 bytes) the same cases on
Haiku and Sonnet scored P1 3/3 and 2/3, P2 1/3 and 2/3, P3 3/3 and 3/3, W1 2/3 and 2/3, and
0.5.0 scored P1, P2 and W1 0/3 and P3 3/3 on both models. Those runs and the review-fix
runs are not the 0.6.0 result; they show how much three runs move between texts. Arm A
scored L1 to L3 3/3 on both models on both earlier texts.

Grader decisions made after seeing the first runs, applied to all runs by regrading the
saved worktrees (`tests/eval/regrade_learnings.py`), not by changing a run:

- A proposal counts as a row when the reply shows it as a table row or as the four
  labelled lines Lesson, Enforced by, Item and Date. "none (no check exists)" in Enforced by
  reads as the empty cell. An inline sentence does not count.
- P3 does not require the item to be Done: the prompt describes work the top item does
  not hold, and some agents asked before closing it (5 of the 12 P3 runs before the fix,
  1 of the 12 after). Their lesson behaviour is what P3 measures.

The pre-fix and first-grade summaries are kept beside the final ones. Transcripts, summaries
and diffs are under the gitignored `artifacts/checks/w669/evals/` in the private
repository (`final2/` for the propose numbers, `final/` for L1 to L3 and 0.5.0, the earlier folders for the pre-fix runs).

## Coverage pass (W669), skill 0.6.1

Run on 2026-10-21 against skill 0.6.1 (SKILL.md 120 lines, 8820 bytes; the description gained "save a
lesson" and lost "priority"; step 4 names learnings as optional). Haiku 5.5 and Sonnet 5.5, three runs per
cell, all completed turns, no iteration on the skill. A small sample, not a reliability estimate.

### Discovery

Haiku, installed as a plugin outside the fixture, 23 queries: the 20 of 0.4.2 plus T21 (propose a lesson
after finishing), T22 (renew a lesson) and the near-miss T23 (a code comment about date formats). First
batch one run per query, then two more runs of the same set (69 sessions, none failed to complete).

| Set | Queries | Runs each | Used the Skill tool |
|---|---:|---:|---:|
| Should trigger | 12 | 3 | 29/36 |
| Near-miss | 11 | 3 | 0/33 |

The first run alone scored 10/12 and 0/11. The misses over three runs: T04 "Which goal does item K417
serve?" 1/3 (it was 1/1 on 0.4.2 and the phrase "which goal" is unchanged), T05 "Move the Offline editing
item above the Share a note by link item" 2/3, T07 "Check our product files are valid" 2/3, and T21
"The importer fix took two tries. Propose a lesson so the next agent does not repeat it." 0/3. The new
description does not make a person's plain request to propose a lesson load the skill. In the lesson
cases the skill loads from the item prompts (P1 to W1 above), not from this phrase. I did not tune the
description: the 0.4.2 numbers came from one run per query and these from three, so a drop on T04 to T07 is
not shown to be the wording. The record is under `artifacts/checks/w669/evals/coverage/discovery*` in the private repository.

### Read-back with no folder hint (L1N, L2N, L3N)

Why: in L1 to L3 the fixture AGENTS.md said "Product docs live in docs/product/." and the prompt was "Start
the top item.", so the 0.5.0 agent listed the folder and read `learnings.md` itself. These cases remove
every hint. The product files sit in `team/`; AGENTS.md has one line about the product, "Backlog:
team/backlog.md."; the prompt names the item, "Start T318."; nothing but `team/learnings.md` contains
DD.MM.YYYY. L1N is L1 (lesson 10 days old, no check), L2N is L2 (200 days old, expired), L3N is L3 (200 days
old, Enforced by an existing check). Passes are as in L1 to L3: L1N and L3N need `%d.%m.%Y` and no ISO date
in `src/export.py`; L2N needs the expired lesson not applied, so it passes just as well when the agent
never sees the lesson. Arm A is 0.6.1, arm C is 0.5.0 from `origin/main` at ef083bff.

Provenance grade, added to the summary: `tool_results` records every tool result, and the grader checks
where the lesson text first appears. `opened_directly` is true when any call other than `context` names
`learnings.md` or returns the lesson text (Read, cat, grep, a listing of the folder followed by a read, or
one shell line that runs `context` and also cats the file, which counts as direct because the two outputs
cannot be told apart). A run is read-back only when the lesson first appears in a `context` result and the
file was never opened directly.

| Case | Arm | Model | Pass | Skill loaded | `context` run | Opened directly | Read-back only | Touched the check |
|---|---|---|---:|---:|---:|---:|---:|---:|
| L1N | A: 0.6.1 | Haiku 5.5 | 2/3 | 2 | 2 | 2 | 0 | |
| L1N | A: 0.6.1 | Sonnet 5.5 | 0/3 | 0 | 0 | 0 | 0 | |
| L1N | C: 0.5.0 | Haiku 5.5 | 2/3 | 2 | 2 | 2 | 0 | |
| L1N | C: 0.5.0 | Sonnet 5.5 | 0/3 | 0 | 0 | 0 | 0 | |
| L2N | A | Haiku 5.5 | 2/3 | 1 | 1 | 2 | 0 | |
| L2N | A | Sonnet 5.5 | 3/3 | 0 | 0 | 0 | 0 | |
| L2N | C | Haiku 5.5 | 2/3 | 0 | 0 | 1 | 0 | |
| L2N | C | Sonnet 5.5 | 3/3 | 0 | 0 | 0 | 0 | |
| L3N | A | Haiku 5.5 | 3/3 | 0 | 0 | 3 | 0 | 3 |
| L3N | A | Sonnet 5.5 | 0/3 | 0 | 0 | 0 | 0 | 0 |
| L3N | C | Haiku 5.5 | 2/3 | 1 | 1 | 2 | 0 | 3 |
| L3N | C | Sonnet 5.5 | 1/3 | 1 | 1 | 1 | 0 | 1 |

Read this as follows.

- The hint is gone and the case is valid. All 5 L1N and L3N passes in arm C came with a direct read of
  `learnings.md` (Haiku listed `team/` or grepped it, Sonnet cat'ed it once); no C run passed without one.
  The expected result "C fails or passes only by a direct read" holds.
- Arm A did not beat arm C. Haiku scored the same on L1N (2/3 and 2/3); on L3N it scored 3/3 against 2/3.
  All 5 A passes on L1N and L3N also came with a direct read, and Haiku read the check in all six L3N runs.
  Sonnet scored 0/3 on L1N and L3N in arm A: it never loaded the skill on "Start T318." (0 of 9 A runs; 1 of 3
  in the superseded L3N attempt below) and never looked in `team/` beyond the backlog, so it wrote ISO dates.
- Of the 18 A runs, 3 loaded the skill (Haiku only) and 3 ran `context`; none was read-back only. The three
  that ran `context` also cat'ed `learnings.md` in the same shell line or the next call. So these runs show
  no case where the skill's read-back alone carried the lesson, and no case where it failed to.
- L2N passes mostly through not seeing the lesson. Haiku A run 3 grepped `team/`, saw the expired row and
  applied it, a failure of step 4's rule, which that run never loaded.
- The prompt "Start T318." loads the skill for 3 of 9 Haiku A runs and 0 of 9 Sonnet A runs, against all
  six L1 runs on "Start the top item." That is a skill discovery gap on a bare item id, not a read-back
  gap. It is not tuned here.

First L3N attempt, kept as context and replaced: the check was `ci/partner_dates.py`. Haiku ran it as a CI
guard in all 6 runs (A and C), so it was not a check the agent had no reason to run; the pass counts of
that attempt were A 1/3 (Haiku) and 1/3 (Sonnet) and C 2/3 and 0/3, and it is not in the table. The final
check is `.github/workflows/partner-dates.yml`, a workflow whose single step is the same assertion. Haiku
still read it in all six runs and ran its assertion by hand in all six; Sonnet read it in one run (C).
Haiku explores every folder it can see, so a check it has no reason to run is not reachable with this
fixture, and I did not hide it further. The L3N confound of L3, an existing test run for its
own sake, is gone, since no `tests/` folder exists, but not the exploration.

Records and diffs are under `artifacts/checks/w669/evals/coverage/` (`A`, `C`, `A-L3N-workflow`,
`C-L3N-workflow`, `discovery`, `discovery-rep`) in the private repository.

## Rerun from this public repository

Signed-in Claude Code and Codex CLIs are required. Runs incur model-account usage.
Paid runs are manual, outside public CI. Run before a release and review the
transcripts and file diffs. Use a new output directory for each comparison.

```sh
python3 tests/eval/run_eval.py --arms "with without" -c "haiku sonnet codex" -s "S1 S3 S4 S7 S9" --repeat 1 --jobs 3 -w /tmp/inwoven-work -o artifacts/core
python3 tests/eval/run_eval.py --triggers -S tests/eval/triggers.tsv -c haiku --repeat 1 --jobs 3 -w /tmp/inwoven-work -o artifacts/triggers
python3 tests/eval/run_eval.py -c codex -s S12 -w /tmp/inwoven-work -o artifacts/override
python3 tests/eval/run_eval.py -c "haiku sonnet" -s "L1 L2 L3" --repeat 3 --jobs 4 -w /tmp/inwoven-work -o artifacts/lessons
python3 tests/eval/run_eval.py -c "haiku sonnet" -s "P1 P2 P3 W1" --repeat 3 --jobs 4 -w /tmp/inwoven-work -o artifacts/propose
python3 tests/eval/run_eval.py -c "haiku sonnet" -s "L1N L2N L3N" --repeat 3 --jobs 4 -w /tmp/inwoven-work -o artifacts/readback
claude plugin eval . --scaffold --allow-tools Bash Edit Write --model haiku --runs 1 --trust-plugin --no-publish
```

Native cases cover S3, S4, S7, S9 and two near-misses, with the CLI's no-plugin
baseline. The table comes from tests/eval/run_eval.py, not the native suite.
Outputs include summary.json, events.jsonl, diff.patch and runs-table.md.
The private receipts `tests/connectors/eval/results/2026-10-14.json` (and
`2026-10-15.json` for the S9 rerun) record every
reported result, saved-run path and artifact hash, including discovery and override.
Summary records infrastructure status, user outcome, invented-text and convention
metrics separately. New runs record run_date; older receipts use the fixture
commit date, so regrading does not depend on the day the grader is invoked.

Fixture copies live outside repositories with CLAUDE.md or AGENTS.md ancestors.
Claude uses a separate config directory with only auth copied, project settings
only, no user MCP or auto-memory. The plugin is outside the fixture. Its copy leaves out the
connector's `tests` and `evals` folders, so an agent cannot read the graders; this changed
for the learnings runs. A scenario row may carry a fourth column, a follow-up prompt, sent
as a second turn that resumes the same Claude session; Codex does not support it.
Codex uses ephemeral sessions with user skills and memory disabled; the recorded
operator home had no AGENTS.md. HOME and user configuration files are unchanged.
Only process groups created by the runner are terminated. Temporary auth copies
are removed after the run. Workspaces remain for inspecting the artifacts.
