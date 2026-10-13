# Goals format

File: goals.md beside the selected backlog.md, unless the person names another path.

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

Keep the header line exactly as in the example.
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
on write. In a legacy table, convert every row to five columns before adding
a goal: use Now on the open goal and empty Horizon on achieved goals.
To add a goal to an occupied horizon, ask once what happens to the old goal.
Move it to Next or Later only as requested, clearing Set; resolve occupied
horizons too. Mark it achieved only when the person says so; set Achieved to today.
Never delete a goal on your own. If impact.md exists, add an empty `## <goal>`
section for a new goal and say it has no actors yet. Create a missing map file
only when asked. Put a requested deadline in Measure in the person's words;
ask for the year if ambiguous.
Keep text on one line without pipes or `<br>`. Preserve unrelated content.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none. Change goals only within the person's request.

Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.
