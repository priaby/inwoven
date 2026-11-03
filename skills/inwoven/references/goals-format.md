# Goals format

File: goals.md beside the selected backlog.md, unless the person names another path.

```markdown
---
title: "Example goals"
updated: 2026-10-13
---
# Product Goal

| Goal | Measure | Horizon | Set | Closed | Outcome | Id |
|---|---|---|---|---|---|---|
| Make choices clear | Fewer unexplained items | Now | 2026-10-13 |  |  | goal-2 |
| Test another direction |  | Next |  |  |  | goal-3 |
| Ship the first version | A person outside the team uses it | Now | 2026-09-01 | 2026-10-12 | Achieved<br>Three people signed up | goal-1 |
```

Keep the header line exactly as in the example.
Cells per row: 7. Goal and measure limit: 200 characters each.
Goal must be nonempty; Measure can be empty.
Horizons: Now, Next, Later.
Keep at most one open goal per horizon, in that order, before closed goals.
Now requires an ISO Set date. Next and Later require an empty Set cell.
Open goals have empty Closed and Outcome cells. Closed goals keep the Horizon they
were closed from (Now, Next or Later; an empty one reads as Now), have a valid ISO
Closed date and an Outcome of Achieved, Missed or Dropped, and a valid ISO Set date
unless they were dropped from Next or Later (those never had one); they
follow the open goals, newest closed first. An optional one-line note goes in the
Outcome cell after `<br>`, for example `Missed<br>The workshop passed without feedback`
(at most 200 characters, no pipe, no second `<br>`).
Dates use YYYY-MM-DD and must be real calendar dates.
Do not add a second table.

Every goal has a permanent id in the last column, `goal-<number>` (`goal-1`, `goal-2`, ...). The id is
for the system and for you: it keys the goal's impact map and it is never shown on a page. Give a new
goal the highest number in the file plus one. Never change an id and never reuse a number: nothing is
deleted, so a number is used once for good. The goal's page in the product is `/product/<id>/goals/<goal id>`.

The parser also reads the six-column table without `Id`, the older `| Goal | Measure | Horizon | Set | Achieved |`
table (every closed row counts as Achieved) and the legacy `| Goal | Set | Achieved |` table, and upgrades
them on write. In an older table, convert every row to seven columns before adding a goal: use Now on the
open goal and leave Horizon empty on closed goals; give every row that lacks an id the next number, in document
order, top to bottom (`goal-1` on the first row of a table with no ids), whatever the dates. The server mints in that
order too, so the two agree; adding a row by hand to an older table gives only that row a new number, and nothing renumbers.
To add a goal to an occupied horizon, ask once what happens to the old goal.
Move it to Next or Later only as requested, clearing Set; resolve occupied
horizons too. Close it only when the person says so, with the outcome they name (Achieved, Missed or
Dropped): set Closed to today and write the Outcome; keep the Horizon and the Set date. Closing the Now goal
moves Next to Now (Set today) and Later to Next. A Next or Later goal is only ever dropped: Outcome
Dropped, Closed today, no other row moves. Never delete a goal: there is no remove. To undo a close, put the
row back in the horizon it left (blank Closed and Outcome), reversing the shift.
Never close a goal on your own. If impact.md exists, add an empty `## <goal>` section
(with the id comment, see the impact format) for a new goal and say it has no actors yet. Create a missing map file
only when asked. Put a requested deadline in Measure in the person's words;
ask for the year if ambiguous.
Keep text on one line without pipes or `<br>`. Preserve unrelated content.
If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
Do not add frontmatter to a file that has none. Change goals only within the person's request.

Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.
