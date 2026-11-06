# Impact format

File: impact.md beside the selected backlog.md, unless the person names another path.
Read the item's goal, actor and change before working it.

```markdown
---
title: "Example impact"
updated: 2026-10-13
---
# Impact maps

## Make choices clear
<!-- goal-2 -->
- People choosing work
  - Explain the reason for the next item
    - K417 Explain the reason
    - GAP: Test whether the reason is clear
```

One `## <goal>` section per goal. The line right under the heading is the goal's id
as an HTML comment, `<!-- goal-2 -->`: the id is the key, the one in `goals.md`
(invisible on GitHub). A map belongs to its goal, never to a slot: Now, Next and Later
are positions, the map follows the goal when it moves. A section without the comment still
matches by its heading text (older files); add the comment when you touch it.
Goal headings must be nonempty and unique when whitespace is collapsed. The heading is the
goal text exactly as in goals.md, with runs of whitespace read as one space. Case differences
name different goals. If you reword a goal, change its map heading text too and keep the id comment.
A closed goal's map stays in the file under its id as history and is frozen: never edit a closed
goal's map (the product refuses it). When an item id appears in several maps, read maps for open goals first.
Goal heading limit: 200 characters.
Use three list levels: actor, impact, leaf. The impact states the actor's change.
Use spaces for indentation, never tabs. `-`, `*` and `+` list markers are read.
An actor or impact can have no children. Do not add a fourth level or prose inside a section.

Actor, impact and gap limit: 80 characters each. Keep them nonempty, on one line,
without pipes, `<br>` in any case, control or invisible format characters,
or a trailing backslash.
Actors per map: 10. Impacts per actor: 10. Leaves per impact: 30.
A leaf is an existing item id, or an id, a space and text, for example
`K417 Explain the reason`. Never put a dot, colon or markup after the id.
A gap is `GAP: <text>`, in capitals.
Use the [backlog id format](backlog-format.md). A gap must have nonempty text.
Do not repeat an item id within one impact. The same id can occur in other impacts.
An item under several impacts shows as one card with several connections.
Missing backlog ids are not parser format problems; report missing links.

Add backlog items only on the person's request; a gap does not authorize a row.
You may link an existing item under an existing impact when the person names
the goal or impact. Invent no actors or impacts. Replace a gap only when the
person says the item closes it.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none. Preserve unrelated sections.

Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.
