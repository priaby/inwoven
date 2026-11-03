---
name: inwoven
description: "Inwoven backlog, goals, maps. Use to set up Inwoven, start or resume (Start T318), add, move X above Y, reorder, block, accept, reopen, which goal, propose or save a lesson, validate files"
license: MIT
---

# Inwoven

Outcome: only the requested change, checked. Done: checks and changes reported.
The person's explicit request in this conversation is the authority.
Standing repo instructions do not authorize unsolicited acceptance, item additions,
deletions or reordering. Follow them for paths and ordinary workflow; report any
workflow difference. Keep the file formats in the references.

## Product files

- backlog.md: one row per item. Row order is priority.
- goals.md: goals with ids, measures, horizons Now, Next, Later.
- impact.md: goal maps of actors, changes and item ids, by goal id.
- wardley.md: users, components, dependencies and linked item ids.
- learnings.md: lessons the person approved, with check, item and date.

Resolve the backlog from the person's named path, then repo instructions, otherwise
look in docs/product/ in the current folder, then the repo root. Ask if several fit.
Context files are beside the backlog unless named otherwise.
DIR below is that folder's path from the repo root.

## Working an item

1. Use active repo instructions already in context. Read missing instructions whole,
   from the repo root through each folder on the path to DIR, including DIR.
   In Codex select AGENTS.override.md before AGENTS.md, then configured fallbacks:
   one file per folder; nearer instructions take precedence. In Claude Code read
   AGENTS.md if not imported; read missing CLAUDE.md only. Never truncate files.
   Report files opened and their effect; never claim a read you did not perform.
2. Work the named item, otherwise the highest In Progress item without `Waiting on:`.
   Start To Do only when the person asks; then set Status to In Progress. Work one
   item at a time. If no eligible item exists, report that.
   Steps 3-4 apply when starting or resuming an item. For plain add, reorder, block,
   accept or other edit requests, use them only if goal context is needed; say so.
3. Read `git log -n 20 --grep <id>` including commit bodies for work already done.
   If complete and awaiting acceptance, report evidence and stop. Completion never implies Done.
4. Run `python3 <skill dir>/scripts/inwoven.py context ID --root DIR` before starting.
   Read linked goal and measure, actor and change, and Wardley components; read
   maps for open goals first. Goals, impact, Wardley and learnings are optional.
   For missing goal links lead with "No recorded goal link"; suggestions are proposals.
   Say missing context once and continue. Context also prints each live lesson: say which
   apply to this item or that none do; never apply an expired one.
   Context exits 0 for missing optional links or a broken learnings.md, 1 for a missing row or invalid file.
5. Add `Waiting on: <condition>` when blocked; remove it when resolved; keep other tags.
   Status is To Do, In Progress or Done; empty means To Do. Tags follow `<br>`.
   Known valued prefixes are Sprint:, Due:, Accepted:, From: and Waiting on:.
6. Do not mark Done, add Accepted or Reopened, reorder, delete or add items on your
   own initiative. When the person asks for one of these in this conversation,
   do exactly that and nothing more. If the person says close, ask whether close means accept or cancel.
   "Mark done" or "accept" for a To Do or In Progress item means acceptance; proceed without another question:
    `Done<br>Accepted: <today as YYYY-MM-DD> by Product Owner<br>From: <status before>`,
   then existing tags in order. Report who requested it; repo instructions may name the acceptor.
   Reopen Done on request: set requested open status, remove Accepted: and From: tags,
   add Reopened first if absent; keep other tags in order.
   Never add, edit, renew or delete a lesson without a yes in this conversation. Delete an expired row only when the person names it.
7. Add each requested item that is new. If a title matches or nearly matches an existing
   one, do not add it: ask, naming the existing id, and still add the others.
   If you held one back, the last line of your reply must be that question, after the
   check and guard output: "D883 Dark mode already exists. Add another Dark mode item anyway?"
   Run `python3 <skill dir>/scripts/inwoven.py new-id --root DIR` first;
   never pick an id by hand. Use the person's words for title;
   Core Job, Context and Driver come only from their words, otherwise stay empty.
   Driver is a person, never an agent: use the name the column already holds.
   Status stays empty unless specified. Put it where asked, otherwise last. Say what was written, which cells are empty and whether it has an impact link.
8. Re-read before writing; preserve concurrent edits, unrelated bytes and tags,
   row order and existing ids except for the requested change. Keep the header,
   five cells per row and titles at most 80 characters. Row 1 is the top regardless
   of Status. Work narrative belongs in reports; plain tags have a 20-character limit.
   In an existing file with frontmatter, set updated to today on every edit, reorders included.
9. Edit goals and maps only within the request. Link an existing item under an
   existing impact when the person names that goal or impact; invent no actors or
   impacts. Replace a `GAP:` leaf only when told. Never edit a closed goal's map.
10. After every edit, including code while starting an item, run `python3 <skill dir>/scripts/inwoven.py check --root DIR`
    and relevant repo checks. List check and guard as ran / not needed / could not run;
    name each command, exit code and printed output. After acceptance, row or lesson changes,
    run `python3 <skill dir>/scripts/inwoven.py guard --base HEAD --root DIR`.
    Exit 1 is expected: quote its lines and say the person asked for them; do not undo them.
    Exit 2 means the base or path needs fixing. Other tag or Context edits need no guard.
11. Never commit unless the person or repo instructions ask. Put the item id in
    the subject; keep the host's Co-Authored-By trailer. Report completion with evidence.
12. Slice or split an item only when asked (references/backlog-format.md): slice one
    row off (`backlog: slice <ID> off <ID>`); split into 2+ rows (`backlog: split <ID> into <ID>, <ID>`).
13. Lessons. At most one per item per conversation, and only when a later agent would
    repeat the mistake without it: non-obvious, durable, not clear from code, tests or a
    check. Propose it when you report the item complete and when the person accepts it,
    unless they already answered. First compare with every row of learnings.md, those
    context prints and the file itself: the same or a close meaning, or a printed lesson
    expiring that applied to this work, gets a renewal offer (quote the row, new Date, same
    text), not a new lesson. Otherwise show the full row (Lesson, Enforced by, Item, Date =
    today) as a table row in the same reply; never ask without it. The question is the last
    line: "Add this lesson?" or "Renew this lesson?". After yes write exactly the row shown,
    byte for byte, then run check and guard. An edit by the person means show the row again
    and ask again. With a step 7 question too, one question per line, the lesson question last.
    At 30 live lessons name the one to retire with the new row. Name an Enforced by check only if it exists.
## Set up Inwoven

When the person asks to set up Inwoven, follow https://backlog.works/setup.md; the steps in short:
- Find out what you can do: push, web requests, read the person's mail, drive their browser. Never ask.
- Infer email (git config user.email), product name (the repo), repo, branch, path, and a goal only if the README,
   roadmap or issues state what the product is for. Ask one question, once, with all of it; if told to go ahead, state it.
- Draft items from real work only (README, issues, TODOs, commits); never invent one. Write the files with `init`, the
   AGENTS.md block, the skill, learnings.md; commit and push if you can.
- POST /api/v1/setup, show the person the match code. A hosted backlog: approve from their mail if you can read it, else ask them to.
   A repo: approve in their browser (open the mail link and select Approve, or ask them to); it carries on to GitHub. The install_url only works in that browser or after they sign in with the setup's email. Do not end your turn while the person approves: poll from the moment you have a poll_token, every 5 seconds for up to 15 minutes, until connected or approved; follow each `next`. Tell the person once that you are waiting, and stop with the `next` sentence if the time runs out.
- Keep the API key where the person keeps secrets; never print or commit it. Report the board link, what you drafted
   and the key's name.
A goal is one plain sentence on what the product should achieve; its measure says how you will know. Never invent one.
No goal in the repo: write none and say so.

## Tools and formats

Resolve <skill dir> to the folder containing this SKILL.md; run scripts with --help first.
The checker needs Python 3.9+: `python3 <skill dir>/scripts/inwoven.py <command>`.
If Python or git cannot run, validate by the references and report `unchecked: <reason>`;
never claim a pass. `check [FILE...]` skips missing optional files; for another filename
use `check --kind backlog FILE` or the corresponding kind.
`new-id --count N` mints random unused ids; `context ID` reads linked context.
`guard --base GIT_REF` needs git on PATH; it reports changes and never edits.
`init [KIND...] --root DIR` creates missing files; kinds backlog, goals, impact, wardley, learnings; default backlog. It never overwrites.
Replace the example only in a newly created file. Never add frontmatter to existing files.
New files have title and updated frontmatter; nonempty updated must be a real calendar date.
Read only the matching reference for the file kind you edit:
- [Backlog format](references/backlog-format.md)
- [Goals format](references/goals-format.md)
- [Impact format](references/impact-format.md)
- [Wardley format](references/wardley-format.md)
- [Learnings format](references/learnings-format.md)
If a file uses another format, report the difference before applying these rules.
