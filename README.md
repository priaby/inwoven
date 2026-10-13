# Inwoven

[Inwoven](https://backlog.works) connects product strategy and goals to an ordered backlog.
People and AI coding agents read the same Markdown files.

The [Inwoven skill](skills/inwoven/SKILL.md) tells an agent how to pick an item,
read why it matters and keep the product files valid. It includes references for
backlog.md, goals.md, impact.md and wardley.md.

## Claude Code

Run in Claude Code:

```text
/plugin marketplace add priaby/inwoven
/plugin install inwoven@inwoven
```

For a manual install, clone this repo and copy skills/inwoven/ to
~/.claude/skills/inwoven/. Invoke the standalone skill with /inwoven,
or the plugin skill with /inwoven:inwoven.

## Codex

Run in your terminal:

```sh
codex plugin marketplace add priaby/inwoven
codex plugin add inwoven@inwoven
```

Start a new session after installing. For a manual install, clone this repo and
copy skills/inwoven/ to .agents/skills/inwoven/ in your project.

## GitHub CLI

Needs GitHub CLI 2.90 or later.

```sh
gh skill install priaby/inwoven inwoven
```

## Claude.ai

1. Download inwoven.zip from [releases](https://github.com/priaby/inwoven/releases).
2. Turn on Code execution and file creation in Settings > Capabilities.
   On Team and Enterprise plans an owner turns it on under Organization settings > Plugins & skills.
3. Open [Customize > Skills](https://claude.ai/customize/skills).
4. Select +, then Create skill, then Upload a skill.
5. Choose inwoven.zip and turn the skill on.

## ChatGPT

Install the Inwoven plugin where your workspace allows plugins. A workspace admin
can import https://github.com/priaby/inwoven through Admin > Plugins > Add >
Import marketplace, then set the installation policy. Invoke the skill with @inwoven.

## AGENTS.md alternative

Copy this block into your repo's AGENTS.md.
For Claude Code, import AGENTS.md from CLAUDE.md with @AGENTS.md.

```markdown
## Product files

Our product files are in docs/product/. Change the path if yours differ.

- backlog.md: one row per item. Row order is priority.
- goals.md: the goals, each with a measure and a horizon: Now, Next or Later.
- impact.md: one map per goal. It lists who must act differently, how, and the item ids that cause it.

## Working an item

- Work the highest item whose Status is In Progress. Start a To Do item only when the person who owns the backlog asks.
- Before you start, find the item's id in impact.md and read its goal, actor and change. If the id is not there, say so.
- Status is To Do, In Progress or Done. An empty Status cell means To Do. Tags follow `<br>`, such as Ready, Waiting on:, Due:, Accepted: and Reopened.
- If an item is blocked, add `Waiting on: <condition>` as a tag.
- Never mark an item Done, add Accepted or Reopened tags, reorder rows or delete items. The person accepts and orders.
- Keep backlog.md valid: keep the header, five cells per row and every id. A title is at most 80 characters.
```

Copyright (c) 2026 Pavel Riaby. All rights reserved.
