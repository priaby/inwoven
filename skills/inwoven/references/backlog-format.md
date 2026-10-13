# Backlog format

File: docs/product/backlog.md, or the path the person names.
Row order is priority. The person adds and orders items.

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
Do not create a second item table. Keep ids unique.

Id alphabet: ABCDEFGHJKLMNPRSTUVWXYZ.
An id is one letter from that alphabet followed by three digits from 100 to 999.
Never invent an id for an existing item, change an id or reuse one.

Title limit: 80 characters. Context limit: 280 characters.
Do not put a pipe or a newline inside a cell.

Statuses: empty, To Do, In Progress, Done. Write them in exact case.
The status is the text before the first `<br>`. Empty means To Do.
Legacy Ready in the status position reads as To Do with a Ready tag.
Other legacy words read as To Do with the original word shown as a chip;
keep new edits in the supported vocabulary.

Note kinds: Sprint:, Due:, Accepted:, Waiting on:, Ready, Reopened.
Notes follow `<br>` and empty notes are ignored. Exact flag words: Ready, Reopened.
Valued prefixes: Sprint:, Due:, Accepted:, Waiting on:.
These four colon prefixes carry values and have no note length limit.
Plain chip limit: 20 characters. Do not put work narrative in chips.
The agent adds `Waiting on: <condition>` when blocked, preserves other tags,
and never adds Accepted or Reopened or marks Done.

If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none. Validate the edited table and
preserve all unrelated bytes, row order and the id set.
