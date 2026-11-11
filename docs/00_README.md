# 00 — Golden Minute Docs: Start Here

Golden Minute is a multi-agent emergency coordination system for the common person: nine
AI agents turn reports (spoken in any language, even from someone who cannot read or type)
into one verified incident and alert, confirm and prepare every needed hospital, EMS, police
and fire unit within 60 seconds, describe the place by local landmarks, coach the bystander
through first aid, and help people prepare an Emergency Card in advance — with
deterministic guardrails and human control.

**This version is a 3-hour, local-only build: no GitHub push, no deployment.** The product
spec is complete; `10_BUILD_PLAN.md` says what is built in the 3 hours and in what order.

## How to use these docs

1. Put this `docs/` folder and `AGENTS.md` in the repo root.
2. Start with:
   > Read AGENTS.md, docs/00_README.md, docs/01_CONTEXT.md, docs/PROGRESS.md and
   > docs/10_BUILD_PLAN.md. We have 3 hours, local only: no GitHub push, no deployment.
   > We are starting T-02 (I am doing T-01 accounts myself). Before each task read the docs
   > it references. Use only names from the docs. Follow "reuse, don't rebuild". Build
   > autopilots first, then wrap agents. Update docs/PROGRESS.md after every task.
3. For each task: "We are at <clock>. Do T-xx. Show me how you verified its Check, then
   update PROGRESS.md." Local commits are optional; never push.
4. When the tool asks or guesses about something not in the docs, add the answer to the
   right doc or `DECISIONS.md` so the next session sees it.

## Reading order

| # | File | Read when |
|---|---|---|
| 1 | `../AGENTS.md` | always, before any code |
| 2 | `01_CONTEXT.md` | always |
| 3 | `architecture.html` | to understand the flow (animated, open in a browser) |
| 4 | `02_PRD.md` | building any feature (F-xx) |
| 5 | `03_TRD.md` | setting up, choosing libraries, file layout |
| 6 | `04_SYSTEM_ARCHITECTURE.md` | wiring components, jobs, failure handling |
| 7 | `05_DATABASE_SCHEMA.md` | any DB work (source of truth for names) |
| 8 | `06_API_SPEC.md` | any endpoint or frontend API call |
| 9 | `07_AI_AGENTS.md` | any agent, prompt, tool, template, content |
| 10 | `08_SECURITY.md` | every endpoint, webhook, tool |
| 11 | `09_DESIGN.md` | any UI |
| 12 | `10_BUILD_PLAN.md` | deciding what to do next (3-hour plan, cut lines) |
| 13 | `11_ENV_SETUP.md` | accounts, env vars, running locally (no deployment) |
| 14 | `12_TESTING_AND_DEMO.md` | tests (3H subset), demo data, demo script |
| 15 | `PROGRESS.md` | **first thing to read and last thing to update, every session** |

## Source-of-truth rules

- Names of tables/columns/enums → `05_DATABASE_SCHEMA.md`
- Endpoints and payloads → `06_API_SPEC.md`
- Agents, tools, prompts, templates, static content → `07_AI_AGENTS.md`
- Libraries and versions → `03_TRD.md`
- Intent and scope → `01_CONTEXT.md` / `02_PRD.md`
