# Inwoven

[Inwoven](https://backlog.works) connects product strategy and goals to an ordered backlog.
People and AI coding agents read the same Markdown files.

Keep agents from inventing work, changing priority or accepting items unasked.
The skill reads the item's goal first, preserves requested changes and checks edits.
See the [backlog format](skills/inwoven/references/backlog-format.md) and this row:

```text
| K417. Explain the next choice | | | In Progress | |
```

The [Inwoven skill](skills/inwoven/SKILL.md) tells an agent how to pick an item,
read why it matters and check the product files. It includes references for
backlog.md, goals.md, impact.md and wardley.md.

Tested: Linux, macOS and Windows; Python 3.9 and 3.13, plus 3.11 on Linux;
Claude Code, Codex CLI and GitHub CLI installs from the published repo and candidate. [CI checks](.github/workflows/ci.yml)
and [install checks](.github/workflows/install.yml) run on pushes and nightly.
Published 0.2.1 has a known Codex hook-discovery defect; candidate hooks are
checked separately and must pass. Scheduled checks need repository activity
at least once every 60 days.

## Claude Code

Run in Claude Code:

```text
/plugin marketplace add priaby/inwoven
/plugin install inwoven@inwoven
```

Update with `/plugin marketplace update inwoven`.

For a manual install, clone this repo and copy skills/inwoven/ to
~/.claude/skills/inwoven/. Invoke the standalone skill with /inwoven,
or the plugin skill with /inwoven:inwoven.

## Codex

Run in your terminal:

```sh
codex plugin marketplace add priaby/inwoven
codex plugin add inwoven@inwoven
```

Codex first asks you to Trust this folder, then shows Hooks need review.
Open `/hooks`, open PostToolUse and press `t` to trust the Inwoven hook.
Changed hooks need review again. See the [Codex hook trust steps](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

Update with `codex plugin marketplace upgrade`. Start a new session after installing. For a manual install, clone this repo and
copy skills/inwoven/ to .agents/skills/inwoven/ in your project.

## GitHub CLI

Needs GitHub CLI 2.90 or later.

```sh
gh auth login
gh skill install priaby/inwoven inwoven
```

Sign in first to avoid the shared anonymous GitHub API rate limit.
Add `--agent claude-code`, `--agent codex` or `--agent opencode` to choose where it installs.

## OpenCode

Run in your project after `gh auth login`:

```sh
gh skill install priaby/inwoven inwoven --agent opencode
```

OpenCode finds the skill in .agents/skills/inwoven/. Run `opencode debug skill`
to see it listed. Tested with OpenCode 1.19.

## Claude.ai

1. Download inwoven.zip from [releases](https://github.com/priaby/inwoven/releases).
2. Turn on Code execution and file creation in Settings > Capabilities.
   On Team and Enterprise plans an owner turns it on under Organization settings > Plugins & skills.
3. Open [Customize > Skills](https://claude.ai/customize/skills).
4. Select +, then Create skill, then Upload a skill.
5. Choose inwoven.zip and turn the skill on.

## ChatGPT

A workspace admin can import https://github.com/priaby/inwoven through
Admin > Plugins > Add > Import marketplace, then set the installation policy.
Invoke the skill with @inwoven.

## Tools

Needs Python 3.9 or later, with no dependencies. On macOS and Linux, copy
skills/inwoven/ into .agents/skills/inwoven/ in your repo and run from that repo:

```sh
python3 .agents/skills/inwoven/scripts/inwoven.py check --root docs/product
```

Use that script path for these commands:

| Command | When | Output |
|---|---|---|
| check [FILE...] | After edits | Success summary or file:line errors |
| new-id --count N | Before requested additions | Random unused ids |
| context ID | Before starting or answering which goal an item serves | Row, goals, measures and maps; missing links |
| guard --base HEAD | After requested row or acceptance changes, before committing | Changes to confirm and stale updated dates; exit 1 if found, 2 if comparison failed |
| init [KIND...] | When asked to create files; default backlog only | Created or kept paths and next step |

Set --root to your product folder. For another filename, use check --kind backlog
FILE or the corresponding kind. Replace the marked example with your work and a
minted id. Optional context files and frontmatter may be absent.

The Claude Code plugin checks recognized Inwoven files after Edit, Write and
MultiEdit. Codex runs the same check after you trust the hook. It recognizes the current or HEAD text of backlog.md, goals.md,
impact.md or wardley.md; other files are ignored. Errors name what to restore;
valid edits and unrelated files are silent.
The hook uses sh on Linux and macOS, and Git Bash on Windows. Install Git Bash
for the Windows hook. Its launcher tries python3, python, then py -3; Python
3.9 or later is required. With no supported Python, it prints
`Inwoven check skipped: python3 not found` to stderr and exits 0. With no Git,
the hook recognizes only the current file text; guard reports `guard needs git on PATH` and exits 2.
It cannot undo an edit. See the [hook contract](https://code.claude.com/docs/en/hooks)
and [plugin layout](https://code.claude.com/docs/en/plugins-reference).
Standalone skills do not install the hook.

## GitHub Action

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: priaby/inwoven@v0
  with:
    root: docs/product
    guard-base: origin/main
    fail-on-guard: 'false'
```

The runner needs Python 3.9 or later. Check fails on invalid files. Guard is
advisory unless fail-on-guard is true. Fetch the base revision before comparison.
Strict guard also fails on an edited backlog.md with an unchanged stale updated
date. The suggested date is the runner's date; this check covers backlog.md only.

## AGENTS.md alternative

The block uses the bundled tools. Copy skills/inwoven/ into your repo first and
replace <skill dir> with its path and DIR with your product folder.
For Claude Code, import AGENTS.md from CLAUDE.md with @AGENTS.md.
The block alone works in OpenCode; command reporting can vary.

```markdown
## Product files
Use docs/product/ unless the person or repo names another path; context files are beside backlog.md.
Read whole instruction files at the repo root, every folder on the path and the product folder; never truncate them.
- backlog.md: rows in priority order; goals.md: goals and measures; impact.md: actors and changes; wardley.md: dependencies.
## Working an item
- Work the named item, otherwise the highest In Progress item without Waiting on:. Start To Do only when asked.
- Read linked context first; say what optional context is missing and continue. Completion never implies Done.
- Do not mark Done, add Accepted or Reopened, reorder, delete or add items on your own initiative. On the person's explicit request in this conversation, do exactly that and nothing more.
- Accept In Progress on request: `Done<br>Accepted: <YYYY-MM-DD> by Product Owner`, then existing tags in order.
- Reopen Done on request: set the requested open status, remove Accepted, add Reopened first if absent, keep other tags.
- Add every requested item, even near-duplicates; use the person's words and leave unprovided cells empty. Put it where asked or last; top means row 1.
- Before adding, run `python3 <skill dir>/scripts/inwoven.py new-id --root DIR`; never pick ids by hand. Say what was written.
- Re-read before writing; preserve concurrent edits, unrelated bytes and ids. Keep five cells per row and titles within 80 characters.
- In existing files with frontmatter, set updated to today as YYYY-MM-DD on every edit, reorders included. Never add frontmatter.
- After edits run `python3 <skill dir>/scripts/inwoven.py check --root DIR`; report its exit code and output. After requested reorder, addition, deletion, acceptance or reopen, run `python3 <skill dir>/scripts/inwoven.py guard --base HEAD --root DIR`; quote its lines. Exit 1 is expected.
- Commit only when the person or repo asks; put the item id in the subject and keep the host's Co-Authored-By trailer.
```

MIT licence. See [LICENSE](LICENSE).
