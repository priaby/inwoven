# Learnings format

File: learnings.md beside the selected backlog.md, unless the person names another path.

```markdown
---
title: "Example learnings"
updated: 2026-10-21
---
# Learnings

| Lesson | Enforced by | Item | Date |
|---|---|---|---|
| Money is integer cents everywhere; a float total broke the invoice export | `tests/billing/test_cents.py` | K417 | 2026-10-02 |
| Run the importer against the sample file before changing a column name |  | K418 | 2026-09-30 |
| Export dates are DD.MM.YYYY, the partner importer rejects ISO |  |  | 2026-05-01 |
```

Keep the header line exactly as in the example.
Cells per row: 4. Lesson and Enforced by limit: 200 characters each.
Lesson is required: one line, a rule in the imperative or a fact with its cost.
Each Lesson is unique after whitespace and case are folded.
Enforced by is optional: the script, test, hook or gate that stops the mistake.
A lesson with Enforced by never expires.
Item is optional: one item id such as K417, the item whose work produced the lesson.
An id missing from backlog.md is a note, not an error.
Date is required: the day the person approved the line, or last approved it again.
Dates use YYYY-MM-DD and must be real calendar dates.
Expiry days: 90. For a row, age is today minus Date in days.
Live: Enforced by is not empty, or age is 90 or less. Day 90 is live; day 91 is expired.
A Date after today is read as live and reported as a note.
Live lessons cap: 30, checked rows included. Expired rows do not count.
Row order does not matter. A new lesson goes last. Do not add a second table.
Frontmatter is optional. Empty `updated:` is absent; a nonempty value must be a real YYYY-MM-DD date.

Agent rules:

- Add a row at the end; renew by changing only Date, and `updated`.
- Never reword a lesson, or fill Enforced by, without the person's yes.
- After yes write exactly the row shown. If the person edits it, show the row again and ask again.
- Compare a new lesson with every row first; the same or a close meaning is a renewal offer.
- Delete an expired row only when the person names it.
- Keep text on one line without pipes or `<br>`. Preserve unrelated content.
- If the file has frontmatter, set `updated:` to today as YYYY-MM-DD.
  Do not add frontmatter to a file that has none.
