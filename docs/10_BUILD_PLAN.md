# 10 — 3-Hour Build Plan (solo, local only): Golden Minute

**Window:** 3:00 hours from start. **Local only:** no GitHub push, no deployment, no CI, no
Vercel/Render/Docker. Everything runs on the laptop; one Cloudflare tunnel lets the phone
reach it. A local `git commit` after each task is optional and never pushed.

The product spec (`02_PRD.md`) is unchanged and complete. This plan only decides **what is
built in 3 hours and in what order** (`01_CONTEXT.md` §8: Tier 3H-A / 3H-B / L).

**Method:** build a thin vertical slice first (a report becomes an alert on a web responder page that can be
acknowledged), then add the features that make Golden Minute different for the common
person. For every agent, build the **autopilot (deterministic) first**, then wrap the agent
around it; if time runs out the autopilot already gives a correct result.

After every task: run its **Check**, update `docs/PROGRESS.md`, then continue. Never start a
Tier 3H-B or L item before the **T-13 demo run** passes.

Legend: **Who** = You (accounts, phone) or Tool (the coding assistant) · **Deps** =
tasks that must be done first · **Check** = acceptance test you run.

---

## Timeline

| ID | Clock | Who | Task | Deps | Check |
|---|---|---|---|---|---|
| **T-01** | 0:00–0:15 | You (parallel to T-02) | Accounts and keys (`11_ENV_SETUP.md` §1): Supabase project, Google AI Studio key, Groq key, (Telegram is optional and OFF: not usable in Pakistan, see `11_ENV_SETUP.md`). Enable Anonymous sign-ins and Email (§5.1/§6 of `05`). **Skip** Twilio, Resend, Vercel, VAPID. | — | All keys in `backend/.env` |
| **T-02** | 0:00–0:20 | Tool | Scaffold the repo as `03_TRD.md` §4 (only the folders used in 3H-A): `AGENTS.md`, `docs/`; backend venv + `requirements.txt` (the 3H subset, see TRD §3); frontend `npm create vite@latest` (react-ts), Tailwind v4, `npx shadcn@latest init` + the components in `09_DESIGN.md`; `vite.config.ts` with `server.proxy` for `/api` + `/webhooks` → `localhost:8000` and `allowedHosts: ['.trycloudflare.com']`; `docs/PROGRESS.md` | — | `uvicorn` serves `/health`; `npm run dev` shows the app and `/api/v1/health`-style call works through the proxy |
| **T-03** | 0:20–0:30 | Tool + You | Run migrations 0001–0005, then 0006a, then 0006b in the Supabase SQL editor; `config.py` (Settings + constants, `COUNTRY_PROFILE=PK`), `country.py`, `GET /api/v1/config`; `scripts/gen_keys.py` (ACK_SECRET, FIELD_ENCRYPTION_KEY, PHONE_HASH_PEPPER); agents foundation `agents/models.py`, `runner.py`, `hooks.py`, `context.py`, `services/activity.py`; `scripts/agent_smoke.py` | T-01, T-02 | `/config` returns the PK profile (Urdu default, 1122/15/115/16); smoke prints ok for each model id (else change model, record in `DECISIONS.md`) |
| **T-04** | 0:30–0:40 | Tool | `scripts/seed_osm.py` for the Lahore bbox (`[31.38, 74.20, 31.62, 74.45]`: hospitals, police, fire, ambulance/rescue stations → `organizations`, `is_mock=true`, `source='seed'`); `scripts/seed_mock.py --demo-orgs` (capabilities, beds, 3 ambulances per rescue station; nearest hospital + police mapped to your two demo Telegram chats) | T-03 | ≥ 10 hospitals, ≥ 3 police in Lahore; demo orgs have Telegram chat placeholders |
| **T-05** | 0:40–1:05 | Tool | **Intake path (F-01, F-02, F-04, F-05, F-07, F-22):** `POST /reports` (validation, idempotency, rate limits, media with Pillow), Whisper `transcribe.py`, `rules_classifier.py` (autopilot), **Intake Agent**, SOS default, `needs.py`, `first_aid.py` + `first_aid.json`, basic `GET /reports/{id}/status` | T-03 | Golden reports 3 (Urdu), 6 and 12 (SOS) → correct type/severity; Urdu audio sample transcribed; feed rows in `agent_activity` |
| **T-06** | 1:05–1:15 | Tool | **Verification + Triage autopilots (F-06, F-08, F-09):** `merge.py` fast path (distance + type + time), `confidence.py`, short codes `GM-xxxx`; `routing_osrm.py`; `matching.spread()` + `validate_plan()` | T-04, T-05 | 3 reports within 200 m → 1 incident; 12 casualties spread across ≥ 3 hospitals |
| **T-07** | 1:15–1:35 | Tool + You | **Web responder channel + Dispatch (F-10, F-11, F-13 without calls):** `dispatch.required_targets` / `send_targets` (channel `dashboard`), `messages.py` (org alert, hospital brief with `landmark_line`/`card_line` slots), `ack_tokens.py` (per-alert ack token + per-org inbox token), `GET /responder/{token}`, ack endpoints, responder page `/r/:token` (mobile-first, EN/ES/UR, polls every 3 s, big ✅ button), `scripts/demo_links.py`; start the tunnel last. Telegram code exists but is disabled (`TELEGRAM_ENABLED=false`) | T-04, T-06 | **H1:35 checkpoint:** curl a report → the incident appears → both `/r/…` pages (hospital, police) show the alert → press ✅ → `alert_targets` acknowledged (`acknowledged_via='dashboard'`) → reporter status shows ✅ |
| **T-08** | 1:35–1:55 | Tool | **Reporter app (F-01, F-02, F-04, F-15, F-22, F-34, F-42):** i18n EN/UR (ES keys present), RTL, anonymous session, `Home` (SOS with countdown, hold-to-speak, type, call buttons from config, `SafetyPromise`, `ListenButton` / `lib/speak.ts`), `ReportStatus` (ticks, first-aid cards, landmark slot), `CoachSheet` that reads the first-aid card step by step with Next/Repeat and the CPR metronome (no agent yet) | T-07 | On the phone via tunnel: SOS and a voice report in Urdu → status page → ticks turn ✅ after the Telegram ack; 🔊 reads the page in Urdu |
| **T-09** | 1:55–2:10 | Tool | **Dashboard (F-14, F-33 minimal):** login, Leaflet map (incidents, hospitals), incident list, incident detail (targets, assignments, reports), **Agent Activity feed + Agent Lights** via Realtime | T-07 | New incident appears without refresh; feed rows show live |
| **T-09b** | 2:10–2:20 | Tool | **Live Flow (F-46):** copy the `<svg>` from `docs/architecture.html` into `components/flow/flow.svg`, `LiveFlow.tsx` + `flowMap.ts` (`09_DESIGN.md` §3.15 table), Realtime subscriptions, live log, Replay | T-09 | Demo burst lights Intake → Landmark → Verification → Triage → Dispatch → responders → ack in order; forced agent failure flashes amber |
| **T-10** | 2:20–2:28 | Tool | **Landmark Agent (F-38):** `services/landmarks.py` (Overpass), agent + validation + template autopilot; saved on the incident; shown in alerts, hospital brief, status page | T-06, T-07 | Crash-site coordinates produce a landmark line (Urdu + English) naming a real Overpass landmark; Overpass blocked → alerts still sent |
| **T-11** | 2:28–2:36 | Tool | **Voice Coach (F-39):** `POST /reports/{id}/coach`, Whisper turn, **Voice Coach Agent** + validation + keyword autopilot, `coach` UI mic button, `GET /tts/ui` fallback | T-08, T-05 | Saying "khoon nahi ruk raha" → bleeding card in Urdu is read; with a bad model id the same phrase still works |
| **T-12** | 2:36–2:52 | Tool | **Emergency Card (F-36, F-40):** `cards` + `redact` + **Preparedness Agent** + guided-form autopilot; `/card/new` wizard, print sheet with QR (`segno`), public scan page `/c/:token`, **Get help** → report with `card_id`; `card_line` in the hospital brief; delete card | T-08, T-07 | Create a card by voice → confirm → print page shows QR → scan with a second phone → **Get help** → incident on the dashboard with the card line |
| **T-13** | 2:52–3:00 | Tool + You | `scripts/demo_burst.py --scenario highway_crash` + `/dev/simulate-reports` + `/dev/reset-demo`; run the demo script (`12` §4) once; start the tunnel last and print the card sticker after it is up | T-12 | The 3-minute demo works end to end once. **Stop building.** |

**Clock note:** Live Flow (T-09b) is the judge-facing "live architecture" and is cheap (the
SVG already exists), so it gets 10 minutes and T-10…T-13 are shortened to fit the same
3:00. To make room, the *agent layers* of Voice Coach and Preparedness are the first things
to cut (both keep their autopilots: keyword intents and the guided form). If you are behind,
skip T-09b's Replay mode first, never its Live mode.

If everything above is finished early, continue with Tier 3H-B in this order (each ≤ 10–15
min): **T-14** 3D command view (F-47: `npm i three @react-three/fiber @react-three/drei`,
lazy-loaded, 2D fallback) and the `/about` landing, **T-15** Verification Agent, **T-16**
Triage Agent, **T-17** Dispatch Agent (agent layers over the autopilots), **T-18** Place
Plan (F-37), **T-19** Family notice (F-41),
**T-20** Hospital Prep Agent + doctor/donor pings (web responder link; Telegram only if enabled), **T-21** silent SOS and
follow-up question (F-20, F-25), **T-22** ambulance simulation (F-26), **T-23** Debrief
Agent. Tier L items (`01_CONTEXT.md` §8) are not part of the 3-hour build.

---

## Cut lines (when behind — apply in this order)

| If at this clock you are not done with… | Do this |
|---|---|
| 1:05 and T-05 not done | Drop the Intake **Agent**; ship with `rules_classifier` only (it is the autopilot); add the agent at the end |
| 1:35 and T-07 not done | Drop the per-alert `ack_tokens` check; keep only the responder-page ✅ and dashboard ack |
| 2:10 and T-08/T-09 not done | Dashboard = incident list + Agent Activity feed (no map) |
| 2:36 and T-11 not done | Voice Coach = card reading + keyword intents only (no agent call, no TTS fallback) |
| 2:52 and T-12 not done | Card by guided form only (no Preparedness Agent); skip print layout polish (show QR on screen) |
| Anything at 2:52 | **Stop building.** Rehearse with what works and say honestly what is "next" |

Never cut: SOS + voice report, Intake, an incident on the dashboard, a responder-page alert with a
working ✅, reporter status ticks, the Agent Activity feed, the Urdu UI.

## Checkpoints

| Clock | Must be true |
|---|---|
| 0:30 | Migrations done; smoke test passes for every agent model; PK profile served |
| 1:35 | Backend vertical slice: report → responder-page alert → ack (by curl) |
| 2:10 | Phone demo works: SOS/voice → status ticks; dashboard shows the incident and agent feed; Live Flow animates (by 2:25) |
| 2:52 | Landmark, Voice Coach and Emergency Card work (or are cut per the table) |
| 3:00 | Demo rehearsed once; backup screen recording started if time allows |

## Time boxes for the tool

Tell the tool the clock: "We are at 1:05; T-05 is done; start T-06." If a task overruns by
more than 5 minutes: write the blocker in `DECISIONS.md`, keep the autopilot path working,
update `PROGRESS.md`, and move on.
Dispatcher123