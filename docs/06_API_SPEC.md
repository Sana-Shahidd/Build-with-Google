# 06 — API Specification: Golden Minute Backend (FastAPI)

Base URL: `{BACKEND_BASE_URL}` — in the 3-hour build this is simply the Vite origin
(`http://localhost:5173`, or the Cloudflare tunnel URL on a phone), which proxies `/api` and
`/webhooks` to the backend on `localhost:8000`. No hosted backend.
All JSON endpoints are under `/api/v1`. Webhooks are under `/webhooks`.
FastAPI auto-docs at `/docs` (disabled when `APP_ENV=production`).

---

## 1. Conventions

**Auth header:** `Authorization: Bearer <supabase_access_token>`.
`deps.get_current_user` verifies the JWT by calling `supabase.auth.get_user(token)` (do not
hand-verify JWTs), then loads `profiles` row → `CurrentUser(id, role, org_id, is_anonymous, phone_verified)`.

Auth levels used below:
- `none` — no header required.
- `session` — any Supabase session, including anonymous reporters.
- `phone` — session whose user has a confirmed phone (`user.phone_confirmed_at` not null).
- `role:<roles>` — `profiles.role` in the list.

**Error body (all non-2xx):**
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "lat must be between -90 and 90" } }
```

| HTTP | code | When |
|---|---|---|
| 400 | `VALIDATION_ERROR` | bad field (FastAPI `RequestValidationError` handler converts to this shape) |
| 400 | `MEDIA_INVALID` | wrong mime, too large, audio too long |
| 401 | `UNAUTHENTICATED` | missing/invalid token |
| 403 | `FORBIDDEN` | role not allowed / not your org |
| 404 | `NOT_FOUND` | unknown id |
| 409 | `ALREADY_DONE` | e.g. follow-up already answered |
| 410 | `TOKEN_EXPIRED` / `TOKEN_USED` | ack token |
| 429 | `RATE_LIMITED` | slowapi limit hit (include `Retry-After`) |
| 500 | `INTERNAL` | unexpected (message generic, details only in logs) |

**IDs** are UUID strings. **Times** are ISO-8601 UTC strings. **Coordinates** are `lat`, `lng`
decimal degrees.

**CORS:** allow only `FRONTEND_BASE_URL` (and `http://localhost:5173` when `APP_ENV=dev`),
methods `GET, POST, PATCH, DELETE`, headers `Authorization, Content-Type`.

---

## 2. Reporter endpoints

### POST `/api/v1/reports` — create a report
Auth: `session`. Rate limit: 5/minute and 20/hour per user id; 30/minute per IP.
Content-Type: `multipart/form-data`.

| Field | Type | Required | Rules |
|---|---|---|---|
| `client_report_id` | uuid | yes | generated on client (`crypto.randomUUID()`); idempotency key |
| `input_type` | `sos\|voice\|photo\|text` | yes | |
| `lat`, `lng` | float | no | both or neither; ranges checked |
| `accuracy_m` | float | no | ≥ 0 |
| `location_hint` | string | no | ≤ 200 chars |
| `text` | string | `text` input: yes; else optional caption | ≤ 1000 chars |
| `audio` | file | `voice`: yes | mime in allowlist, ≤ 10 MB, ≤ 60 s |
| `photo` | file | `photo`: yes | `image/jpeg\|png\|webp`, ≤ 8 MB (frontend converts others by drawing to a canvas and exporting JPEG) |
| `silent` | bool | no | default false |
| `lang` | `en\|es\|ur` | no | UI language |
| `created_offline_at` | ISO time | no | when queued offline |

Response `202`:
```json
{
  "report_id": "uuid",
  "status": "received",
  "first_aid": [ /* FirstAidCard[] — generic 'stay_safe' + 'call_help' until processed */ ]
}
```
Idempotency: if `client_report_id` exists for the same user → return the existing report
with `200` (never create a duplicate).

### GET `/api/v1/reports/{report_id}/status`
Auth: `session` (must be the report's `reporter_id`, else 404).
Response `200`:
```json
{
  "report_id": "uuid",
  "report_status": "processed",
  "transcript": "یہاں دھماکہ ہوا ہے",
  "incident": {
    "short_code": "GM-7K3Q",
    "incident_type": "explosion",
    "severity": "critical",
    "status": "verified",
    "silent": false,
    "needs": ["ambulance","police","fire"]
  },
  "services": [
    { "service": "hospital",  "state": "acknowledged", "acknowledged_at": "…", "count_alerted": 3, "count_acknowledged": 2 },
    { "service": "ambulance", "state": "alerted",      "acknowledged_at": null, "count_alerted": 1, "count_acknowledged": 0 },
    { "service": "police",    "state": "acknowledged", "acknowledged_at": "…", "count_alerted": 1, "count_acknowledged": 1 },
    { "service": "fire",      "state": "alerted",      "acknowledged_at": null, "count_alerted": 1, "count_acknowledged": 0 }
  ],
  "followup_question": "Which road or landmark is closest to you?",
  "followup_answered": false,
  "first_aid": [ { "key": "stay_safe", "title": "…", "steps": ["…"], "icon": "shield" } ]
}
```
Rules: `services` contains only services in `needs` (hospital row shown when `ambulance`
in needs). `service` mapping: hospital ← `hospital`; ambulance ← `rescue` kind targets;
police ← `police`; fire ← `fire`. `state`: `pending` (no target yet) | `alerted` |
`acknowledged` (≥1 acknowledged). `first_aid` and text use the report's `lang`.
Never return any responder names, phones, or other reporters' data.

### POST `/api/v1/reports/{report_id}/answer` — follow-up answer
Auth: `session` (owner). Multipart: `text` (≤ 500) or `audio` (same rules).
`409 ALREADY_DONE` if answered. Response `202 {"report_id": "...", "status": "processing"}`.

### GET `/api/v1/config?lat=&lng=`
Auth: `none`. Rate 30/minute/IP. `lat`/`lng` optional. With coordinates: country detected
from location (F-35) → that country's profile (or `DEFAULT`). Without: the
`COUNTRY_PROFILE` fallback. Response = profile (`07_AI_AGENTS.md` §12) plus public keys
and detection fields (example below is the `US` profile; the default `COUNTRY_PROFILE` is `PK`):
```json
{ "country": "US", "detected": true, "location_label": "Downtown, Houston", "name": "United States", "phone_region": "US", "timezone": "America/Chicago",
  "units": "imperial", "languages": ["en","es","ur"], "default_lang": "en",
  "primary_emergency_number": "911",
  "emergency_numbers": [{"key":"emergency","label":{"en":"Call 911","es":"Llamar al 911","ur":"911 پر کال کریں"},"number":"911"}],
  "demo_city": {"name":"Houston, TX","center":[29.7604,-95.3698],"bbox":[29.52,-95.79,30.11,-95.01],"zoom":13},
  "vapid_public_key": "…", "telegram_bot_username": "…", "app_env": "dev" }
```
Frontend caches it with TanStack Query (`staleTime: Infinity`) and bundles a copy of the US
profile for offline use.

### GET `/api/v1/public/nearby?lat=&lng=` (F-35)
Auth: `none`. Rate 20/minute/IP. Awaits `osm_discovery.ensure_area` (max 8 s; on timeout
returns what exists with `"discovering": true`). Returns the 5 nearest hospitals:
```json
{ "units": "imperial", "discovering": false,
  "hospitals": [ { "name": "Example General Hospital", "distance": 2.4,
    "phone": "+17135550100", "map_url": "https://maps.google.com/?q=29.71,-95.40",
    "source": "seed" } ] }
```
`distance` in miles for `imperial`, km otherwise, 1 decimal. `phone` = `public_phone` or null.

### GET `/api/v1/public/alerts?lat=&lng=`
Auth: `none`. Rate 60/minute/IP. Returns verified incidents of public-alert types within
`PUBLIC_ALERT_RADIUS_KM`, created in last 6 h, not closed:
```json
{ "alerts": [ { "short_code": "GM-7K3Q", "incident_type": "explosion", "location_label": "Saddar", "created_at": "…" } ] }
```

### GET `/api/v1/first-aid?keys=bleeding,burns&lang=ur`
Auth: `none`. Returns `{"cards": FirstAidCard[]}` from `first_aid.json` (for offline caching
the frontend also bundles a copy).

---

## 3. Acknowledgement

### GET `/api/v1/ack/{token}` — preview (does NOT acknowledge)
Auth: `none`. Rate 20/minute/IP.
`200`: `{"recipient_label": "...", "incident": {"short_code","incident_type","severity","location_label","summary_en"}, "already_acknowledged": false}`
`410 TOKEN_EXPIRED | TOKEN_USED`, `404` invalid signature.

### POST `/api/v1/ack/{token}` — acknowledge
Auth: `none`. Rate 10/minute/IP. Marks token used, acknowledges target via
`ack_tokens.acknowledge(target_id, via='sms' or 'email' (from token payload), actor='link')`.
`200`: `{"acknowledged": true, "acknowledged_at": "…", "first": true}`.

### GET `/api/v1/responder/{token}` — web responder inbox (demo channel, replaces Telegram)
Auth: `none` (the token is the credential). Rate 60/minute/IP (the page polls every 3 s).
`token` = signed **organization inbox token** (`ack_tokens.make_inbox_token(org_id)`,
itsdangerous salt `inbox-v1`, expires after `INBOX_TOKEN_MAX_AGE_S` = 6 h, one org per link,
printed by `scripts/demo_links.py`). `404 NOT_FOUND` invalid, `410 TOKEN_EXPIRED`.
`200`:
```json
{ "org": {"id": "…", "name": "Rasheed Hospital", "type": "hospital", "lang": "ur"},
  "alerts": [ {
    "target_id": "…", "kind": "standby|hospital|police|rescue|fire", "state": "sent|delivered|acknowledged|…",
    "acknowledged_at": null, "created_at": "…",
    "ack_token": "<single-use per-alert token, null once acknowledged>",
    "incident": {"short_code": "GM-7K3Q", "incident_type": "road_accident", "severity": "high",
                 "status": "unverified", "location_label": "…", "map_url": "https://maps.google.com/?q=…"},
    "text": {"en": ["line", "…"], "es": ["…"], "ur": ["…"]}   // fixed templates (07 §11) rendered by code
  } ] }
```
Newest first, max 10 alerts, only THIS organization's targets. `text` lines come from
`messages.org_alert` / `messages.hospital_brief` (landmark and card lines included when
present); no phone numbers, chat ids or other organizations' data are ever returned. First
view moves targets `sent → delivered`. The page's ✅ button calls
`POST /api/v1/ack/{ack_token}` (below); the token's channel is `dashboard`, so
`acknowledged_via = 'dashboard'`. GET never acknowledges.

### POST `/api/v1/alerts/{target_id}/ack` — dashboard acknowledge
Auth: `role:dispatcher,admin,hospital_staff,police,rescue,fire`. Non-dispatchers may ack
only targets where `recipient_org_id = user.org_id` (else 403).
`200`: same shape as above.

---

## 4. Incidents (responders)

Reads happen through Supabase (RLS). Mutations:

### POST `/api/v1/incidents/{id}/verify`
Auth: `role:dispatcher,admin`. Sets status `verified`, `verified_at`, `verified_by`, runs
`dispatch_if_needed`. `200 {"status":"verified"}`. `409` if closed/dismissed.

### POST `/api/v1/incidents/{id}/dismiss`
Auth: `role:dispatcher,admin`. Body `{"reason": "string ≤ 300"}`. Sets `dismissed`; sends
"CANCELLED" update to all sent targets; stops escalation (sets `ack_due_at = null`).

### POST `/api/v1/incidents/{id}/close`
Auth: `role:dispatcher,admin,rescue,police`. Sets `closed`, stops escalation, schedules
after-action report generation (background). `200 {"status":"closed"}`.

### GET `/api/v1/incidents/{id}/media`
Auth: `role:*responder*` + `can_view_incident`. Returns signed URLs (10 min) for each
report's audio/photo: `{"items":[{"report_id","audio_url","photo_url"}]}`.

### GET `/api/v1/incidents/{id}/after-action`
Auth: `role:dispatcher,admin`. `{"markdown": "...", "generated_at": "..."}` or 404.

---

## 5. Hospitals

### PATCH `/api/v1/hospitals/{org_id}/capacity`
Auth: `role:hospital_staff` (own org) or `dispatcher,admin`.
Body (all optional, ints ≥ 0):
```json
{ "er_beds_available": 6, "icu_available": 1, "accepting_patients": true,
  "blood_stock": {"A+":10,"A-":3,"B+":9,"B-":2,"AB+":4,"AB-":1,"O+":12,"O-":2} }
```
Validation: `er_beds_available ≤ er_beds_total`; blood_stock keys exactly the 8 groups.
Any successful update also sets `capacity_known = true`.
`200` returns updated `hospital_details`.

### GET/POST `/api/v1/hospitals/{org_id}/on-call`
GET auth: hospital_staff (own) / dispatcher / admin → list without decrypted phones
(`phone_masked`). POST body:
`{"full_name","specialty","phone","email","lang","priority","on_duty"}` (phone parsed with
`phonenumbers`, region = profile `phone_region`, stored encrypted). PATCH `/api/v1/hospitals/{org_id}/on-call/{staff_id}`
same fields optional. DELETE same path.

### POST `/api/v1/hospitals/{org_id}/arrivals`
Auth: hospital_staff (own) / dispatcher. Body
`{"incident_short_code": "GM-7K3Q"|null, "full_name": "…"|null, "approx_age": 30|null,
"sex": "male|female|other|unknown", "wristband_code": "…"|null}`. Backend sets
`name_normalized = lower(trim(collapse_spaces(full_name)))`. `201` returns row.

---

## 6. Community, Telegram linking, push, family

### POST `/api/v1/community/join`
Auth: `phone`. Body:
```json
{ "display_name": "Ali", "is_donor": true, "blood_type": "O+", "skills": ["cpr"],
  "lat": 24.86, "lng": 67.01, "lang": "ur", "consent": true }
```
`consent` must be `true`. Location rounded to 3 decimals (~100 m) before storing. Phone
taken from the verified Supabase user (never from body). Upsert by `phone_hash`.
`200 {"member_id": "...", "telegram_link": "https://t.me/<BOT_USERNAME>?start=<code>"}`.

### DELETE `/api/v1/community/me` — leave (sets `active=false`, deletes phone & location)

### POST `/api/v1/telegram/link-code`
Auth: `role` ≠ reporter (responder links own chat) — body `{"target": "self"}`; or
dispatcher/admin linking an org/staff: `{"target":"org","org_id":"…"}` /
`{"target":"staff","staff_id":"…"}`. Code TTL 15 min.
`200 {"link": "https://t.me/<BOT_USERNAME>?start=<code>", "expires_at": "…"}`.

### POST `/api/v1/push/subscribe`
Auth: `session`. Body: `{"subscription": PushSubscriptionJSON, "lat": 24.86, "lng": 67.01, "lang": "ur"}`.
Location rounded to 2 decimals. Upsert by endpoint. `200 {"ok": true}`.
### DELETE `/api/v1/push/subscribe` body `{"endpoint": "..."}`.
### GET `/api/v1/push/vapid-public-key` → `{"key": VAPID_PUBLIC_KEY}` (auth none).

### POST `/api/v1/family/search`
Auth: `phone`. Rate 5/hour per user. Body `{"name": "≥3 chars ≤ 80", "incident_code": "GM-XXXX"|null}`.
Calls RPC `family_search(name, now()-72h, incident_id|null, profile.timezone)`; logs `family_queries`.
`200 {"results": [{"hospital_name","hospital_phone","arrived_date"}]}`.

---

## 6.1 Common-person endpoints (F-36 … F-45)

Auth `session` = any Supabase session including anonymous (the owner of a card/place is the
anonymous or logged-in user who created it; to keep a card across phones the owner can
sign in later — Tier L). Owner endpoints return 404 for another user's card/place.

### POST `/api/v1/cards/draft` — Preparedness Agent (F-40)
Auth: `session`. Rate 10/hour. Multipart: `audio` (≤ 60 s) or `text` (≤ 1000), `lang`
(`en|es|ur`). Flow: Whisper → `redact.redact_phones` → Preparedness Agent → restore +
validate phones. Response `200`:
```json
{ "source": "agent", "draft": { "full_name": "Ahmad", "blood_type": "O+", "allergies": null,
  "contacts": [ { "name": "Bhai", "relation": "brother", "phone": "+923001234567" } ], "lang": "ur" },
  "missing": ["allergies"], "transcript": "…" }
```
`source` = `agent` or `form` (agent failed → `draft` is empty and the UI shows the guided form).

### POST `/api/v1/cards` — create
Auth: `session`. Rate 5/hour. JSON `CardCreate`:
```json
{ "full_name": "Ahmad", "blood_type": "O+", "allergies": "penicillin",
  "contacts": [ { "name": "Bhai", "relation": "brother", "phone": "+923001234567" } ],
  "lang": "ur", "show_phone": true, "preferred_hospital_id": null, "consent": true }
```
Rules: `consent` must be `true`; 1–3 contacts; phones parsed with `phonenumbers` (region =
profile `phone_region`) and stored encrypted; names ≤ 80. Response `201`:
`{"card_id":"uuid","token":"…24 chars…","scan_url":"{PUBLIC_BASE_URL}/c/<token>","print_url":"/card/<id>/print"}`.

### GET `/api/v1/cards/me` → `{"cards":[{"card_id","full_name","active","scan_count","last_scanned_at","scan_url"}]}`
### GET `/api/v1/cards/{card_id}/qr.svg` — owner only. `image/svg+xml` from `segno` (error level Q).
### DELETE `/api/v1/cards/{card_id}` — owner only; hard-deletes card, contacts, scans. `204`.

### GET `/api/v1/public/card/{token}` — the page a stranger sees after scanning
Auth: `none`. Rate `CARD_SCAN_RATE` per IP. Increments `scan_count`, writes `card_scans`.
`404 NOT_FOUND` if unknown or `active=false`. Response `200` (`PublicCard`):
```json
{ "full_name": "Ahmad", "blood_type": "O+", "allergies": "penicillin", "lang": "ur",
  "contacts": [ { "name": "Bhai", "relation": "brother", "phone": "+923001234567" } ],
  "emergency_numbers": [ /* from the country profile */ ] }
```
`contacts[].phone` is present ONLY for contact #1 and ONLY when `show_phone=true`; otherwise
the key is omitted. Nothing else is ever returned.

### POST `/api/v1/public/card/{token}/alert` — "Get help"
Auth: `session` (anonymous is fine). Rate `CARD_ALERT_RATE` per session, 10/hour per IP.
JSON `{"client_report_id":"uuid","lat":31.50,"lng":74.33,"accuracy_m":20}` (lat/lng optional).
Creates a report exactly like `POST /reports` with `input_type="sos"`, `channel="app"`,
`card_id` set, then runs the normal pipeline. Response `202 {"report_id": "uuid"}`. A repeat
with the same `client_report_id` returns the existing report. Writes `card_scans.report_id`.

### POST `/api/v1/places/draft` — same shape as cards/draft, returns a `PlaceDraft`
`{"draft":{"name":"Ali General Store","place_type":"shop","lang":"ur"},"missing":["location"]}`.

### POST `/api/v1/places` — create (F-37)
Auth: `session`. JSON `PlaceCreate`:
`{"name":"…","place_type":"shop","lat":31.50,"lng":74.33,"lang":"ur","consent":true}`.
The backend computes `location_label`, landmark lines (F-38), and the `nearest` snapshot
(3 nearest hospitals via `matching.hospital_options`). `201`:
`{"place_id","token","scan_url":"{PUBLIC_BASE_URL}/p/<token>","print_url":"/place/<id>/print"}`.

### GET `/api/v1/places/me`, DELETE `/api/v1/places/{place_id}` (owner only), GET `/api/v1/places/{place_id}/qr.svg`

### GET `/api/v1/public/place/{token}` (auth none, 30/min/IP)
`{"name","place_type","location_label","landmark_local","nearest":[{"name","type","distance_m","eta_min","phone"}],"emergency_numbers":[…],"lang"}`
### POST `/api/v1/public/place/{token}/alert` (auth `session`, 3/hour per session)
JSON `{"client_report_id":"uuid"}` → report with the place's fixed location, `place_id` set. `202`.

### POST `/api/v1/reports/{report_id}/coach` — Voice Coach turn (F-39)
Auth: `session` (must own the report, else 404). Rate `COACH_RATE` per session; at most
`COACH_MAX_PER_REPORT` per report → `429 RATE_LIMITED`. Multipart: `audio` (≤ 20 s) or
`text` (≤ 300), `card_key` (current card, optional), `step` (int, optional), `lang`.
Response `200` (`CoachReply`):
```json
{ "intent": "switch_card", "card_key": "bleeding", "step": 0, "of": 4,
  "ack": "ٹھیک ہے، میں آپ کو بتاتا ہوں۔",
  "text": "زخم پر صاف کپڑا رکھ کر مضبوطی سے دبائیں۔", "icon": "droplet",
  "is_last": false, "source": "agent", "disclaimer_key": "firstaid.disclaimer" }
```
`text` always comes from `first_aid.json` (via `coach.step_text`), never from the agent;
`ack` is the agent's short calm phrase (≤ 120 chars, validated: no digits, no medicine/dose
words — see `07_AI_AGENTS.md` §6.8) or a fixed phrase from `labels.py` when `source="rules"`.
`intent` ∈ `next | repeat | previous | switch_card | call_help | done | unclear`.

### GET `/api/v1/tts/ui?key=<i18n or first-aid key>&lang=ur` — read-aloud fallback
Auth: `none`. Rate 60/min/IP. `key` must be on the whitelist (`ui.*` strings and
`firstaid.<card>.<n>`); returns `{"url": "<public mp3 URL>"}` from gTTS via `tts_cache`.
Unknown key → `404`. (Browser `speechSynthesis` is used first; this is only the fallback.)

### Tier L endpoints
- `POST /webhooks/twilio/whatsapp` (F-43): signature validated like S-05; creates a report
  with `channel='whatsapp'`; replies with a fixed-template status text.
- `GET /api/v1/analytics/blackspots?days=90` (F-45): auth `role:dispatcher,admin`; calls
  `rpc('blackspots')` → `{"spots":[{"lat","lng","count","suggestion"}]}`.

### Status response additions (`GET /reports/{id}/status`)
Add inside `incident`: `"landmark_local": "…"` (null until F-38 finishes) and
`"landmark_text": "…"`; add top-level `"coach_available": true` when `first_aid` is non-empty.

---

## 7. Analytics

### GET `/api/v1/analytics/summary?days=7`
Auth: `role:dispatcher,admin`.
```json
{ "incidents": 14, "median_secs_to_first_alert": 6.2, "median_secs_alert_to_ack": 41.0,
  "escalations": 3, "ack_rate": 0.92,
  "ack_by_org": [{"org_name":"…","median_secs":35.1,"count":4}],
  "per_day": [{"date":"2026-10-15","count":3}] }
```
### GET `/api/v1/analytics/heatmap?days=30` → `{"points": [[lat, lng, weight], ...]}` with
weight = 0.25/0.5/0.75/1.0 for low/medium/high/critical.

---

## 8. Webhooks

All webhook URLs are built from `PUBLIC_BASE_URL` (the public HTTPS URL of the backend).

### POST `/webhooks/twilio/sms` — inbound SMS (F-18)
Validate `X-Twilio-Signature` with `RequestValidator(TWILIO_AUTH_TOKEN).validate(url, form, signature)`
where `url = PUBLIC_BASE_URL + request.url.path`. Invalid → `403` empty.
Form fields used: `From`, `Body`, `MessageSid`. `client_report_id = uuid5(NAMESPACE_URL, MessageSid)`.
Response: TwiML `MessagingResponse` with the reply text (content-type `application/xml`).

### POST `/webhooks/twilio/voice` — inbound call = missed-call SOS (F-18)
Validate signature. Fields: `From`, `CallSid`. Creates SOS report (`channel='missed_call'`).
Response TwiML: `<Response><Reject reason="busy"/></Response>`.

### POST `/webhooks/twilio/gather?target_id=<uuid>&sig=<hmac>` — keypad on outbound calls
Validate Twilio signature AND `sig = HMAC_SHA256(ACK_SECRET, target_id)` (hex, first 32 chars).
`Digits == "1"` → `acknowledge(target_id, via='voice')` → TwiML `<Say>` "Thank you…" / Urdu
`<Play>`. Other digit/no input → repeat prompt once, then hang up.

### POST `/webhooks/twilio/status?delivery_id=<uuid>&sig=<hmac>` — SMS/call status callbacks
Maps `MessageStatus`/`CallStatus` (`delivered`/`completed` → delivered; `failed`/`undelivered`/
`busy`/`no-answer` → failed) into `deliveries.status`; if all deliveries of a target are
`delivered`, set target `delivered` (unless already acknowledged).

### POST `/webhooks/telegram`
Verify header `X-Telegram-Bot-Api-Secret-Token == TELEGRAM_WEBHOOK_SECRET` (constant-time
compare) else `403`. Parse with `telegram.Update.de_json(body, bot)` and process with
`Application.process_update`. Handlers:

| Update | Handler behaviour |
|---|---|
| `/start <code>` | look up `telegram_link_codes` (unused, not expired) → store `chat_id` on profile / member / staff / org (org: `telegram_chat_id`; if already set, store as `backup_telegram_chat_id` when code was created with `{"backup": true}`) → reply "Linked ✅ You will receive Golden Minute alerts here." |
| `/start` (no code) | reply with instructions (no data stored) |
| callback `ack:<target_id>` | check the target's recipient chat id == `update.effective_chat.id` (org/staff/profile) → `acknowledge(..., via='telegram')` → edit message to append "✅ Acknowledged by {name} at {HH:MM}" and remove button; else answer callback "Not authorized" |
| callback `resp:<incident_id>:<role>:<coming|cannot>` | must match a member whose `telegram_chat_id` == chat → upsert `community_responses` → answer "Thank you" |
| `/stop` | community member → `active=false`; responder → unlink chat |
| any other message | reply "This bot only sends alerts. In an emergency call {primary_emergency_number}." |

Return `200` quickly (process inside the request; it is fast).

### GET `/health` → `{"status":"ok","time":"…","scheduler":true}`

---

## 9. Dev/demo-only endpoints (`APP_ENV != production` AND role admin)

- `POST /api/v1/dev/simulate-reports` body `{"scenario":"highway_crash"}` — runs
  `scripts/demo_burst.py` scenario server-side (5 staggered reports).
- `POST /api/v1/dev/reset-demo` — closes all open incidents, resets ambulances to stations.

---

## 10. Frontend API client (`src/lib/api.ts`)

```ts
export async function api<T>(path: string, opts: { method?: string; body?: FormData | object; auth?: boolean } = {}, schema?: z.ZodType<T>): Promise<T>
// - prefixes VITE_API_BASE_URL + '/api/v1'
// - adds Authorization from supabase.auth.getSession()
// - JSON-encodes plain objects; passes FormData as-is (never set Content-Type for FormData)
// - throws ApiError(code, message, status) using the error body shape
// - validates with zod schema when provided
```
