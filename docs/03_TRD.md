# 03 — Technical Requirements Document (TRD): Golden Minute

This document fixes the stack, versions, folder layout, module responsibilities and
configuration. **Use exactly these libraries. Do not add alternatives without updating
this file.** Versions were checked on npm/PyPI on 2026-10-16 (`segno` on 2026-11-10); pin them.
**Local-only build:** nothing in this stack requires a deployment platform.

---

## 1. Runtime versions

| Runtime | Version |
|---|---|
| Node.js | 22.x LTS |
| Python | 3.13 |
| Package managers | `npm` (frontend), `pip` + `requirements.txt` with a venv (backend) |

## 2. Frontend dependencies (`frontend/package.json`)

| Package | Version | Used for |
|---|---|---|
| react, react-dom | 19.3.1 | UI |
| vite | 8.3.4 | build/dev server |
| @vitejs/plugin-react | 6.1.2 | React in Vite |
| typescript | 7.0.2 | types (if the shadcn/Vite templates require TS 5.x, use the version the template installs and note it here) |
| tailwindcss, @tailwindcss/vite | 4.3.3 | styling |
| shadcn (CLI, dev) | 4.22.0 | generates UI components into `src/components/ui` |
| lucide-react | 1.58.0 | icons |
| sonner | 2.0.8 | toasts |
| @supabase/supabase-js | 2.118.0 | auth, realtime, DB reads, storage signed URLs |
| @tanstack/react-query | 5.104.3 | API calls, polling, caching |
| react-router-dom | 7.18.4 | routing |
| zod | 4.6.7 | validating API responses and forms |
| three | 0.187.0 | 3D engine for the 3D command view (F-47, Tier 3H-B) |
| @react-three/fiber | 9.8.2 | React renderer for three (F-47) |
| @react-three/drei | 10.7.9 | `OrbitControls`, `Html`, `Float`, `QuadraticBezierLine` helpers (F-47) |
| @types/three | 0.187.0 | dev types |
| leaflet | 1.9.4 | maps |
| react-leaflet | 5.0.0 | React bindings for Leaflet |
| @types/leaflet | 1.9.22 | types |
| leaflet.heat | 0.2.0 | heatmap layer |
| recharts | 3.10.1 | analytics charts |
| i18next | 26.4.7 | translations |
| react-i18next | 17.0.20 | React bindings |
| vite-plugin-pwa | 2.0.0 | service worker, manifest, offline shell |
| idb-keyval | 6.3.0 | offline report queue in IndexedDB |
| date-fns | 4.4.0 | time formatting ("42 s ago") |
| vitest (dev) | 5.0.5 | unit tests |
| @playwright/test (dev) | 1.64.1 | one end-to-end smoke test |
| eslint (dev) | 10.13.0 | linting |

## 3. Backend dependencies (`backend/requirements.txt`)

**3-hour build:** install only what Tier 3H-A uses. Keep the full pinned list below, but put
`twilio`, `resend`, `pywebpush` (Tier L) in `backend/requirements-later.txt` and do not
install them now. Frontend: skip `three`, `@react-three/*` until T-14 (3D), and skip `recharts`, `leaflet.heat`, `vite-plugin-pwa`, `idb-keyval`,
`@playwright/test` and `date-fns` until Tier L (install them when the feature is built).

```
fastapi==0.143.3
uvicorn[standard]==0.54.0
pydantic==2.14.1
pydantic-settings==2.16.0
python-multipart==0.0.32
supabase==2.33.0
openai-agents==0.24.0
openai==3.31.0
groq==1.7.0
twilio==9.12.0
python-telegram-bot==22.8
resend==2.49.1
pywebpush==2.5.0
gTTS==2.5.4
slowapi==0.1.10
itsdangerous==2.2.0
cryptography==50.0.2
apscheduler==3.11.3
httpx==0.28.1
tenacity==9.2.1
phonenumbers==9.0.41
segno==1.6.6
geopy==2.5.0
Pillow==12.3.0
pytest==9.1.1
pytest-asyncio==1.4.0
respx==0.23.1
ruff==0.17.1
```

| Library | Used for (never hand-write these) |
|---|---|
| fastapi + pydantic | HTTP API, request validation, OpenAPI docs |
| pydantic-settings | loading and validating env config |
| supabase (python) | DB access with service role, storage uploads, auth admin |
| openai-agents | the nine agents: `Agent`, `Runner`, `function_tool`, `RunHooks`, typed outputs (used with Gemini + Groq via OpenAI-compatible endpoints) |
| openai | `AsyncOpenAI` clients pointed at Gemini/Groq base URLs (required by openai-agents) |
| groq | Whisper transcription (`whisper-large-v3-turbo`) |
| twilio | SMS, voice calls, TwiML (`twilio.twiml.voice_response`, `messaging_response`), webhook signature (`twilio.request_validator.RequestValidator`) |
| python-telegram-bot | Telegram bot: messages, inline keyboards, webhook update parsing |
| resend | transactional email |
| pywebpush | Web Push with VAPID |
| gTTS | Urdu text-to-speech MP3 |
| slowapi | rate limiting |
| itsdangerous | signed, timed ack tokens |
| cryptography (Fernet) | encrypting phone numbers at rest |
| apscheduler | periodic jobs (escalation, simulation, retention) |
| httpx | OSRM and Overpass HTTP calls (async) |
| tenacity | retries with backoff for LLM/HTTP calls |
| phonenumbers | parsing/normalizing to E.164 (default region = profile `phone_region`) |
| geopy | Nominatim geocoding of SMS location hints; haversine via `geopy.distance` |
| Pillow | re-encoding photos (strips EXIF), size limits |
| segno | QR codes for Emergency Card / Place Plan stickers: `segno.make(url, error='q')` then `.svg_inline(scale=...)` or `.save(buffer, kind='png', scale=...)` |
| respx | mocking httpx in tests |

Browser built-ins used (no packages): `speechSynthesis` (read aloud), `MediaRecorder`
(voice), `navigator.geolocation`, Web Audio API (CPR metronome), `DeviceMotionEvent`
(Ride Mode, Tier L).

## 4. Repository layout (monorepo)

```
golden-minute/
├── AGENTS.md                      # coding rules for AI tools (read first)
├── README.md                      # project intro + run instructions
├── docs/                          # these documents
├── supabase/
│   ├── migrations/
│   │   ├── 0001_extensions_enums.sql
│   │   ├── 0002_tables.sql
│   │   ├── 0003_functions.sql
│   │   ├── 0004_rls.sql
│   │   ├── 0005_realtime_storage.sql
│   │   ├── 0006a_enum_additions.sql    # run FIRST and alone (ALTER TYPE ... ADD VALUE)
│   │   └── 0006b_common_person.sql     # emergency_cards, card_contacts, card_scans, place_plans, new columns
│   └── seed/
│       └── demo_accounts.sql
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                # FastAPI app, routers, CORS, limiter, lifespan (scheduler)
│   │   ├── config.py              # Settings (pydantic-settings) + constants
│   │   ├── deps.py                # get_current_user, require_role, supabase client
│   │   ├── models/
│   │   │   ├── enums.py           # Python Enums mirroring DB enums EXACTLY
│   │   │   ├── ai.py              # IncidentExtraction, VerificationDecision, PlannedAssignment, TriagePlan, DispatchPlan, PrepSummary, AfterActionReport
│   │   │   └── api.py             # request/response models for every endpoint
│   │   ├── routers/
│   │   │   ├── reports.py         # POST /reports, GET status, POST answer
│   │   │   ├── public.py          # GET /config, GET /public/alerts, GET /first-aid
│   │   │   ├── ack.py             # GET/POST /ack/{token}
│   │   │   ├── incidents.py       # verify/dismiss/close, signed media URLs
│   │   │   ├── alerts.py          # dashboard ack
│   │   │   ├── hospitals.py       # capacity, arrivals, on-call staff
│   │   │   ├── community.py       # join/register, telegram link codes
│   │   │   ├── family.py          # family finder search
│   │   │   ├── cards.py           # Emergency Card (F-36): draft, create, list, delete, qr, public view + alert
│   │   │   ├── places.py          # Place Plan (F-37): draft, create, list, delete, public view + alert
│   │   │   ├── coach.py           # POST /reports/{id}/coach (F-39) + GET /tts/ui
│   │   │   ├── push.py            # web push subscribe/unsubscribe
│   │   │   ├── analytics.py       # KPIs, heatmap
│   │   │   ├── webhooks_twilio.py # sms, voice (missed call), gather, status callbacks, whatsapp (Tier L)
│   │   │   ├── webhooks_telegram.py
│   │   │   └── health.py
│   │   ├── agents/                # the nine agents (docs/07_AI_AGENTS.md)
│   │   │   ├── models.py          # build_model('provider:model_id') for Gemini/Groq
│   │   │   ├── runner.py          # run_agent(): primary → fallback model → None (autopilot)
│   │   │   ├── hooks.py           # ActivityHooks(RunHooks) → agent_activity
│   │   │   ├── context.py         # AgentCtx dataclass
│   │   │   ├── orchestrator.py    # deterministic order: intake → verification → triage → dispatch → prep
│   │   │   ├── intake.py          # Intake Agent factory + tools
│   │   │   ├── verification.py    # Verification Agent + tools + guardrail
│   │   │   ├── triage.py          # Triage Agent + tools + plan validation
│   │   │   ├── dispatch.py        # Dispatch Agent + tools
│   │   │   ├── hospital_prep.py   # Hospital Prep Agent + tools
│   │   │   ├── debrief.py         # Debrief Agent + tools
│   │   │   ├── landmark.py        # Landmark Agent (F-38), runs beside Intake
│   │   │   ├── voice_coach.py     # Voice Coach Agent (F-39)
│   │   │   └── preparedness.py    # Preparedness Agent (F-40)
│   │   ├── services/
│   │   │   ├── activity.py        # agent_activity writer (used by hooks + orchestrator)
│   │   │   ├── transcribe.py      # Groq Whisper
│   │   │   ├── rules_classifier.py # Intake autopilot
│   │   │   ├── merge.py           # candidate search, same-event, recompute
│   │   │   ├── confidence.py      # formula from PRD F-06
│   │   │   ├── needs.py           # rules from PRD F-07 + severity floors
│   │   │   ├── matching.py        # hospital matching + casualty spreading
│   │   │   ├── routing_osrm.py    # table + route calls, haversine fallback, cache
│   │   │   ├── dispatch.py        # decides alert targets (idempotent)
│   │   │   ├── messages.py        # all message templates (EN/UR)
│   │   │   ├── notify_telegram.py
│   │   │   ├── notify_twilio.py   # sms + voice calls
│   │   │   ├── notify_email.py
│   │   │   ├── notify_push.py
│   │   │   ├── tts.py             # gTTS → storage URL (cached)
│   │   │   ├── ack_tokens.py      # itsdangerous sign/verify + single-use
│   │   │   ├── crypto.py          # Fernet encrypt/decrypt, HMAC phone hash, E.164
│   │   │   ├── geocode.py         # Nominatim via geopy (bounded viewbox)
│   │   │   ├── media.py           # upload validation, Pillow re-encode, storage
│   │   │   ├── first_aid.py       # select cards from first_aid.json
│   │   │   ├── community.py       # donor/volunteer selection
│   │   │   ├── doctors.py         # on-call selection + call-in
│   │   │   ├── public_alerts.py   # radius push
│   │   │   ├── after_action.py    # template after-action report (Debrief autopilot)
│   │   │   ├── country.py         # country_profiles.json + detect(lat, lng) → profile (F-35)
│   │   │   ├── osm_discovery.py   # Overpass live discovery of hospitals/stations + tile cache (F-35)
│   │   │   ├── labels.py          # type/severity/injury/specialty labels en/es/ur
│   │   │   ├── landmarks.py       # Overpass landmark query + selection + compass (F-38)
│   │   │   ├── cards.py           # card create/validate, token, public view, scan log (F-36)
│   │   │   ├── places.py          # place snapshot of nearest hospitals (F-37)
│   │   │   ├── redact.py          # phone-number placeholders for agent input (F-40)
│   │   │   ├── coach.py           # intent keywords, card/step selection, CoachTurn validation (F-39)
│   │   │   ├── events.py          # incident_events writer
│   │   │   └── audit.py           # audit_log writer
│   │   ├── jobs/
│   │   │   ├── scheduler.py       # APScheduler setup (AsyncIOScheduler)
│   │   │   ├── escalation.py      # every 10 s
│   │   │   ├── ambulance_sim.py   # every 2 s when SIMULATION_ENABLED
│   │   │   └── retention.py       # daily 03:00 in the country profile time zone
│   │   ├── data/
│   │   │   ├── first_aid.json
│   │   │   ├── injury_capability_map.json
│   │   │   ├── rules_keywords.json     # also the coach intent keywords (F-39 autopilot)
│   │   │   └── country_profiles.json
│   │   └── utils/
│   │       ├── short_code.py
│   │       └── time.py
│   ├── scripts/
│   │   ├── seed_osm.py            # Overpass → organizations
│   │   ├── seed_mock.py           # capabilities, beds, blood, staff, ambulances, members
│   │   ├── set_telegram_webhook.py
│   │   ├── gen_keys.py            # Fernet key, VAPID keys, secrets
│   │   ├── demo_burst.py          # sends the demo scenario reports
│   │   └── agent_smoke.py         # hour-1 check: every agent × primary/fallback model
│   └── tests/
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.ts
    ├── components.json            # shadcn config
    ├── .env.example
    ├── public/ (icons/, sounds/alert.mp3, sw handled by plugin)
    └── src/
        ├── main.tsx, App.tsx, router.tsx, index.css
        ├── i18n/ (index.ts, en.json, es.json, ur.json)
        ├── lib/ (supabase.ts, api.ts, severity.ts, offlineQueue.ts, geo.ts, recorder.ts, push.ts, schemas.ts, speak.ts)
        ├── hooks/ (useAnonSession.ts, useRole.ts, useRealtimeTable.ts, useGeolocation.ts)
        ├── components/ui/          # shadcn generated — do not edit by hand except styling
        ├── components/flow/        # LiveFlow.tsx, flowMap.ts (event → node ids), flow.svg
        ├── components/three/       # CommandScene.tsx, IncidentPillar.tsx, AlertArc.tsx, MarkerBox.tsx (lazy-loaded)
        ├── components/reporter/    # SosButton, HoldToSpeak, PhotoCapture, TextReportSheet, CallButtons, FirstAidCard, StatusTicks, FollowupCard, OfflineBanner, DangerBanner,
        │                           #   ListenButton, SafetyPromise, CoachSheet, CprMetronome, PictureButton, BloodGroupPicker,
        │                           #   CardForm, CardView, QrSticker, PlacePoster, RideModeGuard (Tier L)
        ├── components/dashboard/   # AgentActivityFeed, AgentLights, IncidentList, IncidentCard, IncidentMap, IncidentDetail, TargetsTable, AssignmentsTable, Timeline, ConfidenceBar, ReportsList
        └── pages/ (Home, Silent, ReportStatus, Family, Join, Ack, Login, Dashboard, IncidentPage, HospitalConsole, Analytics, Settings,
                    CardNew, CardPrint, CardScan, PlaceNew, PlacePrint, PlaceScan, Flow, Command, About)
```

## 5. Configuration (`backend/app/config.py`)

`Settings(BaseSettings)` reads env vars (full list in `11_ENV_SETUP.md`). Constants
(override-able by env, defaults below — keep names EXACT, they are referenced by docs):

```python
MERGE_RADIUS_M = 500
AUTO_MERGE_RADIUS_M = 150
MERGE_WINDOW_MIN = 15
CONF_VERIFIED = 0.60
CONF_UNVERIFIED = 0.30
ACK_TIMEOUT_S = 60
ESCALATION_TICK_S = 10
HOSPITAL_SEARCH_RADIUS_KM = 25
HOSPITAL_CANDIDATES = 15
MAX_HOSPITALS = 5
CRITICAL_SHARE = {"low": 0.0, "medium": 0.2, "high": 0.4, "critical": 0.6}
FALLBACK_SPEED_KMH = 25
OSRM_TIMEOUT_S = 3
AGENT_TIMEOUT_S = 15
DEBRIEF_TIMEOUT_S = 30
PROVIDER_COOLDOWN_S = 60
DISCOVERY_MIN_HOSPITALS = 3
DISCOVERY_TIMEOUT_S = 8
DISCOVERY_TILE_TTL_H = 24
COUNTRY_CACHE_TTL_D = 7
DONOR_RADIUS_KM = 10
DONOR_COOLDOWN_H = 24
DONOR_MAX = 30
BLOOD_LOW_UNITS = 5
VOLUNTEER_RADIUS_KM = 1.5
VOLUNTEER_COOLDOWN_H = 6
VOLUNTEER_MAX = 10
PUBLIC_ALERT_RADIUS_KM = 2
MAX_AUDIO_SECONDS = 60
# common-person features (F-36 … F-45)
LANDMARK_RADIUS_M = 300
LANDMARK_MAX = 3
LANDMARK_RELOCATE_M = 150
LANDMARK_TIMEOUT_S = 6
COACH_TIMEOUT_S = 6
PREPAREDNESS_TIMEOUT_S = 12
CARD_TOKEN_BYTES = 18                 # secrets.token_urlsafe(18) -> 24 chars
CARD_MAX_CONTACTS = 3
CARD_SCAN_RATE = "30/minute"          # per IP, public scan page
CARD_ALERT_RATE = "3/hour"            # per session, "Get help" from a card
COACH_RATE = "12/hour"                # per session
COACH_MAX_PER_REPORT = 10
RIDE_IMPACT_G = 4.0                   # Tier L (F-44)
RIDE_COUNTDOWN_S = 20                 # Tier L (F-44)
BLACKSPOT_GRID_M = 200                # Tier L (F-45)
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 1000
ACK_TOKEN_MAX_AGE_S = 6 * 3600
SIM_TICK_S = 2
SIM_SPEED_KMH = 40
RETENTION_DAYS_AFTER_CLOSE = 7
```

## 6. Core module contracts (function signatures — implement exactly)

```python
# agents/orchestrator.py
async def handle_report(report_id: UUID) -> None
    # transcribe → intake (agent|SOS default|rules) → needs rules → save → verify_step
    # → (status up / significant) triage → dispatch → (verified) hospital prep. Logs agent_activity.
    # Any exception: report status 'failed', activity 'error', and STILL attach a 'review' incident.
async def handle_close(incident_id: UUID) -> None          # Debrief Agent or template
async def handle_hospital_ack(target_id: UUID) -> None     # doctor call-in rule

# agents/runner.py
async def run_agent(agent_key: str, agent_factory, input, ctx: AgentCtx,
                    *, timeout_s: float = 15, max_turns: int = 4) -> object | None

# services/activity.py
async def log(ctx: AgentCtx | None, agent: str, kind: str, message: str, *, model: str | None = None,
              tool: str | None = None, latency_ms: int | None = None, data: dict | None = None) -> None

# services/transcribe.py
async def transcribe(audio_bytes: bytes, filename: str, mime: str) -> TranscriptResult  # text, language

# services/rules_classifier.py
def classify(text: str) -> IncidentExtraction                 # Intake autopilot

# services/merge.py
async def find_candidates(lat: float | None, lng: float | None, since: datetime) -> list[Candidate]
def fast_path(candidates: list[Candidate], extraction: IncidentExtraction) -> UUID | None
def autopilot_decision(candidates: list[Candidate], extraction: IncidentExtraction) -> UUID | None
async def attach_or_create(report: dict, extraction: IncidentExtraction, incident_id: UUID | None) -> tuple[UUID, bool]
async def recompute_incident(incident_id: UUID) -> IncidentChange  # old/new status, deltas

# services/confidence.py
def compute_confidence(max_ai_conf: float, unique_reporters: int, has_photo: bool,
                       any_phone_verified: bool, best_accuracy_m: float | None) -> float
def status_from_confidence(c: float, current: str, all_non_emergency: bool) -> str

# services/needs.py
def apply_rules(e: IncidentExtraction) -> IncidentExtraction   # needs + severity floors

# services/matching.py
async def hospital_options(incident: dict) -> HospitalOptions             # F-08 (used by Triage tool)
def validate_plan(plan: list[PlannedAssignment], opts: HospitalOptions) -> list[str]  # errors; [] = ok
def spread(opts: HospitalOptions) -> list[PlannedAssignment]              # F-09 autopilot
async def save_plan(incident_id: UUID, plan: list[PlannedAssignment], planned_by: str) -> None

# services/routing_osrm.py
async def etas_minutes(origin: tuple[float, float], dests: list[tuple[float, float]]) -> list[float]
async def route_geojson(a: tuple[float, float], b: tuple[float, float]) -> dict | None
# NOTE: OSRM uses lon,lat order in URLs. Our tuples are (lat, lng). Convert at the boundary.

# services/dispatch.py
async def required_targets(incident: dict) -> list[RequiredTarget]     # policy table PRD F-10
def default_order(targets: list[RequiredTarget]) -> list[str]          # Dispatch autopilot order
async def send_targets(incident_id: UUID, keys_in_order: list[str]) -> list[str]  # creates targets + deliveries
async def send_update(incident_id: UUID, change: IncidentChange) -> None
async def send_target(target_id: UUID, update: bool = False) -> None

# services/landmarks.py  (F-38)
async def nearby_landmarks(lat: float, lng: float) -> list[Landmark]        # Overpass, <= LANDMARK_MAX, with distance_m + compass
def validate_landmark_line(line: str, landmarks: list[Landmark]) -> bool    # names/distances must come from the list
def template_landmark_line(landmarks: list[Landmark], lang: str) -> str     # autopilot "Near {A}, {dir} of {B}"

# services/redact.py  (F-40)
def redact_phones(text: str, region: str) -> tuple[str, dict[str, str]]     # "<PHONE_1>" -> raw digits
def restore_phones(draft: dict, mapping: dict[str, str], region: str) -> dict  # E.164 via phonenumbers; invalid -> dropped

# services/cards.py  (F-36)
def new_token() -> str                                                      # secrets.token_urlsafe(CARD_TOKEN_BYTES)
async def create_card(user_id: UUID, data: CardCreate) -> CardOut           # encrypts phones, stores consent_at
async def public_view(token: str, ip_hash: str) -> PublicCard | None        # logs card_scans, increments scan_count
def card_line(card: dict, lang: str) -> str                                 # "Card: blood O+, allergy: ..." fixed template

# services/coach.py  (F-39)
def classify_intent(text: str, lang: str) -> CoachTurn                      # autopilot from rules_keywords.json
def step_text(card_key: str, step: int, lang: str) -> dict                  # {title, step, of, text, is_last} from first_aid.json
def validate_turn(turn: CoachTurn, valid_keys: set[str]) -> CoachTurn       # unknown card_key -> None

# services/ack_tokens.py
def make_token(target_id: UUID) -> str
def verify_token(token: str) -> UUID          # raises InvalidToken / ExpiredToken / UsedToken
async def acknowledge(target_id: UUID, via: str, actor: str | None) -> bool  # True if first ack
```

## 7. Async & background processing

- `POST /api/v1/reports` stores the report and media, then schedules
  `orchestrator.handle_report(report_id)` with FastAPI `BackgroundTasks`, returning `202`.
- APScheduler `AsyncIOScheduler(timezone=profile.timezone)` started in FastAPI `lifespan`:
  `escalation.tick` every `ESCALATION_TICK_S`, `ambulance_sim.tick` every `SIM_TICK_S`
  (only if `SIMULATION_ENABLED`), `retention.run` daily at 03:00.
  `max_instances=1, coalesce=True` for every job.
- All job state lives in the DB (`ack_due_at`, `escalation_level`, ambulance rows), so a
  restart loses nothing.
- Run ONE backend instance (no horizontal scaling) — the scheduler must not run twice.
- The Landmark step runs concurrently with Intake (`asyncio.gather`) as soon as a report
  has coordinates; its result is saved to the incident when it exists (never blocks alerts:
  alerts go out with the coordinates + area label and are *updated* with the landmark line
  if it arrives later than the first alert).
- Local run: backend and frontend are started by hand (`11_ENV_SETUP.md`); there is no
  Dockerfile, CI or hosting configuration in this build.

## 8. External API usage rules

| API | Call | Timeout | Retry | Fallback |
|---|---|---|---|---|
| Agents (Gemini/Groq via openai-agents) | `Runner.run(agent, input, context=ctx, hooks=ActivityHooks(...), max_turns=n)` in `asyncio.wait_for` | 15 s (Debrief 30 s) | none inside; runner tries fallback model | autopilot (deterministic) |
| Groq Whisper | `audio.transcriptions.create(model="whisper-large-v3-turbo", file=(name, bytes), temperature=0, response_format="verbose_json")` | 15 s | 1 retry | report saved, extraction from rules on empty text → `review` |
| OSRM | `GET {OSRM_BASE_URL}/table/v1/driving/{lng,lat;...}?sources=0&annotations=duration` | 3 s | none | haversine / 25 km/h |
| Telegram | `bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(...))` | 10 s | 2 retries | SMS still sent |
| Twilio | `client.messages.create(...)`, `client.calls.create(to, from_, twiml=..., status_callback=...)` | default | 1 retry | Telegram/email |
| Resend | `resend.Emails.send({...})` | default | 1 retry | — |
| Overpass | `httpx.AsyncClient.post(OVERPASS_URL, data={"data": query})` (query in `07_AI_AGENTS.md` §12.1) | 8 s | none | use existing orgs; tile marked `failed`, retried after 10 min |
| Nominatim | sync `geopy.geocoders.Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=5)` wrapped in `geopy.extra.rate_limiter.RateLimiter(min_delay_seconds=1)`, called via `asyncio.to_thread`; forward geocode uses `viewbox` (from profile bbox) + `bounded=True` | 5 s | none | no location → review |

Model names are **env vars** (`INTAKE_MODEL`, `INTAKE_FALLBACK_MODEL`, … one pair per agent,
format `provider:model_id`, see `07_AI_AGENTS.md` §1.1) because free-tier model lists
change. Pick current free models in Google AI Studio and the Groq console, run
`scripts/agent_smoke.py`, and record choices in `docs/DECISIONS.md`. Never hard-code.

Telegram calls from synchronous APScheduler contexts must use the same running event loop
(the scheduler is `AsyncIOScheduler`; all job functions are `async def`).

## 9. Error handling standard

- API errors return `{"error": {"code": "STRING_CODE", "message": "human text"}}` with the
  right HTTP status (codes listed in `06_API_SPEC.md` §1).
- External failures never bubble to the reporter; they are logged, audited, and the
  fallback is used.
- Logging: Python `logging`, JSON-ish format `level time module message key=value`;
  never log phone numbers, tokens, or full transcripts (log `report_id` instead).

## 10. Frontend data access rules

- **Reads for dashboard** (incidents, alert_targets, deliveries, hospital_assignments,
  ambulances, incident_events, organizations, hospital_details): `supabase-js` with the
  user's JWT, filtered by RLS; live updates via `supabase.channel(...).on('postgres_changes', ...)`.
- **All writes and all reporter actions** go through the FastAPI backend (`src/lib/api.ts`,
  `Authorization: Bearer <supabase access_token>`).
- Reporter status uses polling (`GET /api/v1/reports/{id}/status`), not Realtime.
- Validate every backend response with zod schemas in `src/lib/schemas.ts`.

## 11. Testing requirements

See `12_TESTING_AND_DEMO.md`. Minimum: unit tests for confidence, needs rules, matching,
ack tokens, rules classifier, message templates; integration test of `orchestrator.handle_report`
with mocked AI/Twilio/Telegram; one Playwright smoke test (SOS → status page shows code).
