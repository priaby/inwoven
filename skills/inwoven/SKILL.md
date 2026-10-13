---
name: inwoven
description: Work with Inwoven backlog.md, goals.md, impact.md and wardley.md. Use in repos with docs/product/backlog.md or when someone names these product files.
---

# Inwoven

Use this skill to read product context and work an item in an Inwoven backlog.
Use the product files the person names. Otherwise they are in docs/product/,
unless the repo's AGENTS.md gives another path.
Read the repo's AGENTS.md and follow its instructions before changing files.

## Product files

- backlog.md: one row per item. Row order is priority.
- goals.md: the goals, each with a measure and a horizon: Now, Next or Later.
- impact.md: one map per goal. It lists who must act differently, how, and the item ids that cause it.
- wardley.md: the landscape of users and components, each component linked to item ids.

## Working an item

- Work the highest item whose Status is In Progress. Start a To Do item only when the person who owns the backlog asks.
- When the person asks you to start a To Do item, set its Status to In Progress.
- Before you start, find the item's id in impact.md and read its goal, actor and change. If the id is not there, say so.
- Status is To Do, In Progress or Done. An empty Status cell means To Do. Tags follow `<br>`, such as Ready, Waiting on:, Due:, Accepted: and Reopened.
- If an item is blocked, add `Waiting on: <condition>` as a tag.
- Remove the `Waiting on:` tag when the condition is met.
- Never mark an item Done, add Accepted or Reopened tags, reorder rows or delete items. The person accepts and orders.
- Keep backlog.md valid: keep the header, five cells per row and every id. A title is at most 80 characters.

## Boundaries

- The person adds items. Never add rows, invent ids for existing items or reuse ids.
- If no item is In Progress and the person has not asked to start one, report that.
- If the item's impact link is missing, report the missing context before implementation.
- The impact.md section heading equals the goal text in goals.md.
  Read goals.md for the linked goal and measure. Read wardley.md when the item is
  attached to a landscape component, to understand its dependencies and movement.
- Work one item at a time. Report completed work with evidence for the person to accept.
  Report work detail to the person and in commit messages. Do not write it in the
  backlog file. A Status tag with no known prefix may hold 20 characters at most.
- Edit product context only within the person's request. Preserve unrelated text,
  every existing id and concurrent edits. Re-read the files before writing.
- Keep every changed file valid. If the file starts with frontmatter, set its
  `updated:` line to today as YYYY-MM-DD. Do not add frontmatter to a file that has none.
  Run the repo's format checks and relevant tests. If no checker exists, check the
  changed file against the reference and report what you checked.

## Format references

Read the matching reference before editing a document:

- [Backlog format](references/backlog-format.md): row shape, ids, statuses and tags.
- [Goals format](references/goals-format.md): horizons, measures and dates.
- [Impact format](references/impact-format.md): goals, actors, changes and item links.
- [Wardley format](references/wardley-format.md): users, components and dependencies.

These references describe the Inwoven formats. Do not apply them to unrelated files
that share a name. If the file uses another format, report the difference.
