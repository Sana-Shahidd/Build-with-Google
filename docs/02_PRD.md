# 02 — Product Requirements Document (PRD): Golden Minute

Version 3.0 (3-hour build, common-person focus) · Owner: Sana · Status: Approved for build
Feature IDs (`F-xx`) are referenced by the build plan, API spec and tests. Never renumber.

---

## 1. Goal and success metrics

**Goal:** Cut the time between an incident happening and every relevant responder being
alerted, acknowledged and prepared — and warn hospitals before patients arrive — in any
country and any language.

| Metric (measured from first report) | Demo target |
|---|---|
| Report received → incident created | ≤ 10 s (text), ≤ 15 s (voice/photo) |
| Incident verified → first alert delivered (Telegram) | ≤ 10 s (includes Triage + Dispatch agents) |
| Unacknowledged target → escalation voice call placed | 60 s ± 10 s |
| Duplicate reports of one event merged into one incident | 100 % in demo scenario |
| Reporter sees live status ticks | ≤ 3 s after each ack |
| Every agent step visible in Agent Activity feed | ≤ 2 s after it happens |

## 2. Scope

All features F-01 … F-47 are in scope of the product. The **build tier** of each feature
(`01_CONTEXT.md` §8: 3H-A built in the 3 hours, 3H-B only if time remains, L later) only
defines build order; the per-feature "Tier A/B/C" headings below are the older 24-hour
grouping and are kept for reference. Tier D items are roadmap and must NOT be built.
**When time is short, build exactly what `10_BUILD_PLAN.md` lists.**

**Agent ↔ feature map**

| Agent (`07_AI_AGENTS.md`) | Features |
|---|---|
| 🧠 Intake | F-02, F-03, F-04, F-05, F-22 (selects cards), F-25 |
| 🔎 Verification | F-06 |
| 🏥 Triage | F-08, F-09 |
| 📣 Dispatch | F-07 (with rules), F-10, F-11, F-12, F-13, F-21, F-27, F-28 |
| 🩺 Hospital Prep | F-19, F-23, F-24 |
| 📝 Debrief | F-31 (after-action report) |
| 🧭 Landmark | F-38 |
| 🗣 Voice Coach | F-39 (uses cards from F-22) |
| 🪪 Preparedness | F-40 (serves F-36 and F-37) |
| Code only (no agent) | F-36 scan flow, F-37, F-41 family notice templates, F-42, F-43–F-45 |
| Orchestrator + feed | F-33 |
| Orchestrator (code) + Triage | F-35 (detection and discovery are code; Triage consumes the result) |

---

## 3. Feature requirements

"MUST" = required. Every agent-driven feature also has an **autopilot** (deterministic
fallback) that produces a valid result when the agent fails, times out, hits a rate limit,
or proposes something a guardrail rejects. The autopilot is the algorithm written in the
feature below; the agent may only produce results that pass the same validation.

### Tier A — Core

#### F-01 One-tap SOS with auto GPS
- **Story:** As a bystander, I press one big button and help is alerted without typing.
- **FR:**
  1. Home (`/`) shows one SOS button occupying ≥ 40 % of viewport height.
  2. Pressing SOS starts a **3-second cancel countdown** (big "Cancel"), then submits.
  3. Location via `navigator.geolocation.getCurrentPosition` with
     `{ enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }`.
  4. Permission denied / timeout → report still sent with `lat/lng = null`; user sees
     "Where are you? (landmark/area)".
  5. Payload: `input_type = "sos"`, `channel = "app"`, plus `accuracy_m`.
- **AC:** SOS creates a report and an incident (type `other`, severity `high`) within 10 s;
  reporter is taken to `/report/:id`.

#### F-02 Voice report (any language)
- **Story:** As a panicked reporter, I hold a button and speak in my own language.
- **FR:**
  1. Hold-to-record using `MediaRecorder` (mime: first supported of
     `audio/webm;codecs=opus`, `audio/mp4`, `audio/ogg`).
  2. Max 60 s (auto-stop), min 1 s (shorter discarded with message).
  3. Backend transcribes with Groq `whisper-large-v3-turbo`, auto language detect.
  4. Transcript stored in `reports.transcript` and shown on the status page.
- **AC:** Spanish clip "Hay disparos en el concierto, muchas personas heridas" → type
  `attack_shooting`, severity ≥ `high`, injuries include `gunshot`; Urdu clip
  "یہاں دھماکہ ہوا ہے بہت لوگ زخمی ہیں" → type `explosion`.

#### F-03 Photo report
- **FR:** `accept="image/*" capture="environment"`; frontend converts to JPEG via canvas
  if needed; ≤ 8 MB; backend re-encodes with Pillow (strips EXIF) and passes the image to
  the Intake Agent; optional caption text alongside.
- **AC:** Photo of a car crash → type `road_accident`; stored photo has no EXIF.

#### F-04 Text report
- **FR:** Free text (≤ 1,000 chars), any language. Same flow as voice minus transcription.

#### F-05 Intake Agent: structured incident data
- **Story:** As a responder, I get a clean structured summary instead of a messy message.
- **FR:**
  1. The Intake Agent outputs `IncidentExtraction` (schema in `07_AI_AGENTS.md` §4):
     `is_emergency, incident_type, severity, est_casualties_min, est_casualties_max,
     injury_types[], needs[], ongoing_danger, location_hint, summary_en, summary_local,
     language_detected, confidence, missing_info[], followup_question, rationale`.
  2. Model chain: `INTAKE_MODEL` → `INTAKE_FALLBACK_MODEL` → rules classifier (autopilot).
     A report MUST never fail to produce an extraction.
  3. Bare SOS skips the agent (fixed SOS extraction, `07_AI_AGENTS.md` §5).
  4. Severity floors (code, after the agent): `est_casualties_max ≥ 5` → ≥ `high`;
     `≥ 15` → `critical`; type in (`attack_shooting`, `explosion`, `building_collapse`) → ≥ `high`.
- **AC:** All golden test reports in `12_TESTING_AND_DEMO.md` produce the expected type
  and severity within ±1 level.

#### F-06 Verification Agent: merging + confidence
- **Story:** As a dispatcher, 30 reports of one shooting appear as ONE incident.
- **FR:**
  1. Candidates: incidents with status in (`review`, `unverified`, `verified`), within
     `MERGE_RADIUS_M = 500` m and created within `MERGE_WINDOW_MIN = 15` min
     (`incidents_near_for_merge`, max 3).
  2. **Rule fast-path (no LLM):** exactly one candidate within `AUTO_MERGE_RADIUS_M = 150` m
     AND same `incident_type` (or either is `other`) → merge. Logged as ⚙ rule.
  3. Otherwise the Verification Agent receives the new extraction + candidates and returns
     `VerificationDecision {action: "merge"|"new", incident_id, confidence, rationale}`.
     Guardrail: `incident_id` must be one of the candidate ids; `merge` requires
     `confidence ≥ 0.6`; else treated as `new`.
  4. No candidates / `new` → create incident with `short_code = "GM-" + 4 chars [A-Z2-9]`.
  5. No location: Verification Agent compares only against incidents of the last 15 min
     whose `location_label` it is given; else new incident in `review`.
  6. On merge recompute (code): `severity = max`, casualties = max of mins / max of maxes,
     `injury_types`, `needs` = union, `ongoing_danger = any`, `report_count++`,
     `unique_reporters` = distinct (`reporter_id` or `phone_hash`), location = report with
     smallest `accuracy_m`.
  7. **Confidence (code, never the LLM)**, clamp 0–1:
     ```
     c = 0.40 * max(ai_confidence of merged reports)
       + 0.25 * min(1, (unique_reporters - 1) / 3)
       + 0.15 * (1 if any report has a photo else 0)
       + 0.10 * (1 if any reporter phone verified else 0)
       + 0.10 * (1 if best accuracy_m <= 100 else 0)
     ```
  8. Status: `c ≥ 0.60` → `verified`; `0.30 ≤ c < 0.60` → `unverified`; `< 0.30` → `review`.
     Only non-emergency reports → `review`. Automatic moves only go up. Dispatcher can
     verify/dismiss (F-14).
- **AC:** 5 reports within 200 m in 3 min (EN, ES, UR) → 1 incident, `report_count = 5`,
  status `verified`.

#### F-07 Needs rules
- **FR:** `needs[]` ⊆ {`ambulance`, `police`, `fire`, `rescue`} from the Intake Agent, then
  code adds: any injuries or casualties > 0 → `ambulance`; type in (`attack_shooting`,
  `explosion`, `riot_crowd`) → `police`; `fire`/`explosion` → `fire`;
  `building_collapse`/`flood` → `rescue`. EMS/rescue stations handle `ambulance` + `rescue`.

#### F-08 Triage Agent: hospital options
- **FR:**
  1. Injuries → required capabilities via `data/injury_capability_map.json`.
  2. Candidates: `organizations.type = 'hospital'` within `HOSPITAL_SEARCH_RADIUS_KM = 25`,
     nearest 15 (`nearest_orgs`), excluding `accepting_patients = false`.
  3. ETAs: one OSRM Table call; on failure (3 s) straight-line km / 25 km/h.
  4. "Fits" = hospital capabilities ⊇ required capabilities.
  5. Tool `get_hospital_options` returns this list (id, name, capabilities, free ER beds,
     ICU, ETA, fits) to the Triage Agent.

#### F-09 Triage Agent: casualty spreading
- **FR:**
  1. The Triage Agent calls `propose_assignment_plan(assignments, rationale)`.
  2. **Guardrail validation** (code): every hospital id ∈ options; sum of
     `casualties` == `total`; sum of `critical` == `critical_total`; critical patients only
     to fitting hospitals unless none fit; no hospital over free ER beds unless all fitting
     capacity is used (then `over_capacity = true`); 1 ≤ hospitals ≤ `MAX_HOSPITALS = 5`.
     Invalid → tool returns the errors; agent may retry once; then autopilot.
  3. **Autopilot algorithm** (`services/matching.py::spread`):
     ```
     total = est_casualties_max (min 1 if 'ambulance' in needs)
     critical_total = ceil(total * CRITICAL_SHARE[severity])  # low 0, medium .2, high .4, critical .6
     minor_total = total - critical_total
     fit = fitting hospitals by eta asc;  general = all candidates by eta asc
     for h in fit: give min(critical_left, h.free) critical
     leftover critical → nearest fit hospitals ignoring capacity (over_capacity)
     for h in general (skip full): give min(minor_left, free left) minor
     leftover minor → nearest general hospital (over_capacity)
     keep ≤ MAX_HOSPITALS; ensure ≥ 1
     ```
  4. Saved to `hospital_assignments` (casualties, critical, eta, reason, `planned_by` =
     `agent`|`autopilot`).
- **AC:** 12 casualties, nearest hospital 4 free beds → ≥ 3 hospitals, none over free beds
  unless flagged; burns patients never sent to a non-burns hospital when a burns
  hospital is within 25 km.

#### F-10 Dispatch Agent: multi-channel alerts
- **FR:**
  1. Tool `get_required_targets` (code policy) returns the **mandatory** target list:
     | Incident status | Required targets |
     |---|---|
     | `unverified` | nearest police (if `police`), nearest EMS/rescue (if `ambulance`/`rescue`), nearest fire (if `fire`), top-1 assigned hospital as STANDBY, dispatchers |
     | `verified` | all above + every assigned hospital (full brief) + public push (F-21 types) |
  2. The Dispatch Agent decides the **send order** (e.g. EMS first for many casualties,
     police first for active shooter) and calls `send_alerts(target_keys_in_order, rationale)`.
     Guardrail: keys must be a subset of the required list; any required key the agent
     omits is appended automatically (nothing required is ever skipped).
  3. Targets are created idempotently (unique recipient index) → deliveries per channel:
     org → Telegram (if chat linked) + SMS (if phone) + email (if email) + dashboard;
     public → web push.
  4. Message content = fixed templates (`07_AI_AGENTS.md` §11). The agent cannot write
     message text.
  5. Silent incidents add "⚠ SILENT REPORT – DO NOT CALL REPORTER".
  6. `incidents.first_alert_at` set at the first successful delivery.
  7. **No-contact orgs** (discovered live from OpenStreetMap, F-35, so no Telegram/SMS/email
     on file): the target is still created with a `dashboard` delivery, and the dispatcher
     target receives "Call manually: {org name} {public_phone or 'no phone listed'}". The
     reporter's status shows that service as "alerted via control room".
- **AC:** Verified demo incident sends Telegram messages to hospital/police/EMS/fire demo
  chats within 10 s of verification, each with "✅ Acknowledge".

#### F-11 Hospital pre-arrival brief
- **FR:** Deterministic template: type, severity, patients assigned (critical/minor),
  injuries, first ambulance ETA, ongoing danger, short code, doctors being called.
  STANDBY version (unverified): "UNVERIFIED – prepare, do not activate mass-casualty plan yet".

#### F-12 Incident updates
- **FR:** When a merge raises `est_casualties_max` ≥ 30 %, adds a need, raises severity,
  or verification happens: Triage re-plans only the extra casualties; Dispatch sends
  "UPDATE" deliveries to existing targets (no new ack) and normal alerts to new targets;
  `incident_events` row written.

#### F-13 Acknowledge + 60-second escalation
- **FR:**
  1. Ack methods: Telegram button (`callback_data = "ack:<target_id>"`), signed link in
     SMS/email (`{FRONTEND_BASE_URL}/ack/<token>` → page → POST), dashboard button, voice
     keypad "press 1".
  2. First ack on any channel wins; later acks no-op.
  3. Escalation job (code, logged in the feed as 📣 Dispatch Agent ⚙) every 10 s:
     - Level 0 → 1: `now ≥ ack_due_at` (created + 60 s) → voice call to primary phone in
       the org's `lang`, "press 1 to acknowledge"; `ack_due_at += 60 s`.
     - Level 1 → 2: call + Telegram to backup contact AND notify dispatcher.
     - Level 2 timeout → `no_response` (red on dashboard).
  4. Donors, volunteers, public never escalate.
- **AC:** Leaving the police alert unacked for 60 s triggers a Twilio call to the demo
  police phone; pressing 1 acknowledges.

#### F-14 Responder dashboard (live map)
- **FR:** `/dashboard` (auth): left incident list (severity then time); center Leaflet map
  (incident markers by severity, hospitals with free beds, stations, moving ambulances,
  500 m merge circle on selection); **right Agent Activity feed (F-33)**.
  Incident detail Sheet: summary EN + local language, reports (transcript, photo via signed
  URL), confidence bar with breakdown, alert targets with status chips, hospital
  assignments (with `planned_by`), timeline, buttons Verify / Dismiss (dispatcher) / Close.
  Live via Supabase Realtime.
  Role views: dispatcher/admin see all; org roles see only incidents where their org is a
  target (RLS).

#### F-15 Reporter live status
- **FR:** `/report/:id` polls `GET /api/v1/reports/{id}/status` every 3 s; shows short code,
  per-service ticks (Hospital / Ambulance / Police / Fire: ⏳ alerted → ✅ acknowledged),
  transcript, first-aid cards (F-22), follow-up question (F-25), emergency call buttons
  from the country profile. Silent mode: see F-20.

#### F-16 Audit log
- **FR:** Every state change writes `audit_log` via `services/audit.py::log()`.

#### F-17 Security controls
- **FR:** All controls in `08_SECURITY.md`.

#### F-33 Agent Activity feed + orchestrator
- **Story:** As a judge/dispatcher, I watch the agents think and act in real time.
- **FR:**
  1. `agents/orchestrator.py` runs agents in a fixed order per report:
     Intake → Verification → (if status changed or significant update) Triage → Dispatch →
     (if verified) Hospital Prep. Debrief runs when an incident closes.
  2. Every agent start, tool call, tool result summary, decision, guardrail block,
     fallback and error is written to `agent_activity` (schema in `05_DATABASE_SCHEMA.md`)
     via the SDK `RunHooks` subclass `ActivityHooks` plus explicit orchestrator logs.
  3. Rows contain a short human-readable `message` (≤ 200 chars, English) — e.g.
     "Triage Agent: 2 burns patients → Memorial Hermann (burns unit, 9 min)". Never raw
     prompts, phone numbers, or chain-of-thought; the agent's `rationale` field is the only
     reasoning shown.
  4. Dashboard right panel lists rows newest-first via Realtime: agent emoji + name, kind
     icon (🧠 thinking/decision, 🔧 tool, 🛡 guardrail, ⚙ autopilot/rule, ⚠ error), time,
     message, and model name chip. Filter by selected incident; "All" by default.
  5. A header strip shows one "light" per agent (nine): idle (gray) / working (pulsing blue) /
     done (green) / fallback (amber) for the selected incident.
- **AC:** During the demo burst, the feed shows all six core agents (Debrief after close), plus Landmark and Voice Coach when used, with
  ≥ 1 entry each, in order, within 2 s of each step.

#### F-34 Country profiles + multilingual
- **FR:**
  1. `data/country_profiles.json` (content in `07_AI_AGENTS.md` §12). The profile is
     **detected from location** (F-35); `COUNTRY_PROFILE` (default `US`) is only the
     fallback when no location is known. `GET /api/v1/config` returns the public part.
  2. Frontend: emergency call buttons, phone default region, languages offered, time zone
     for display and distance units come from config.
  3. UI languages: `en`, `es`, `ur` (RTL). Reports in any language. Summaries:
     `summary_en` always + `summary_local` in the report's language.
  4. Voice calls in recipient `lang`: `en`/`es` via TwiML `<Say>` with a matching
     `language` attribute; `ur` via gTTS MP3 + `<Play>`.
- **AC:** With no location, `COUNTRY_PROFILE=PK` shows Rescue 1122 / Police 15 / Edhi 115 /
  Fire 16 and Urdu first, without code changes.

#### F-35 Location-aware emergency numbers + live hospital discovery
- **Story:** As a reporter anywhere in the world, I see the right emergency number and the
  hospitals nearest to me, without anyone configuring my city.
- **FR:**
  1. **Country detection.** `services/country.py::detect(lat, lng)` reverse-geocodes with
     Nominatim (`zoom=3`, reads `address.country_code`, upper-cased), cached per coordinates
     rounded to 1 decimal (~10 km) for 7 days in memory + `geo_country_cache`. Profile
     lookup: exact country in `country_profiles.json` → else `DEFAULT` (112).
     Lookup failure → fallback profile from `COUNTRY_PROFILE`.
  2. **Frontend.** On load, config comes from `GET /api/v1/config` (fallback profile,
     `detected=false`). As soon as a location is available (first interaction, or
     immediately if `navigator.permissions.query({name:'geolocation'})` is already
     `granted`), call `GET /api/v1/config?lat=&lng=` and swap: emergency buttons, default
     language (only if the user has not picked one), phone region, units, time zone.
     A small chip shows "📍 Lahore, PK · 1122". Emergency buttons are NEVER hidden while
     loading: the fallback profile's buttons show plus a `112` button until detection finishes.
  3. **Per-incident country.** Reports and incidents store `country_code`. Message
     templates, time formatting, phone parsing (`phonenumbers` region) and SMS reply text
     use the incident's profile, not the server default.
  4. **Live hospital discovery.** `services/osm_discovery.py::ensure_area(lat, lng)`:
     if fewer than 3 hospitals exist within `HOSPITAL_SEARCH_RADIUS_KM`, query Overpass
     (`around:25000` for `amenity=hospital`, `amenity=police`, `amenity=fire_station`,
     `emergency=ambulance_station`, max 60 elements, timeout 8 s) and insert missing ones
     into `organizations` with `source='osm_live'`, `is_mock=false`, `public_phone` from the
     OSM `phone`/`contact:phone` tag, and `hospital_details` with
     `capabilities={general}`, `capacity_known=false`. Each ~10 km tile (coords rounded to
     1 decimal) is fetched at most once per 24 h (`osm_discovery_cache`).
  5. **When it runs.** The orchestrator starts `ensure_area` as a background task the moment
     a report with coordinates arrives (in parallel with transcription + Intake) and awaits
     it (max 8 s) before Triage. `GET /api/v1/public/nearby` also triggers it.
  6. **Triage with unknown capacity.** Hospitals with `capacity_known=false` are treated as
     `general` with `er_beds_available` unknown: they receive minor patients after
     known-capacity hospitals are used, never critical patients if any fitting
     known-capacity hospital exists, and their assignment reason says "capacity unknown".
  7. **Reporter "Nearest hospitals" card.** `GET /api/v1/public/nearby?lat=&lng=` returns
     the 5 nearest hospitals (name, distance in profile units, `public_phone` if known,
     map link). Shown on Home (after location is known) and on the status page.
  8. **Demo city switch (dev only).** With `APP_ENV=dev`, the frontend accepts a location
     override from Settings → "Simulate location" (presets: Houston, Lahore, Karachi,
     London, Mexico City) stored in `sessionStorage`, used instead of GPS.
- **AC:** Simulating Lahore shows Rescue 1122 / Police 15 / Edhi 115 / Fire 16, Urdu
  default, and within 10 s a "Nearest hospitals" list from OpenStreetMap; simulating London
  shows the GB numbers; a location with no profile shows `112`. An incident reported in a
  live-discovered city still produces hospital assignments (marked "capacity unknown") and
  dashboard alerts with manual-call instructions.

### Tier B

#### F-18 SMS and missed-call triggers
- **SMS:** Twilio inbound webhook `POST /webhooks/twilio/sms` (signature verified) → text
  report (`channel='sms'`). Location: registered home location of the sender
  (`community_members` by `phone_hash`) → else geocode `location_hint` with Nominatim
  (bounded to demo city) → else none (`review`). Reply TwiML: "Golden Minute: report
  GM-XXXX received. Help is being alerted. If you can, also call {primary_emergency_number}."
- **Missed call:** `POST /webhooks/twilio/voice` → `<Reject reason="busy"/>` + SOS report
  (`channel='missed_call'`) at the caller's registered home location; unregistered →
  `review` + SMS asking for location.

#### F-19 Doctor call-in (Hospital Prep Agent)
- **FR:** Required specialties from `injury_capability_map.json`. Trigger: Hospital Prep
  Agent run on `verified` incidents with severity `critical`, AND (rule) whenever a
  hospital target acks a verified incident. Tool `call_doctors(hospital_id, specialties)`
  guardrail: hospital must be assigned; specialties ⊆ required; max 4 per hospital; picks
  on-duty `on_call_staff` with lowest `priority`. Deliveries: voice (press 1 if coming),
  email, Telegram. Unanswered doctor → next-priority doctor of same specialty.

#### F-20 Silent SOS
- **FR:** `/silent` + toggle. Black screen, no sound/vibration/dialogs; **hold 2 s** sends
  SOS with `silent = true`; status shows only tiny "Sent ✓ GM-XXXX". Every alert says
  "DO NOT CALL REPORTER"; reporter phone never shown.

#### F-22 First-aid cards
- **FR:** Only from `data/first_aid.json` (EN/ES/UR). Selection is code from the Intake
  Agent's `incident_type` + `injury_types` (max 3; "Stay safe" first for violent/fire/
  collapse/flood types). Disclaimer always shown.

#### F-23 Blood donor ping (Hospital Prep Agent)
- **FR:** Eligible when verified, `est_casualties_max ≥ 3`, and injuries include `gunshot`,
  `blast_shrapnel`, `bleeding` or `crush`. Tool `get_prep_options` returns eligibility,
  allowed groups (`O-`, `O+` + any group below `BLOOD_LOW_UNITS = 5` units in any assigned
  hospital) and donor count. Tool `ping_donors(groups)` guardrail: groups ⊆ allowed;
  donors within `DONOR_RADIUS_KM = 10` (US profile shows "6 mi"), consented, active, not
  pinged in `DONOR_COOLDOWN_H = 24` h; max 30. Buttons "I can come" / "Can't".

#### F-24 Trained volunteers (Hospital Prep Agent)
- **FR:** Eligible when `ambulance` in needs and `ongoing_danger = false` (status
  unverified or verified). `ping_volunteers()` → members with skills `cpr`, `first_aid`,
  `nurse`, `doctor` within `VOLUNTEER_RADIUS_KM = 1.5`, max 10, cooldown 6 h. Message:
  "Only go if it is safe." On unverified incidents the orchestrator calls this as ⚙ rule.

#### F-25 Follow-up question
- **FR:** If Intake returns `followup_question`, status page shows it with text box + mic;
  `POST /api/v1/reports/{id}/answer` → Intake re-runs on the combined text → incident
  updated. Max 1 per report.

#### F-26 Ambulance simulation
- **FR:** `SIMULATION_ENABLED=true` → 3 ambulances per EMS station. Verified incident with
  `ambulance` → assign `min(6, ceil(est_casualties_max / 2))` nearest available;
  `jobs/ambulance_sim.py` moves them along OSRM route geometry at 40 km/h-equivalent:
  `en_route_scene` → `at_scene` (30 s) → `en_route_hospital` (round-robin assigned hospitals)
  → `at_hospital` (30 s) → `available`. First ETA feeds the brief.

### Tier C

#### F-21 Public danger-zone alert
- **FR:** "Warn me about danger nearby" → push permission + coarse location (2 decimals)
  via `POST /api/v1/push/subscribe`. Verified incidents of type `attack_shooting`,
  `explosion`, `fire`, `riot_crowd`, `building_collapse`, `flood` → push to subscriptions
  within `PUBLIC_ALERT_RADIUS_KM = 2` in the subscriber's language; once per subscription
  per incident; in-app banner via `GET /api/v1/public/alerts`.

#### F-27 Email alerts
- **FR:** Resend email to every org target with `email` and every doctor. Subject
  `[GOLDEN MINUTE] {SEVERITY} {type} – {code} – {location}`; signed ack button.

#### F-28 Multilingual voice calls
- **FR:** See F-34 §4. Audio cached per (template, incident, lang) in `tts_cache`;
  gTTS failure → English `<Say>`.

#### F-29 Family finder
- **FR:** `/family`: phone OTP → name (≥ 3 chars) + optional incident code →
  `pg_trgm` similarity ≥ 0.4 on `patient_arrivals` (72 h) → max 3 results: hospital name,
  public phone, arrival date only. 5 searches/hour/phone; every search logged. Hospital
  staff add arrivals on `/dashboard/hospital`.

#### F-30 Hospital capacity console
- **FR:** `/dashboard/hospital`: ER beds, ICU, blood stock (8 groups), accepting toggle →
  `PATCH /api/v1/hospitals/{id}/capacity`. Triage uses latest values; non-accepting
  hospitals excluded.

#### F-31 Debrief Agent + analytics + heatmap
- **FR:** `/dashboard/analytics` (dispatcher/admin): KPI tiles (incidents 7 d, median
  report→first-alert s, median alert→ack s, escalations, ack rate, % agent vs autopilot
  decisions), bar chart ack time by org, line chart incidents/day, heatmap
  (`leaflet.heat`). Closing an incident runs the Debrief Agent → `incidents.after_action_md`
  (autopilot: template), viewable + printable.

#### F-32 Offline queueing
- **FR:** `vite-plugin-pwa` precaches the shell; offline/failed POST → report (with Blob)
  saved in IndexedDB via `idb-keyval` (`gm:pending:<client_report_id>`); flush on
  `online`, app load, every 15 s; idempotent `client_report_id`. UI: "Saved – will send
  when connected" + call buttons (`tel:` works without data).


### Tier N — Common-person features (F-36 … F-45)

These features make the system usable by a person who cannot read, type or speak English,
and move preparation to *before* the emergency. Build tier for each is in
`01_CONTEXT.md` §8. Each has an autopilot or works without an LLM.

#### F-36 Emergency Card with QR sticker (Tier 3H-A)
- **Story:** As a rider/rickshaw driver/parent, I register once, stick a QR on my helmet or
  wallet, and if I am hurt a stranger can get my family and my medical basics in seconds.
- **FR:**
  1. `/card/new`: owner gives name, blood group (8 big buttons), allergies (optional),
     up to 3 family contacts (name, relation, phone), language, preferred hospital
     (optional, picked from nearest hospitals), and ticks a consent box read aloud
     ("Anyone who scans this card will see these details"). Setup can be by voice: the
     **Preparedness Agent** (F-40) fills a draft; the owner confirms every field on screen
     (read aloud) before saving.
  2. Saved by `POST /api/v1/cards`: phones encrypted (`crypto.encrypt_phone`), `token`
     = 24 URL-safe random chars, `consent_at` stored.
  3. `/card/:id/print` shows a printable sticker sheet (QR via `segno`, name, "Scan if I am
     hurt / اگر میں زخمی ہوں تو اسکین کریں") in a size for helmets and wallets.
  4. Public scan page `/c/:token` (no login; QR opens it with the phone camera): shows name,
     blood group, allergies, contact first names, and big buttons **🚑 Get help** and
     **📞 Call family** (`tel:`; shown only if the owner ticked `show_phone`). It never
     shows anything else.
  5. **Get help** calls `POST /api/v1/public/card/{token}/alert` → creates an SOS report
     (`reports.card_id` set) with the scanner's GPS; the pipeline runs normally. Hospital
     alerts get a fixed-template line from code: "Card: blood O+, allergy: penicillin"
     (never sent to an LLM, `messages.py` `card_line`).
  6. The owner can deactivate or delete the card at any time (`DELETE /api/v1/cards/{id}`
     removes contacts); every scan is logged (`card_scans`).
- **AC:** Create a card by voice in Urdu → confirm → print page shows a QR. Scan it from
  a second phone → public page in Urdu. Press **Get help** → incident appears on the
  dashboard within 10 s with the card line in the hospital brief. Deleting the card makes
  the scan page return 404.

#### F-37 Place Plan (Tier 3H-B)
- **Story:** As a shopkeeper/school/mosque committee/factory owner, I prepare my place once
  so anyone there can get help with one scan.
- **FR:**
  1. `/place/new`: place name, type (home, shop, school, mosque, factory, office, other —
     with pictures), location (GPS button or pin on map), language. Preparedness Agent can
     prefill from a spoken description.
  2. `POST /api/v1/places` stores it and takes a **snapshot** of the 3 nearest hospitals
     (by distance + ETA from `matching.hospital_options`), the country's emergency
     numbers, and the landmark text (F-38).
  3. `/place/:id/print` = a one-page poster (Urdu/English) with big **"Press for help"** QR,
     nearest hospital names with distance/ETA, the emergency numbers, and the landmark
     line.
  4. Scanning opens `/p/:token`; **Press for help** creates an SOS report with the place's
     fixed location (`reports.place_id`) — no GPS needed indoors.
- **AC:** Create a shop in Lahore → poster lists 3 nearby hospitals; scan → incident with the
  shop's landmark line appears on the dashboard.

#### F-38 Landmark directions — 🧭 Landmark Agent (Tier 3H-A)
- **Story:** As an ambulance crew, I need directions like locals give them.
- **FR:**
  1. When an incident is created (and when its location moves > 150 m), code
     (`services/landmarks.py`) queries OpenStreetMap Overpass for named landmarks within
     300 m (place of worship, fuel station, school, hospital, bank, mall, bridge/underpass,
     chowk/roundabout, bus stop). It selects up to 3 by distance with type priority and
     computes distance (m) and compass direction (N/NE/…) to each.
  2. The **Landmark Agent** receives that structured list and writes ONE line in the
     incident's local language, e.g. "کلمہ چوک سے 200 میٹر آگے، پٹرول پمپ کے سامنے". It may only
     use landmarks, distances and directions from the list.
  3. Autopilot (and validation): template "Near {A}, {dir} of {B}" in the language, using
     the same facts. The line is validated (every landmark name it mentions must be in the
     list; distances within ±50 m of the list) else the template is used.
  4. Saved to `incidents.landmark_text` (English) and `incidents.landmark_local`; added to
     every alert, the hospital brief, the ambulance simulation label and the reporter's
     status page ("Help is coming to: …").
- **AC:** Incident at the demo crash site produces an Urdu landmark line naming ≥ 1 real
  landmark from the Overpass result in ≤ 8 s; Overpass down → coordinates + area label only,
  alerts still sent.

#### F-39 Voice Coach — 🗣 Voice Coach Agent (Tier 3H-A)
- **Story:** As a scared bystander, I want a calm voice to tell me what to do, step by step,
  without reading.
- **FR:**
  1. On `/report/:id` a big **🔊 Talk me through it** button opens the coach sheet. It reads
     the selected first-aid card (F-22) aloud one step at a time (browser
     `speechSynthesis` in the reporter's language; gTTS fallback via `GET /api/v1/tts/ui`),
     each step with a picture/icon, a big **Next** button and **Repeat**.
  2. If the card is CPR, a Web Audio **metronome** beeps at 110 beats per minute.
  3. The person can hold the mic and say something ("he is not breathing", "blood is not
     stopping", "اب کیا کروں") → `POST /api/v1/reports/{id}/coach` → Whisper → the
     **Voice Coach Agent** returns a `CoachTurn` (intent, optional `card_key`, short calm
     acknowledgement). **Code** then reads the step text from `first_aid.json`; the agent
     never writes medical instructions.
  4. Rate limit 12 coach turns per session per hour, max 10 per report.
  5. Autopilot: keyword intent classifier (`rules_keywords.json`) maps words to card keys;
     unknown → "repeat current step" + "Call {number}" button.
  6. Always shows the disclaimer `firstaid.disclaimer` and the emergency number button.
- **AC:** Saying "khoon nahi ruk raha" (Roman Urdu: "the bleeding isn't stopping") returns
  the `bleeding` card steps in Urdu, spoken aloud; with the agent forced to fail, the same
  phrase still selects `bleeding` via keywords.

#### F-40 Preparedness Agent (Tier 3H-A for the card, 3H-B for places)
- **FR:** `POST /api/v1/cards/draft` and `POST /api/v1/places/draft` accept a voice note or
  text in any language. Code first replaces phone numbers with placeholders (`<PHONE_1>`…)
  using `phonenumbers`; the agent returns a typed draft (`CardDraft` / `PlaceDraft`);
  code restores the phone numbers, validates and normalises them (E.164 for the profile's
  `phone_region`), and returns the draft to the screen. Nothing is saved until the owner
  presses a big green **Save** after hearing the draft read back. If the agent fails the
  UI shows the guided form (one question per screen, each read aloud).
- **AC:** "میرا نام احمد ہے، خون کا گروپ او پازیٹو، بھائی کا نمبر 0300 1234567" → draft with
  name Ahmad, `O+`, contact "bhai" with a valid PK number, shown for confirmation.

#### F-41 Family notice (Tier 3H-B; templates, no agent)
- **FR:** When an incident is created from a card scan, `dispatch.notify_card_family` sends
  each contact who linked Telegram (`card_contacts.telegram_chat_id`) a fixed-template
  message in the card's language: "{name}'s Emergency Card was scanned at {landmark_local}.
  Help has been alerted. Hospital: {hospital}." Contacts without Telegram are listed on the
  dashboard incident detail as "call manually". (SMS: Tier L.) Linking works like
  F-23 Telegram codes (`telegram_link_codes` extended, see schema).
- **AC:** Linked contact receives the message within 10 s of the scan.

#### F-42 Bystander safety promise (Tier 3H-A, copy only)
- **FR:** The reporter home and the card-scan page show, in the reporter's language and
  read aloud, one calm line: "You are helping. You do not need to give your name or phone.
  You will not be questioned or blamed." The app never asks a reporter for name/phone.
  The line is in the i18n files (`safety.promise`). **Before a real launch, check the
  local legal position (Good Samaritan rules) and rewrite the line if it cannot be true.**
- **AC:** Line visible and spoken on `/` and `/c/:token`; no name/phone fields exist on any
  reporter screen.

#### F-43 WhatsApp voice-note channel (Tier L)
- **FR:** `POST /webhooks/twilio/whatsapp` (Twilio WhatsApp sandbox, signature-validated):
  a voice note or text becomes a report (`channel='whatsapp'`); location via WhatsApp
  location message or text; reply: short fixed-template text in the sender's language
  with the status ("Help alerted ✅"). Reply as a voice note is Tier L+ (gTTS audio via
  Twilio media).
- **AC:** Voice note "highway pe accident hua hai" → incident created; reply received.

#### F-44 Ride Mode crash detection (Tier L)
- **FR:** Opt-in toggle on the home screen for motorcyclists. While the page is in the
  foreground, `DeviceMotionEvent` acceleration > 4 g followed by < 0.5 g movement for
  5 s triggers a full-screen **"Are you OK?"** with a 20-second countdown, siren sound and
  one huge **I'm OK** button; no answer → SOS with GPS (`input_type='sos'`, `ride_mode`
  flag in `reports.extraction.source`). **Limitation to state honestly:** a web page cannot
  detect crashes in the background or with the screen off.
- **AC:** Simulated motion event (dev button) shows the countdown; cancelling sends nothing;
  letting it expire creates an SOS.

#### F-45 Black-spot warnings (Tier L)
- **FR:** `GET /api/v1/analytics/blackspots` clusters `road_accident` incidents (last 90
  days, 200 m grid) and returns the top 10 spots with counts; dashboard "Black spots" panel
  and map layer; suggestion text (code template): "Consider stationing an ambulance near X".
- **AC:** Seed 12 historic accidents → top spot appears with the right count.


#### F-46 Live Flow view (Tier 3H-A, build right after the dashboard)
- **Story:** As a judge or dispatcher, I watch the real system work: a report lights up the
  architecture, step by step, as it really happens.
- **FR:**
  1. Route `/flow` (dispatcher/admin; also a "Live flow" tab on the dashboard): the same
     diagram as `docs/architecture.html` (nine agents, guardrail layer, responders,
     database, acknowledgement loop) as a React component `LiveFlow.tsx` using the SVG
     from `frontend/src/assets/flow.svg` (copy the `<svg>` from `architecture.html`).
  2. It subscribes to Supabase Realtime on `agent_activity` (and `alert_targets`,
     `incident_events`). Each new row lights the matching nodes/edges for ~2 s (class
     `active`, then `done`) using the mapping table in `09_DESIGN.md` §3.15, and appends
     the row's message to a small live log beside the diagram.
  3. A `guardrail` row of kind `blocked` flashes the guardrail node red; a row with
     `fallback` flashes the agent's node dashed-amber ("autopilot").
  4. Controls: **Live** (follow new events), **Replay** (pick an incident, replays its
     `agent_activity` in original timing, speed ×1/×4), and the step explainer text from
     `architecture.html`'s steps for context.
  5. No new backend endpoint: reads existing tables through Realtime and
     `GET /incidents/{id}` (`agent_activity` list).
- **AC:** During `demo_burst` the diagram lights Intake → Landmark → Verification → Triage →
  Dispatch → responders → ack in the real order; a forced agent failure shows the amber
  autopilot flash; Replay of a closed incident reproduces the sequence.

#### F-47 3D command view (Tier 3H-B; only after T-13)
- **Story:** As a judge, I see the incident as a living 3D scene, not just a table.
- **FR:**
  1. `/command` (dispatcher/admin, and the public landing `/about` shows a decorative
     version): React Three Fiber scene — a dark tilted ground plane with the demo city
     grid, hospitals/police as small 3D markers, incidents as glowing pulsing pillars
     (height = casualties, colour = status), animated arcs from the incident to each
     alerted hospital (dashed line travelling along a curve; green when acknowledged).
  2. Positions come from `lat/lng` projected to metres around `demo_city.center` (simple
     equirectangular projection; no map tiles needed).
  3. Live: new incidents rise from the ground, alerts draw arcs, acks turn them green
     (Realtime on `incidents`, `alert_targets`, `hospital_assignments`).
  4. Camera: slow auto-orbit, drag to rotate (drei `OrbitControls`, polar angle limited),
     labels via drei `Html`; click an incident → opens the incident page.
  5. **Safety/performance:** lazy-loaded (`React.lazy`) so the reporter bundle is unaffected;
     `prefers-reduced-motion` → no auto-orbit; no WebGL or low-power device → falls back to
     the 2D Leaflet map automatically; `dpr` capped at 1.5; ≤ 60 incidents rendered.
  6. **The reporter app stays flat and light** (NFR-12): no 3D on any reporter screen.
- **AC:** Dashboard `/command` shows the scene at ≥ 30 fps on the demo laptop; the demo burst
  makes a pillar rise and arcs reach 3 hospitals; WebGL disabled → 2D map is shown.

---

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Reporter screens usable with one thumb; SOS in ≤ 1 tap from app open |
| NFR-2 | Reporter UI in English, Spanish, Urdu (RTL); toggle on every page; Urdu is the default for the `PK` profile |
| NFR-10 | A person who cannot read can complete SOS, a voice report, a card scan and the first-aid coach using only buttons with icons, speech and sound (`09_DESIGN.md` §1) |
| NFR-11 | No reporter screen asks for a name, phone number, account or any typing |
| NFR-12 | Reporter routes stay light and flat: ≤ 300 KB gzip JS, no WebGL/3D; 3D (F-47) is lazy-loaded and only on `/command` and `/about` |
| NFR-3 | Works on mid-range Android Chrome and iOS Safari (latest two versions) |
| NFR-4 | Report endpoint responds `202` in < 1 s; agents run async |
| NFR-5 | No single external failure stops alerts (model fallback, autopilot, OSRM fallback, Telegram + SMS redundancy) |
| NFR-6 | WCAG AA contrast; touch targets ≥ 48 px |
| NFR-7 | No secrets in frontend except Supabase anon key, VAPID public key, bot username |
| NFR-8 | Demo data only; no real patient data |
| NFR-9 | Each agent run has `max_turns ≤ 4` and a 15 s timeout; LLM calls per report ≤ 7, or ≤ 13 for the report that first verifies an incident (`07_AI_AGENTS.md` §14); Voice Coach turns are budgeted per session, not per report |

## 5. Out of scope (Tier D roadmap)

CCTV/gunshot-sensor detection agent, NG911/CAD integration, Rescue 1122 integration,
hospital EHR integration, native apps, paid zero-retention LLMs, real dispatch authority.

## 6. Pitch line

"Whether 911 is overloaded or doesn't exist, Golden Minute's nine AI agents make sure every
responder and hospital knows — and is ready — within 60 seconds, and you don't need to
read, type or know English: just press, speak or scan. Agents propose, guardrails decide,
humans stay in control."
