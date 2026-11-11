# 11 — Environment Setup: Golden Minute

## 1. Accounts (all free)

| Service | What to do | Gives you |
|---|---|---|
| Supabase | New project (region closest to Pakistan available, e.g. Singapore/Mumbai). Settings → API | `SUPABASE_URL`, anon key, service role key |
| Google AI Studio | Create API key; note current free Flash and Flash-Lite model ids | `GEMINI_API_KEY`, model ids |
| Groq console | Create API key; note a current instruction model that supports tool calling + JSON | `GROQ_API_KEY`, model id |
| Telegram *(optional, OFF by default: not usable in Pakistan)* | Only if you set `TELEGRAM_ENABLED=true`: @BotFather → `/newbot` | `TELEGRAM_BOT_TOKEN`, bot username |
| Cloudflare | Install `cloudflared` (no account needed for quick tunnels) | Public HTTPS URL for the phone demo |
| *Later (Tier L, not in the 3-hour build)* | Twilio trial (SMS, voice, WhatsApp sandbox, phone-auth OTP), Resend (email), VAPID keys (web push) | — |

**Skip in the 3-hour build:** Twilio, Resend, VAPID, Vercel, Render, GitHub.
The demo responders are two **web pages** (`/r/<token>`, printed by `python -m scripts.demo_links`):
one plays "hospital", one plays "police". Open them on two browser tabs or two phones.
No chat accounts are needed.

## 2. Backend env (`backend/.env`, mirror in `.env.example` with empty values)

```bash
# app
APP_ENV=dev                                  # dev | production
PUBLIC_BASE_URL=https://<tunnel>.trycloudflare.com   # the ONE tunnel URL (points at the Vite server :5173, which proxies /api + /webhooks) — used for QR codes, ack links, Telegram webhook
FRONTEND_BASE_URL=http://localhost:5173              # CORS (the tunnel URL is allowed via PUBLIC_BASE_URL)
COUNTRY_PROFILE=PK                           # PK (demo default) | US
SIMULATION_ENABLED=false                     # ambulance simulation is Tier 3H-B

# supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# AI keys
GEMINI_API_KEY=
GROQ_API_KEY=

# agent models (format provider:model_id) — see 07_AI_AGENTS.md §1.1
INTAKE_MODEL=gemini:<flash-id>
INTAKE_FALLBACK_MODEL=groq:<instruction-model-id>
VERIFICATION_MODEL=groq:<instruction-model-id>
VERIFICATION_FALLBACK_MODEL=gemini:<flash-lite-id>
TRIAGE_MODEL=groq:<instruction-model-id>
TRIAGE_FALLBACK_MODEL=gemini:<flash-id>
DISPATCH_MODEL=gemini:<flash-lite-id>
DISPATCH_FALLBACK_MODEL=groq:<instruction-model-id>
HOSPITAL_PREP_MODEL=groq:<instruction-model-id>
HOSPITAL_PREP_FALLBACK_MODEL=gemini:<flash-lite-id>
DEBRIEF_MODEL=gemini:<flash-id>
DEBRIEF_FALLBACK_MODEL=groq:<instruction-model-id>
LANDMARK_MODEL=gemini:<flash-lite-id>
LANDMARK_FALLBACK_MODEL=groq:<instruction-model-id>
COACH_MODEL=groq:<instruction-model-id>
COACH_FALLBACK_MODEL=gemini:<flash-lite-id>
PREPAREDNESS_MODEL=gemini:<flash-id>
PREPAREDNESS_FALLBACK_MODEL=groq:<instruction-model-id>

# telegram (OPTIONAL, off by default: the demo uses the web responder link)
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_WEBHOOK_SECRET=                     # 32+ random chars (gen_keys.py)

# --- Tier L (NOT used in the 3-hour build; leave empty) ---
# twilio (SMS, voice, WhatsApp sandbox)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_DAILY_MAX=100
# email
RESEND_API_KEY=
EMAIL_FROM=Golden Minute <onboarding@resend.dev>
# web push
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=

# secrets (gen_keys.py)
ACK_SECRET=
FIELD_ENCRYPTION_KEY=                        # Fernet key
PHONE_HASH_PEPPER=

# geo
OSRM_BASE_URL=https://router.project-osrm.org
OVERPASS_URL=https://overpass-api.de/api/interpreter
NOMINATIM_USER_AGENT=golden-minute-hackathon/1.0 (<your email>)

# demo mapping (seed_mock.py --demo-orgs) — optional Telegram chat ids; leave empty for the web responder demo
DEMO_HOSPITAL_CHAT=                          # linked via /start <code> (see run steps)
DEMO_POLICE_CHAT=
# Tier L only:
DEMO_HOSPITAL_PHONE=
DEMO_POLICE_PHONE=
DEMO_EMS_PHONE=
DEMO_FIRE_PHONE=
DEMO_DOCTOR_PHONE=
DEMO_EMAIL=
```

## 3. Frontend env (`frontend/.env`, public values only)

```bash
VITE_API_BASE_URL=                           # leave EMPTY: the browser calls the same origin; Vite proxies /api and /webhooks to :8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```
(VAPID public key, bot username and country profile come from `GET /api/v1/config`.)

## 4. Local run (this is the whole "deployment")

```bash
# terminal 1 — backend
cd backend
python3.13 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                            # the 3-hour subset (03_TRD.md §3)
python -m scripts.gen_keys            # prints secrets to paste into .env
python -m scripts.agent_smoke         # every agent model: ok?  (add --audio to test Urdu/Punjabi voice)
python -m scripts.seed_osm            # Lahore orgs from OpenStreetMap
python -m scripts.seed_mock --demo-orgs
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend (Vite proxies /api + /webhooks to :8000)
cd frontend && npm install && npm run dev                  # http://localhost:5173

# terminal 3 — tunnel for the phone (start it last; keep it running during the demo)
cloudflared tunnel --url http://localhost:5173
#   copy the https://….trycloudflare.com URL into PUBLIC_BASE_URL (backend/.env), restart the backend,
#   then print the responder links:  python -m scripts.demo_links   (uses PUBLIC_BASE_URL, else http://localhost:5173)
#   (optional, only with TELEGRAM_ENABLED=true:  python -m scripts.set_telegram_webhook)
```

Responder links: `python -m scripts.demo_links` prints one URL for the demo hospital and one for the demo
police station (nearest to the crash site). Open each in its own tab/phone. The links are secrets and
expire after 6 h; re-run the script after the tunnel URL changes. (Optional Telegram linking only
applies with `TELEGRAM_ENABLED=true`.)

Phone test checklist before you start building the UI: open the tunnel URL on the phone →
page loads → microphone permission prompt appears → location prompt appears. (If it does
not, the URL is not HTTPS or the Vite `allowedHosts` setting is missing.)

**Not part of this build:** Twilio webhooks, Resend, VAPID keys, Vercel, Render, GitHub
push, CI.

## 5. Demo accounts (create in Supabase Auth → Users, password of your choice)

| Email | Role |
|---|---|
| dispatcher@goldenminute.demo | dispatcher |
| hospital@goldenminute.demo | hospital_staff (nearest demo hospital) |
| police@goldenminute.demo | police |
| rescue@goldenminute.demo | rescue (EMS) |
| fire@goldenminute.demo | fire |
Then run `supabase/seed/demo_accounts.sql`.

## 6. Deployment — none in this build

There is no deployment in the 3-hour build. Everything runs on the laptop and the phone
reaches it through the Cloudflare quick tunnel. When the tunnel URL changes (new run of
`cloudflared`): update `PUBLIC_BASE_URL`, restart the backend, re-run
`python -m scripts.set_telegram_webhook`, and **re-print any QR stickers** (they encode the
old URL). Stop the tunnel when you are done (`08_SECURITY.md` S-21).

Later (not now): Vercel for the frontend, Render or a VPS for the backend, Twilio/Resend/VAPID,
CI. The old deployment notes were removed from this file on purpose so a coding tool does
not try to set them up.

## 7. `.gitignore` must include

```
.env
backend/.venv/
frontend/node_modules/
frontend/dist/
__pycache__/
*.pyc
```
