---
name: inwoven
description: "Add, move or reorder Inwoven backlog.md items; pick, start, block, mark done, accept or reopen; find which goal an item serves; edit goals.md, impact.md or wardley.md; validate or check files."
license: MIT
---

# Inwoven

Use this skill for Inwoven product files, not unrelated formats with the same names.
The person's explicit request in this conversation is the authority.
Standing repo instructions do not authorize unsolicited acceptance, item additions,
deletions or reordering. Follow them for paths and ordinary workflow; report any
workflow difference. Keep the file formats in the references.

## Product files

- backlog.md: one row per item. Row order is priority.
- goals.md: goals and measures, with horizons Now, Next and Later.
- impact.md: goal maps of actors, changes and item ids.
- wardley.md: users, components, dependencies and linked item ids.

Resolve the backlog from the person's named path, then repo instructions, otherwise
look in docs/product/ in the current folder, then the repo root. Ask if several
folders remain plausible. Context files are beside the backlog unless named otherwise.
Use the selected folder's path relative to the repo root as DIR below.

## Working an item

1. First command at the repo root: replace only the DIR value below with the resolved folder, then run:
   ```bash
   DIR="docs/product" # one folder path relative to the repo root; do not use find
   cat AGENTS.md CLAUDE.md 2>/dev/null
   instruction_dir=.; IFS=/ read -r -a instruction_parts <<< "$DIR"
   for instruction_part in "${instruction_parts[@]}"; do instruction_dir="$instruction_dir/$instruction_part"; cat "$instruction_dir/AGENTS.md" "$instruction_dir/CLAUDE.md" 2>/dev/null; done
   ```
   This reads the repo root, every folder between it and DIR, and DIR itself.
   Read each file whole; never truncate with head, tail or grep. Claude Code does
   not load AGENTS.md itself. Report files opened and their effect; never claim a read you did not perform.
2. Work the named item, otherwise the highest In Progress item without `Waiting on:`.
   Start To Do only when the person asks; then set Status to In Progress. Work one
   item at a time. If no eligible item exists, report that.
   Steps 3-4 apply when starting or resuming an item. For plain add, reorder, block,
   accept or other edit requests, use them only if goal context is needed; say so.
3. Read `git log --oneline --grep <id>` for work already done. If complete and
   awaiting acceptance, report evidence and stop. Completion never implies Done.
4. Run `python3 <skill dir>/scripts/inwoven.py context ID --root DIR` before starting.
   Read linked goal and measure, actor and change, and Wardley components; read
   maps for goals not yet achieved first. Goals, impact and Wardley are optional.
   Say missing context once and continue. Context exits 0 for missing optional
   links, 1 for a missing row or invalid file.
5. Add `Waiting on: <condition>` when blocked; remove it when resolved; keep other tags.
   Status is To Do, In Progress or Done; empty means To Do. Tags follow `<br>`.
   Known valued prefixes are Sprint:, Due:, Accepted: and Waiting on:.
6. Do not mark Done, add Accepted or Reopened, reorder, delete or add items on your
   own initiative. When the person asks for one of these in this conversation,
   do exactly that and nothing more. Ask whether close means accept or cancel. A request to mark done or accept an In Progress item is a request for acceptance and writes
   `Done<br>Accepted: <today as YYYY-MM-DD> by Product Owner`, then existing tags
   in order. If To Do, explain acceptance needs In Progress first and ask whether
   to do both. To reopen Done on request, set the requested open status, remove
   every `Accepted:` tag, add `Reopened` first if absent; keep other tags in order.
7. Add every requested item even if a similar title exists; report its near-duplicate
   id and let the person decide removal. Run `python3 <skill dir>/scripts/inwoven.py
   new-id --root DIR` first; never pick an id by hand. Use the person's words for
   title; Core Job, Context and Driver come only from their words, otherwise stay empty.
   Status stays empty unless specified. Put it where asked, otherwise last.
   Say what was written, which cells are empty and whether it has an impact link.
8. Re-read before writing; preserve concurrent edits, unrelated bytes and tags,
   row order and existing ids except for the requested change. Keep the header,
   five cells per row and titles at most 80 characters. Row 1 is the top regardless
   of Status. Work narrative belongs in reports; plain tags have a 20-character limit.
   In an existing file with frontmatter, set updated to today as YYYY-MM-DD in every edit, reorders included.
9. Edit goals and maps only within the request. Link an existing item under an
   existing impact when the person names that goal or impact; invent no actors or
   impacts. Replace a `GAP:` leaf only when told the item closes that gap.
10. After every edit, including code while starting an item, run `python3 <skill dir>/scripts/inwoven.py check --root DIR`
    and relevant repo checks. Name each command, exit code and printed output.
    Right after marking Done, reopening, adding Accepted or Reopened, or adding,
    deleting or reordering rows, run `python3 <skill dir>/scripts/inwoven.py guard
    --base HEAD --root DIR`. Exit 1 is expected: quote its lines and say the person
    asked for them; do not undo them. Exit 2 means the base or path needs fixing.
    Skip guard after other tag or Context-column edits and unrelated file changes.
11. Never commit unless the person or repo instructions ask. Put the item id in
    the subject; keep the host's Co-Authored-By trailer. Report completion with evidence.

## Tools and formats

Paths are relative to the skill directory. The checker needs Python 3.9+:
`python3 <skill dir>/scripts/inwoven.py <command>`.
`check [FILE...]` skips missing optional files; for another filename use
`check --kind backlog FILE` or the corresponding kind.
`new-id --count N` mints random unused ids; `context ID` reads linked context.
`guard --base GIT_REF` needs git on PATH; it lists acceptance, row and id changes and never edits.
`init [KIND...] --root DIR` creates requested missing files from assets/; default
is backlog only. It never overwrites. Replace its marked example with the person's work.
New files have title and updated frontmatter. Never add frontmatter to existing files. Empty updated is absent; a nonempty updated value must be a real calendar date.

Read the matching reference before editing:

- [Backlog format](references/backlog-format.md)
- [Goals format](references/goals-format.md)
- [Impact format](references/impact-format.md)
- [Wardley format](references/wardley-format.md)

If a file uses another format, report the difference before applying these rules.
