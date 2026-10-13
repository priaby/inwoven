# Goals format

File: docs/product/goals.md, or the named sibling of backlog.md.

```markdown
---
title: "Example goals"
updated: 2026-10-13
---
# Product Goal

| Goal | Measure | Horizon | Set | Achieved |
|---|---|---|---|---|
| Make choices clear | Fewer unexplained items | Now | 2026-10-13 |  |
| Test another direction |  | Next |  |  |
```

Cells per row: 5. Goal and measure limit: 200 characters each.
Goal must be nonempty; Measure can be empty.
Horizons: Now, Next, Later.
Keep at most one open goal per horizon, in that order, before achieved goals.
Now requires an ISO Set date. Next and Later require an empty Set cell.
Open goals have an empty Achieved cell. Achieved goals have an empty Horizon,
valid ISO Set and Achieved dates, and follow the open goals, newest achieved first.
Dates use YYYY-MM-DD and must be real calendar dates.
Do not add a second table.

The parser also reads the legacy `| Goal | Set | Achieved |` table and upgrades it
on write. Use the five-column format for new content.
Keep text on one line without pipes or `<br>`. Preserve unrelated content.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none. Change goals only within the person's request.
