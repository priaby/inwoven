# Wardley format

File: wardley.md beside the selected backlog.md, unless the person names another path.
One landscape describes the product. Read the components linked to the current item.

```markdown
---
title: "Example wardley"
updated: 2026-10-13
---
## Users
| User | Stage | Needs |
|---|---|---|
| People choosing work | Custom | Product context |

## Components
| Component | Stage | Row | Moving to | Depends on | Items |
|---|---|---|---|---|---|
| Product context | Genesis | 1 | Custom |  | K417 |
```

User cells per row: 3. Component cells per row: 6.
Stages: Genesis, Custom, Product, Commodity. Stage names are read without case sensitivity.
Keep every cell on one line. Do not put a pipe inside a cell, even an escaped pipe.
Name limit: 60 characters. Names are nonempty, contain no commas, and are unique
across users and components after whitespace is collapsed and case is folded.
A component Row is one to four digits with a value from 1 to 9999.
Moving to is empty or a later stage. Do not move backward or to the same stage.
Needs and Depends on are comma-separated component names; Items is a comma-separated
list of [backlog ids](backlog-format.md) and gaps, `GAP: <text>` (an item described, not in
the backlog yet; 1 to 80 characters, no `|`, `,`, `\` or `<br`, no control or invisible characters),
in any order, at most 50 entries together; a gap with the same text in another case is
read once. Empty lists are allowed.
Avoid unknown links, self-links, links to users and dependency cycles.
A component's place is its Stage, its Row and its line among the lines of that stage and
row. Rows are positions: the map numbers its rows 1, 2, 3... in the order of the Row values,
whatever numbers the file writes, so a file may skip numbers. The web map's `move` op (name,
stage, row as that position, optional index in that cell, `new_row` for a gap before the row)
changes the place: it rewrites the Stage and Row cells and moves only the moved component's
line among the component lines, and it leaves the rows dense (1, 2, 3...), changing only the
Row cells whose number changes. When you move one by hand, close up a row it leaves empty.
A gap is edited by the web map's `add_gap` (name, text: appends `GAP: <text>` to the Items cell),
`set_gap` (name, text, `to`: renames that gap in place) and `remove_gap` (name, text). The `attach`
op takes an optional `at`, the index among the entries the reader keeps (ids and gaps; a duplicate or an
entry it cannot read is not counted), so a promoted gap's id lands where the gap was. Keep a gap's place in
the cell when you edit it by hand, and when you promote one to a backlog item replace the `GAP:` entry with
the new id.

Keep the two section headings, headers and separator rows. Do not put table rows
after prose has ended a table. Leading and trailing pipes are optional in this format.
Malformed structure makes the map unreadable. Link problems, invalid ids, bad `GAP:` entries
and backward movement are reported even when the map still reads; fix them before claiming validity.
A missing wardley.md is allowed.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none.

Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.
