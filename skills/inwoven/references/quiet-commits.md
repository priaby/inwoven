# Quiet commits

Read once, at the end of GitHub setup. Goal: a board edit starts no build or deploy.

## What Inwoven commits

Inwoven commits each board edit to the default branch as `backlog-works[bot]`.
Every message ends with the line `[skip ci] [skip render] [skip-cd]`.
GitHub Actions, GitLab CI, CircleCI, Buildkite, Netlify, Render and AWS Amplify read it and skip the build.
Change nothing for them.
Vercel and Railway read no marker. They need a path filter in a repo file.
Cloudflare Pages, Heroku and Fly.io have no repo file for it.

## When you act

Look in the repo root once. Ask the person nothing.
- `vercel.json`, `railway.json` or `railway.toml` exists: add the filter below in the same commit as the AGENTS.md block. Tell the person in one sentence.
- None exists: change nothing and say nothing.
- The repo uses Cloudflare Pages, Heroku or Fly.io: say one sentence from "Dashboard only".

Replace `docs/product` with the folder that holds the person's product files.
Keep every other key. If the key is already set, extend it, never replace it.

## Vercel

Add to `vercel.json`. Vercel ignores the build when the command exits 0 and runs it on 1.

```json
{ "ignoreCommand": "git diff --quiet HEAD^ HEAD -- . ':!docs/product/backlog.md' ':!docs/product/goals.md' ':!docs/product/impact.md' ':!docs/product/learnings.md' ':!docs/product/wardley.md'" }
```

Exit 0 means the last commit changed only those files. A push of several commits is judged by its last commit.
Vercel counts an ignored build in the deployment quota.

## Railway

Add to `railway.json`. Railway skips the deploy when no changed file matches a pattern.
A pattern that starts with `!` removes files an earlier pattern matched, so the list starts with `**`.

```json
{ "build": { "watchPatterns": ["**", "!/docs/product/backlog.md", "!/docs/product/goals.md", "!/docs/product/impact.md", "!/docs/product/learnings.md", "!/docs/product/wardley.md"] } }
```

In `railway.toml` set the same list as `watchPatterns` under `[build]`.
Railway marks these files deprecated and reads them until 2026-12-01. A repo with `.railway/` keeps its settings there: leave it and say so.

## Dashboard only

- Cloudflare Pages: Settings, Build, Build watch paths. Exclude the product files.
- Heroku and Fly.io: no setting skips a deploy by file path.

Name the setting or the gap in one sentence. Do not ask the person to change it.

## Sources

- Vercel `ignoreCommand`: https://vercel.com/docs/project-configuration/vercel-json
- Railway `watchPatterns`: https://docs.railway.com/reference/config-as-code
- Railway pattern syntax: https://docs.railway.com/builds/build-configuration#configure-watch-paths
- Cloudflare Pages: https://developers.cloudflare.com/pages/configuration/build-watch-paths/
