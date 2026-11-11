# AGENTS.md — Rules for contributors working on Golden Minute

Read this file completely before writing code. Then read `docs/01_CONTEXT.md` and the doc
for the part you are building. These rules override your defaults.

**Build window: 3 hours, solo, local only.** There is NO GitHub push and NO deployment in
this build (no Vercel, Render, CI or Docker image). Everything runs on the developer's
laptop; one Cloudflare quick tunnel exposes it to a phone for the demo. Follow
`docs/10_BUILD_PLAN.md`, which lists exactly what is built in the 3 hours and what stays
documented for later. Never start a "later" feature before the 3-hour core works.

---

## Rule 0 — Do not hallucinate

1. **Names come from the docs.** Table, column, enum, endpoint, env var, file and function
   names MUST match `docs/05_DATABASE_SCHEMA.md`, `docs/06_API_SPEC.md`, `docs/03_TRD.md`
   exactly. Never invent a column or endpoint. If something you need is missing, STOP and
   add it to the relevant doc first (schema change = new migration file + doc update).
2. **Library APIs:** use only functions you are sure exist in the pinned version
   (`docs/03_TRD.md`). If unsure, read the library's official docs or installed source
   (`pip show -f`, `node_modules/<pkg>`) before using it. Never guess a method name.
3. **Model names** (Gemini/Groq) come from env vars only. Never hard-code them.
4. **No fake success.** Never stub a function to return success silently. Unfinished code
   raises `NotImplementedError("F-xx: <what is missing>")`.
5. When a doc is ambiguous, choose the simplest behaviour consistent with the PRD and
   write the decision in `docs/DECISIONS.md` (create it if missing): date, decision, reason.

## Rule 1 — Code smartly: reuse, don't rebuild

If a library or managed service already does it, USE IT. Custom code is allowed only for
glue code and logic unique to Golden Minute (agent instructions + tools, guardrails,
autopilots, confidence, message templates, route interpolation).

| Need | Use | Never hand-write |
|---|---|---|
| UI components | shadcn/ui (`npx shadcn@latest add <component>`) | your own buttons, dialogs, sheets, tabs, forms |
| Icons | lucide-react | inline SVG icon sets |
| Toasts | sonner | custom toast system |
| Maps | react-leaflet + leaflet; heatmap: leaflet.heat | canvas maps |
| Charts | recharts | SVG charts by hand |
| Server state / polling | @tanstack/react-query | useEffect fetch loops |
| Forms validation | zod | manual regex validation |
| i18n + RTL | i18next + react-i18next | custom translation dictionary code |
| Offline shell / SW | vite-plugin-pwa | handwritten service worker |
| Offline queue storage | idb-keyval | raw IndexedDB API |
| Auth, sessions, OTP | Supabase Auth | JWT signing/verification, OTP sending |
| Realtime updates | Supabase Realtime | websockets server |
| Geo queries | PostGIS functions in `05_DATABASE_SCHEMA.md` | distance math in Python for DB queries |
| Fuzzy names | pg_trgm `similarity()` | Levenshtein code |
| Distance (Python) | `geopy.distance.distance` | haversine formula by hand |
| Geocoding + country detection | geopy Nominatim (`address.country_code`) | raw HTTP to Nominatim, IP-geolocation services |
| Finding hospitals/stations anywhere | OpenStreetMap Overpass via `services/osm_discovery.py` | scraping maps sites, Google Places |
| Routing/ETA | OSRM HTTP API | Dijkstra/graph code |
| Request validation | FastAPI + Pydantic | manual dict checks |
| Settings | pydantic-settings | os.environ parsing |
| Rate limiting | slowapi | counters in dicts |
| Signed tokens | itsdangerous | custom HMAC token formats |
| Encryption | cryptography Fernet | any custom crypto |
| Retries | tenacity | while-loops with sleep |
| Scheduling | APScheduler | asyncio sleep loops |
| SMS/voice/TwiML/webhook validation | twilio SDK | XML strings, signature code |
| Telegram | python-telegram-bot | raw Bot API HTTP calls |
| Email | resend SDK | SMTP code |
| Web push | pywebpush | VAPID/ECE encryption code |
| Urdu TTS (en/es use TwiML `<Say>`) | gTTS | — |
| Phone parsing | phonenumbers | regex for phone numbers |
| Image handling | Pillow | — |
| Agents, tool calling, typed outputs | openai-agents SDK (`Agent`, `Runner`, `function_tool`, `AgentOutputSchema`, `RunHooks`) with Gemini/Groq OpenAI-compatible endpoints | custom agent loops, regex parsing of LLM text |
| Speech-to-text | Groq Whisper via `groq` SDK | — |
| QR codes (Emergency Card, Place Plan stickers) | `segno` (SVG/PNG output) | QR encoding code |
| Reading text aloud in the UI | browser `window.speechSynthesis` first; backend gTTS (`/api/v1/tts/ui`) if the device has no voice for that language | custom TTS, audio-file recording by hand |
| 3D command view (F-47) | `three` + `@react-three/fiber` + `@react-three/drei` (lazy-loaded, only `/command` and `/about`) | custom WebGL, 3D on reporter screens |
| Live Flow animation (F-46) | existing `architecture.html` SVG + CSS classes; Supabase Realtime | a charting/graph library |
| CPR metronome / beeps | Web Audio API `OscillatorNode` | audio libraries |
| Crash / fall detection (Ride Mode, F-44) | browser `DeviceMotionEvent` | sensor libraries |

Do not add any dependency not listed in `docs/03_TRD.md`. If one is truly needed, add it
to the TRD table with version and reason, then install it.

## Rule 2 — Safety-critical logic

- **Agents propose, guardrails decide.** Agents act only through tools; every tool
  validates against policy code (`08_SECURITY.md` S-17). Confidence, status, required
  recipients and message text are decided by code (`confidence.py`, `needs.py`,
  `dispatch.required_targets`, `messages.py`), never by an agent.
- Every agent has an autopilot (deterministic fallback). Agent failure must never stop an
  alert.
- Never give agents phone numbers, emails, chat ids or tokens in tool outputs.
- Never send SMS/calls to numbers taken from report text.
- Never write medical advice in code or prompts; first aid comes only from
  `backend/app/data/first_aid.json`. The Voice Coach Agent (F-39) may only choose which
  card and step to read; the words that are spoken come from the card file.
- Emergency Card data (F-36) is health-adjacent personal data: only the fields in
  `05_DATABASE_SCHEMA.md` (`emergency_cards`, `card_contacts`); never send card fields or
  contact phone numbers to an LLM; replace phone numbers by placeholders before any agent
  sees owner text (`07_AI_AGENTS.md` §6.7); card data enters hospital alerts only through
  fixed templates written by code.
- Every alert path must be idempotent (unique constraints + `on conflict do nothing`).
- Every state change calls `audit.log(...)` and, for incidents, `events.add(...)`.

## Rule 3 — Security (see `docs/08_SECURITY.md`)

- Never commit secrets. Never put service-role key, Twilio, Groq, Gemini, Resend, Telegram
  token, ACK_SECRET, encryption keys in frontend code or `VITE_*` vars.
- Every non-public endpoint uses `Depends(get_current_user)` and `require_role(...)`.
- Never log phone numbers, tokens, full transcripts or LLM prompts.
- Phone numbers: encrypt with `crypto.encrypt_phone`, look up by `crypto.phone_hash`.
- HTML-escape all dynamic text in Telegram (HTML mode) and email.

## Rule 4 — Code conventions

**Python:** 3.13, type hints everywhere, `async def` for I/O, Pydantic v2 models,
`ruff check` and `ruff format` clean, functions ≤ 60 lines, one service per file as in
`docs/03_TRD.md` §4. Enums in `models/enums.py` mirror DB enums by value.
Supabase python client: create one client in `deps.py` with the service role key;
it is synchronous — call it via `await asyncio.to_thread(...)` inside async functions
(or use the client's async variant `acreate_client` if available in the pinned version —
check before using).

**TypeScript/React:** strict mode, function components, hooks, no `any` (use `unknown` +
zod). Files: components `PascalCase.tsx`, hooks `useCamelCase.ts`, libs `camelCase.ts`.
All user-visible text through `t('key')` with keys in `en.json`, `es.json` and `ur.json`.
Reporter screens are **picture-first and voice-first** (`docs/09_DESIGN.md` §1): icon on
every button, a 🔊 listen button on every screen, no paragraph longer than two short lines.
Tailwind classes only (tokens from `docs/09_DESIGN.md`); no inline styles except dynamic
map sizes.

**Coordinates:** Our code uses `(lat, lng)`. OSRM and GeoJSON use `[lng, lat]`. Convert
only in `routing_osrm.py` and `utils/geo.py`.

**Time:** store UTC; display in the country profile `timezone` (US demo: America/Chicago).

## Rule 5 — Workflow

1. Follow `docs/10_BUILD_PLAN.md` in order. Do not start a task until its dependencies
   are done and their acceptance check passes.
2. After each task: run tests for touched modules, run the app, check the acceptance
   criteria, then make a LOCAL commit `F-xx: <summary>` (or `T-xx`) if the folder is a git
   repository. **Never `git push`. Never deploy.** Update `docs/PROGRESS.md` (see below).
3. Keep `.env.example` in sync with every new env var.
4. Before saying a feature is done, demonstrate it (test output or manual steps run).
5. Do not refactor unrelated code. Do not rename anything defined in the docs.
6. **Progress file:** read `docs/PROGRESS.md` first in every session. After every task set
   its status (`todo` / `doing` / `done` / `blocked`), the time spent, and write 1–3 lines
   under "Notes for the next tool" (what works, what is half-done, what to do next). If
   the tool or session changes, the next one continues from that file.

## Rule 6 — Definition of done (per feature)

- Matches the PRD functional requirements and acceptance criteria for its `F-xx`.
- Uses names from the docs exactly.
- Has the tests marked **3H** in `docs/12_TESTING_AND_DEMO.md` for that feature (other
  tests are written later).
- Handles the failure cases in `docs/04_SYSTEM_ARCHITECTURE.md` §9.
- Writes audit/events.
- UI strings exist in English, Spanish and Urdu.
