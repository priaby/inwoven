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
list of [backlog ids](backlog-format.md). Empty lists are allowed.
Avoid unknown links, self-links, links to users and dependency cycles.

Keep the two section headings, headers and separator rows. Do not put table rows
after prose has ended a table. Leading and trailing pipes are optional in this format.
Malformed structure makes the map unreadable. Link problems, invalid ids and backward
movement are reported even when the map still reads; fix them before claiming validity.
A missing wardley.md is allowed.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none.

Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.
