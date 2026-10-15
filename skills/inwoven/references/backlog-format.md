# Backlog format

File: docs/product/backlog.md, or the path the person names.
Row order is priority. Add and order items only when the person asks.
"The top" means the first row regardless of Status.

```markdown
---
title: "Example backlog"
updated: 2026-10-13
---
| Item (PBI) | Core Job | Context | Status | Driver |
|---|---|---|---|---|
| K417. Make the next choice clear | Choose work | Show its goal | In Progress | Alex |
| K418. Fix the form | Collect orders | Show the error | In Progress<br>Waiting on: API key | Alex |
```

Cells per row: 5. Keep the header and all existing cells.
The active table is the first run of consecutive rows that begin `| <id>. `,
for example `| K417. `. A header and separator alone can represent an empty table.
The reader also accepts an item-row block without its header or separator;
check follows that tolerant reading and does not prove Markdown renders a table.
Keep the header and separator for rendering; restore them if an edit removed them.
Do not create a second item table. Keep ids unique.

Id alphabet: ABCDEFGHJKLMNPRSTUVWXYZ.
An id is one letter from that alphabet followed by three digits from 100 to 999.
Never change an existing id or reuse one.
Before adding a requested item, run `python3 <skill dir>/scripts/inwoven.py new-id
--root DIR`. Never pick an id by hand. The tool checks the backlog, impact,
Wardley and git history. Put the row where requested, otherwise last.
Core Job is the person's job the item serves; Context explains the request.
Use only the person's words for title, Core Job, Context and Driver; leave
unprovided cells empty. Driver names are comma-separated. Say what was written.

Title limit: 80 characters. Context limit: 280 characters.
Do not put a pipe or a newline inside a cell.

Statuses: empty, To Do, In Progress, Done. Write them in exact case.
The status is the text before the first `<br>`. Empty means To Do.
Legacy Ready in the status position reads as To Do with a Ready tag.
Other legacy words read as To Do with the original word shown as a tag;
keep new edits in the supported vocabulary. Check accepts legacy Ready and other
status words, but prints a non-failing note for unknown words so typos are visible.

Tag kinds: Sprint:, Due:, Accepted:, Waiting on:, Ready, Reopened.
Tags follow `<br>` and empty tags are ignored. Exact flag words: Ready, Reopened.
Valued prefixes: Sprint:, Due:, Accepted:, Waiting on:.
These four colon prefixes carry values and have no tag length limit.
Plain tag limit: 20 characters. Do not put work narrative in tags.
Write prefixes exactly, with capitals and the colon.
Add `Waiting on: <condition>` when blocked; keep other tags.
Do not mark Done, add Accepted or Reopened, reorder, delete or add items on your
own initiative. On the person's explicit request, do exactly that and nothing more.
Ask whether close means accept or cancel. To accept or mark done an In Progress item on request, write
`Done<br>Accepted: <today as YYYY-MM-DD> by Product Owner`, followed by existing
tags in order. Example: `In Progress<br>Sprint: S2` becomes
`Done<br>Accepted: 2026-10-13 by Product Owner<br>Sprint: S2`.
The suffix `by Product Owner` is the product's acceptance convention, treating
the accepting person as that role. Report who requested acceptance; follow repo instructions if they name the acceptor.
To reopen Done on request, remove every `Accepted:` tag and add `Reopened` first
if absent; set the requested open status and preserve the other tags.
Add each requested item that is new. If a title matches or nearly matches an existing
one (a near-duplicate), do not add it; ask, naming the existing id, and still add the
others. Completing work never implies Done.

If the file has frontmatter, set `updated:` to today as YYYY-MM-DD; do not add
frontmatter otherwise. Empty updated is absent; a nonempty value must be a real date.
Preserve unrelated bytes, row order and ids except for the requested change.

## Status examples

Before: `In Progress<br>Sprint: S2`.
Accept on request: `Done<br>Accepted: 2026-10-14 by Product Owner<br>Sprint: S2`.
Reopen on request: `In Progress<br>Reopened<br>Sprint: S2`.
Block: `In Progress<br>Sprint: S2<br>Waiting on: legal sign-off`.
The example date is illustrative; use today's date and report who asked.
