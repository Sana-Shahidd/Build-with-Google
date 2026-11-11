# 01 — Project Context: Golden Minute

> Read this file first. It explains WHY the project exists, WHO it serves, and the
> fixed decisions every other document depends on. If anything in another document
> conflicts with this one, this one wins for intent; `05_DATABASE_SCHEMA.md` wins for
> names of tables/columns/enums; `06_API_SPEC.md` wins for endpoints;
> `07_AI_AGENTS.md` wins for agent names, tools and prompts.

---

## 1. One-line summary

Golden Minute is a **multi-agent emergency coordination system for the common person**:
when a severe accident or mass-casualty incident happens (crash, fire, blast, collapse,
shooting), nine AI agents turn reports — spoken in any language, even from someone who
cannot read or type — into one verified incident and, within 60 seconds, **alert and confirm
every hospital, ambulance, police and fire unit that is needed, tell them exactly where to
go using local landmarks, talk the bystander through first aid, and prepare hospitals
before the first patient arrives.** Everything that can be prepared in advance (an
**Emergency Card** on a helmet or wallet, a **Place Plan** for a shop or home) is prepared
before anything happens. Every agent action passes through deterministic safety
guardrails, and humans stay in the loop.

## 2. The problem (global)

Emergency response breaks down in the first minutes of a mass-casualty event, in every
country, for two different reasons:

- **Overloaded systems (e.g. the United States).** 911 centers are understaffed; dispatchers
  often work 12–16 hour shifts. During a mass shooting or disaster, hundreds of calls about
  the same event flood the lines, and dispatchers lose minutes de-duplicating them.
- **Missing systems (e.g. Pakistan and much of the Global South).** There is no unified
  dispatch; police, rescue and hospitals learn late, through scattered calls.

In both cases:
- **Hospitals find out last.** No surgeons called in, no blood ready, no beds freed.
- **Patients are not distributed.** Everyone is rushed to the nearest ER, which collapses
  while a trauma center 8 minutes away sits idle.
- **Language barriers** slow intake (Spanish, Urdu, and other non-English speakers).
- **People who cannot speak** (hiding from an attacker) or have **no internet** cannot report.
- **Families** flood hospitals and phone lines looking for relatives.

The delay we attack: **between "it happened" and "the right people know, have
acknowledged, and are ready."**

Third failure, the one this version targets: **the person on the spot cannot use the
system.** In many places the person who first reaches a crash is a rickshaw driver, a
shopkeeper or a student who does not read English, does not know which number to call,
has no address to give (people say "near the petrol pump after the mosque"), and is afraid
of being questioned. Apps that need typing, English, accounts or an exact address fail
exactly when they matter.

Pitch line: *"Whether 911 is overloaded or doesn't exist, Golden Minute makes sure every
responder and hospital knows — and is ready — within 60 seconds. You don't need to read,
type or know English: just press, speak, or scan."*

## 3. What Golden Minute is NOT

- It does NOT replace 911, Rescue 1122, police, fire or hospital systems. It alerts them.
- It does NOT dispatch on its own authority; humans (dispatchers, responders) act.
- It does NOT give medical diagnosis. First aid is static vetted content selected by an
  agent, never AI-written medical advice.
- **Agents propose; guardrails decide.** Agents reason and call tools, but every tool
  enforces policy (who may be contacted, confidence thresholds, rate limits). If an agent
  fails or proposes something invalid, a deterministic **autopilot** does the same job.

## 3.1 Design target: the common person (primary user)

Every reporter-side feature is judged against one person: **someone who has never used an
app with typing, reads little or no English, may read little Urdu, owns an Android phone,
and uses WhatsApp by voice note.** Therefore:

1. **No typing is ever required.** Everything can be done by pressing a big picture button
   or speaking in any language (Urdu, Punjabi, Pashto, Roman Urdu, English — Whisper
   auto-detects).
2. **No account, no sign-up.** Anonymous session; no name or phone asked from a reporter.
3. **Everything is also spoken.** Every reporter screen has a 🔊 button and reads itself
   aloud in the user's language (F-39 and `09_DESIGN.md` §1).
4. **Pictures before words.** Large icons and photos of what is happening; short text.
5. **Landmarks, not addresses.** Responders get "200 m after Kalma Chowk, opposite the
   petrol pump" in their own language (F-38).
6. **Prepared in advance.** Emergency Card (F-36) and Place Plan (F-37) are set up once, by
   voice, with a family member's help if needed (Preparedness Agent).
7. **Fear removed.** The app says in plain words that the helper will not be questioned or
   blamed and gives no name (F-42; check the local legal position before promising this
   in a real launch).

## 4. Users (personas)

| Persona | Who | Main need | Interface |
|---|---|---|---|
| **Common person (primary)** | Rickshaw driver, shopkeeper, student, parent — reads little or no English, may not read at all | Get help by pressing or speaking; be talked through first aid; have their own details ready if they are hurt | Big-button PWA with spoken guidance, Emergency Card QR, Place Plan poster, (later) WhatsApp voice notes |
| Reporter | Any bystander/victim | Report in seconds, in any language, even silently or offline | Reporter PWA (`/`), SMS, missed call |
| Dispatcher | Control-room operator | See all incidents + agent activity; verify/dismiss | Dashboard (`/dashboard`) |
| Hospital staff | ER charge nurse / in-charge | Pre-arrival brief, acknowledge, update capacity, log arrivals | Telegram + Dashboard |
| Police | Duty officer | Location, threat summary, acknowledge | Telegram + Dashboard |
| EMS / Rescue | Ambulance service | Location, casualties, assigned hospitals | Telegram + Dashboard |
| Fire | Fire station | Location, fire details | Telegram + Dashboard |
| On-call doctor | Specialist (trauma, burns…) | "Come in now" with summary | Voice call, email, Telegram |
| Community member | Blood donor / CPR-trained volunteer | When and where they're needed | Telegram, SMS |
| Family member | Relative of a possible victim, or listed on an Emergency Card | Which hospital is my relative at; be told when a card owner is hurt | Family finder (`/family`), Telegram notice (F-41) |
| Public | Anyone with the PWA + push enabled | "Avoid this area" warning | Web push |

## 5. Global design: country profiles

Everything country-specific lives in `backend/app/data/country_profiles.json`. **The profile
follows the reporter's location** (F-35): the backend detects the country from GPS and
returns that country's emergency numbers, languages, phone region, time zone and units.
`COUNTRY_PROFILE` is only the fallback before a location is known. Unknown countries get
the `DEFAULT` profile with the international number **112**. Hospitals, police, EMS and
fire are always chosen by distance from the incident; if an area has no data yet, they are
**discovered live from OpenStreetMap**. The frontend reads the profile from
`GET /api/v1/config?lat=&lng=`.

| Profile | Emergency buttons | Languages (first = default) | Phone region | Time zone | Units | Demo city |
|---|---|---|---|---|---|---|
| `PK` (**default, used for the demo**) | Rescue 1122, Police 15, Edhi 115, Fire 16 | ur, en | PK | Asia/Karachi | km | Lahore |
| `US` (second demo: "it follows the person") | 911 | en, es, ur | US | America/Chicago | miles | Houston, TX |
| `CA`, `MX`, `GB`, `IN`, `AU` | local numbers (911 / 911 / 999 + 112 / 112 + 108 / 000 + 112) | see profile | — | — | — | — |
| `DEFAULT` | 112 | en, es, ur | — | browser | km | — |

Supported UI and report languages: **English (`en`), Spanish (`es`), Urdu (`ur`, RTL)**.
Reports in other languages still work (Whisper + the LLM handle them); UI text falls back
to English.

Demo scenario (PK profile, scenario key `highway_crash`): a multi-vehicle crash on Ferozepur
Road, Lahore (a bus and two motorcycles, many injured, one rider unconscious wearing an
Emergency Card helmet sticker). Reports come in Urdu voice, Roman Urdu text and English
text; a bystander scans the helmet QR; the Landmark Agent describes the spot in Urdu;
the Voice Coach talks the bystander through bleeding control. The US/Houston profile is
the second demo (simulate location) to show the system is global. Hospital/police/fire
locations are seeded from OpenStreetMap; capabilities, beds and blood stock are MOCK
(`is_mock = true`).

## 6. The nine agents (six core + three common-person agents)

| Agent | Job | Main tools | Fallback (autopilot) |
|---|---|---|---|
| 🧠 Intake Agent | Understand a report (voice transcript, photo, text, any language) → structured incident data; ask a follow-up if unclear | `get_location_label` | rules classifier |
| 🔎 Verification Agent | Decide whether a report is a new incident or the same as an existing one | `find_nearby_incidents`, `get_incident_summary` | distance + type rule |
| 🏥 Triage Agent | Choose hospitals by capability, capacity and ETA; spread casualties | `get_hospital_options`, `propose_assignment_plan` | deterministic spreading algorithm |
| 📣 Dispatch Agent | Alert police / EMS / fire / hospitals in priority order; owns escalation | `get_required_targets`, `send_alerts` | send all required targets |
| 🩺 Hospital Prep Agent | Call in on-call specialists, ping blood donors and trained volunteers | `get_prep_options`, `call_doctors`, `ping_donors`, `ping_volunteers` | rule-based selection |
| 📝 Debrief Agent | Write the after-action report when an incident closes | `get_incident_timeline` | template report |
| 🧭 Landmark Agent | Turn coordinates + nearby OpenStreetMap landmarks into directions a person can follow ("200 m after the petrol pump, opposite the mosque") in the local language | none (structured input) | code template "Near {A}, {direction} of {B}" |
| 🗣 Voice Coach Agent | Understand what a stressed bystander says to the first-aid guide and pick the right card/step; short calming acknowledgements | none (typed output) | keyword intent classifier |
| 🪪 Preparedness Agent | Turn a spoken or typed description ("my name is…, blood group O+, my brother's number is…") into a draft Emergency Card or Place Plan for the owner to confirm | none (typed output; phone numbers replaced by placeholders) | guided step-by-step form |

A deterministic **Orchestrator** (code, not an LLM) runs the six core agents in order (the
Landmark Agent runs beside Intake) and writes every step to `agent_activity`, which the
dashboard shows as a live **Agent Activity feed**. The Voice Coach and Preparedness agents
run outside incident processing (on the reporter's phone request and at set-up time) but log
to the same feed. **Family notices (F-41) are templates sent by Dispatch code, not an
agent**, because alert text must never be written by an LLM (`AGENTS.md` Rule 2).

## 7. Fixed decisions (do not change without updating all docs)

| Area | Decision |
|---|---|
| Name | Golden Minute (incident short code prefix `GM-`) |
| Team / time | 1 developer (solo), **3 hours total** (`10_BUILD_PLAN.md`). Pitch in simple English; product UI Urdu-first |
| Budget | $0 — free tiers only |
| Strategy | **Reuse, don't rebuild** (see `AGENTS.md` Rule 1) |
| Frontend | One React app (Vite + TypeScript): reporter PWA + responder dashboard as routes |
| Backend | FastAPI (Python 3.13) |
| Agents | **OpenAI Agents SDK** (`openai-agents`) used with non-OpenAI models through OpenAI-compatible endpoints (Gemini and Groq). Tracing to OpenAI disabled. |
| LLMs | Gemini Flash / Flash-Lite (Google AI Studio free key) and Groq instruction model (free key); model per agent set by env vars |
| Speech-to-text | Groq `whisper-large-v3-turbo` |
| DB/Auth/Realtime/Storage | Supabase (Postgres + PostGIS + pg_trgm) |
| Alerts | **Web responder link `/r/<token>` (demo channel; Telegram is not usable in Pakistan and is OFF behind `TELEGRAM_ENABLED`)**, Twilio SMS + voice (trial, Tier L), Resend email, Web Push |
| Maps / routing | Leaflet + OpenStreetMap; OSRM public server with straight-line fallback |
| Hosting | **Local only.** Backend `uvicorn` on :8000 and frontend `vite dev` on :5173 (Vite proxies `/api` and `/webhooks` to :8000). One Cloudflare quick tunnel to :5173 gives the phone HTTPS (needed for mic, GPS, camera). **No GitHub push, no Vercel/Render, no CI, no Docker.** |
| Background jobs | APScheduler inside FastAPI, state in DB |

## 8. Feature tiers (ALL features stay documented; tiers = what fits in 3 hours)

Nothing is deleted from the product. The tier only says when it is built.

- **Tier 3H-A — Build in the 3 hours (the demo):** SOS + GPS (F-01), voice report (F-02),
  text report (F-04), **Intake Agent** (F-05), Verification and Triage as **autopilots**
  (F-06 rule fast-path + confidence; F-08/F-09 spreading algorithm), needs rules (F-07),
  Dispatch as code with **Telegram + dashboard ack** only (F-10/F-11/F-13 without the
  phone-call escalation), reporter live status (F-15), live map dashboard (F-14), Agent
  Activity feed (F-33), **Live Flow architecture view (F-46)**, PK profile + EN/UR (F-34), nearest hospitals from seeded
  OpenStreetMap data (F-35 seed part), first-aid cards (F-22), **Landmark Agent (F-38),
  Voice Coach Agent (F-39), Emergency Card + QR (F-36) with Preparedness Agent (F-40),
  bystander safety promise (F-42)**, audit log, core security controls. Real LLM agents in
  the 3-hour demo: Intake, Landmark, Voice Coach, Preparedness.
- **Tier 3H-B — Only if time remains, in this order:** the **3D command view + `/about`
  landing (F-47, T-14)**, the Verification, Triage and Dispatch **agent layers** over their
  autopilots (T-15…T-17), Place Plan (F-37), Family
  notice by Telegram (F-41), Hospital Prep Agent with doctor/donor Telegram pings
  (F-19/F-23/F-24), silent SOS (F-20), follow-up question (F-25), ambulance simulation
  (F-26), Debrief Agent (F-31 report only).
- **Tier L — Documented, built after the 3 hours:** SMS + missed-call triggers (F-18),
  Twilio voice escalation call (F-13 call step) + multilingual voice calls (F-28), email
  (F-27), public danger-zone push (F-21), family finder (F-29), hospital capacity console
  (F-30), analytics + heatmap (F-31), offline queue (F-32), live discovery for new cities
  (F-35 full), WhatsApp voice-note channel (F-43), Ride Mode crash detection (F-44),
  black-spot warnings (F-45).
- **Tier D — Roadmap (pitch only, NOT built):** CCTV/gunshot-sensor detection agent,
  NG911/CAD integration (e.g. via RapidSOS-style data feeds), Rescue 1122 integration,
  hospital EHR integration, native apps, paid zero-retention LLMs.

## 9. Glossary

| Term | Meaning |
|---|---|
| Report | One submission from one reporter via one channel. Many reports → one incident. |
| Incident | A real-world event formed from ≥1 merged reports. |
| Organization (org) | A hospital, police station, EMS/rescue station or fire station. |
| Alert target | One recipient that must be told about an incident; holds ack state. |
| Delivery | One message on one channel to one alert target. |
| Acknowledge (ack) | Recipient confirms they are responding. Any channel's ack counts. |
| Escalation | Automatic follow-up call when a target does not ack in 60 s. |
| Confidence score | 0–1 number deciding `review` / `unverified` / `verified`. |
| Casualty spreading | Splitting casualties across hospitals by capability and capacity. |
| Agent | An LLM with instructions, tools and a typed output, run by the Orchestrator. |
| Guardrail | Deterministic policy check inside a tool or after an agent output. |
| Autopilot | The deterministic fallback that does an agent's job if it fails. |
| Agent activity | A row in `agent_activity` shown live in the dashboard feed. |
| Country profile | Config of emergency numbers, languages, region, time zone, units, demo city; detected from the reporter's location. |
| Live discovery | Fetching nearby hospitals/stations from OpenStreetMap for an area with no data yet. |
| Emergency Card | A person's pre-registered card (name, blood group, allergies, up to 3 family contacts) with a QR sticker for a helmet, bike, rickshaw or wallet; a bystander scans it (F-36). |
| Place Plan | A shop/home/school/mosque registered in advance with its nearest hospitals and a "press for help" QR poster (F-37). |
| Landmark text | A human direction line ("near X, opposite Y") built from OpenStreetMap landmarks (F-38). |
| Coach turn | One exchange with the Voice Coach: what the person said → which first-aid card/step is read aloud (F-39). |

## 10. Assumptions

1. Responders in the demo are the developer's own phones/Telegram accounts.
2. Twilio trial sends SMS/calls only to verified numbers (the demo phones).
3. Resend without a verified domain sends only to the account owner's email.
4. Free-tier LLM providers may use prompts for training → only fake demo data.
5. OSRM public server is for light demo use; results cached per incident.
6. Free-tier rate limits are the main risk for multi-agent runs → agents are spread across
   Gemini and Groq models, and autopilot covers any rate-limit failure.
7. The demo runs on the developer's laptop; the phone reaches it through one Cloudflare
   quick tunnel. If the tunnel URL changes, restart it and re-set the Telegram webhook.
8. Whisper handles Urdu well and Punjabi/Pashto/Sindhi less reliably; test each language at
   setup (`scripts/agent_smoke.py --audio`) and say honestly which ones work.

## 11. Document map

| File | Purpose |
|---|---|
| `00_README.md` | Index and how to use these docs |
| `01_CONTEXT.md` | This file |
| `02_PRD.md` | Every feature (F-xx), user stories, acceptance criteria |
| `03_TRD.md` | Stack, pinned versions, repo layout, module contracts, config |
| `04_SYSTEM_ARCHITECTURE.md` | Components, agent flow, sequence and state diagrams |
| `architecture.html` | **Animated** architecture diagram (open in a browser) |
| `05_DATABASE_SCHEMA.md` | Complete SQL: enums, tables, functions, RLS, realtime |
| `06_API_SPEC.md` | Every endpoint, request/response, errors, webhooks |
| `07_AI_AGENTS.md` | The nine agents: instructions, tools, outputs, guardrails, fallbacks, content |
| `08_SECURITY.md` | Threat model and security controls |
| `09_DESIGN.md` | Screens, components, tokens, copy, i18n |
| `10_BUILD_PLAN.md` | 3-hour plan with ordered tasks, checks and cut lines |
| `PROGRESS.md` | Live task status + notes for the next tool (update after every task) |
| `11_ENV_SETUP.md` | Accounts, keys, env vars, local run (no deployment) |
| `12_TESTING_AND_DEMO.md` | Tests, sample reports, demo script, pitch |
| `../AGENTS.md` | Coding rules for the AI tool (read before writing code) |
