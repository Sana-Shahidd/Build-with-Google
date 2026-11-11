# 09 — Design (UI/UX): Golden Minute

Use **shadcn/ui** components (generated with the `shadcn` CLI) + Tailwind CSS v4 +
`lucide-react` icons + `sonner` toasts. Do not hand-build components that shadcn provides
(Button, Card, Dialog, Sheet, Tabs, Badge, Input, Textarea, Label, Switch, Table, Tooltip,
Progress, Separator, Skeleton, Alert, DropdownMenu, Form).

---

## 1. Design principles

1. **Panic-proof:** a terrified person must succeed with one thumb, no reading.
2. **Big, few, obvious:** max 3 primary actions per reporter screen.
3. **Status over silence:** always show what is happening ("Hospital alerted ⏳").
4. **Calm authority for responders:** dark, dense, scannable dashboard; red only for
   critical things.
5. **Bilingual by default:** Urdu and English are equal; Urdu is RTL. For the `PK` profile
   (the demo default) Urdu is shown first.

**Common-person rules (apply to every reporter-side screen; F-36 … F-42, NFR-10/11):**
6. **Picture first.** Every button has a large lucide icon (or emoji) and a ≤ 3-word label;
   state is shown by icon + colour + sound, never by a sentence alone.
7. **Everything can be heard.** Every reporter screen has a round 🔊 `ListenButton` (64 px)
   and reads itself aloud on first open if the user has tapped anywhere once (browsers block
   autoplay). `lib/speak.ts`: `speak(text, lang)` uses `speechSynthesis` with the best voice
   for the language (`ur-PK`, `en-US`, `es-US`); if no voice exists it calls
   `GET /api/v1/tts/ui` and plays the mp3.
8. **Nothing to type.** Anything typed can also be spoken (mic icon inside inputs) or chosen
   by tiles/keypad. No account, no login, no name asked from a reporter.
9. **One question per screen** in wizards; max 3 primary actions per screen; huge targets
   (≥ 64 px, primary ≥ 96 px).
10. **Plain words, short lines.** No sentence over ~8 words on a reporter screen; no jargon
    ("SOS" is kept because it is recognised); numbers written as numbers with icons.
11. **Calm, not scary.** Red only for SOS/Get help; reassurance line (`safety.promise`)
    visible on home and scan pages.
12. **Works on a weak phone.** Total JS for the reporter routes ≤ 300 KB gzip (lazy-load
    the dashboard, Leaflet and Recharts); no animation required to use the app.

## 2. Design tokens (define in `src/index.css` with Tailwind v4 `@theme`)

```css
@import "tailwindcss";

@theme {
  --color-sos: #E11D2E;          /* SOS button, critical */
  --color-sos-dark: #B0101F;
  --color-critical: #E11D2E;
  --color-high: #F97316;
  --color-medium: #EAB308;
  --color-low: #22C55E;
  --color-ack: #16A34A;          /* acknowledged */
  --color-pending: #64748B;      /* waiting */
  --color-escalated: #DC2626;
  --color-info: #2563EB;
  --color-surface: #FFFFFF;      /* reporter app background */
  --color-ink: #0F172A;          /* main text */
  --color-muted: #475569;
  --color-dash-bg: #0B1220;      /* dashboard background */
  --color-dash-panel: #111A2E;
  --color-dash-border: #1E2A44;
  --color-dash-text: #E2E8F0;

  --font-sans: "Inter", system-ui, sans-serif;
  --font-urdu: "Noto Nastaliq Urdu", "Noto Naskh Arabic", serif;

  --radius-xl: 1rem;
}
```

Fonts: load from Google Fonts in `index.html`:
`Inter:wght@400;600;800` and `Noto+Nastaliq+Urdu:wght@400;700`.
When `i18n.language === 'ur'`: set `<html dir="rtl" lang="ur">` and apply
`font-family: var(--font-urdu)` with `line-height: 2` (Nastaliq needs extra line height).

Severity → color map (single source: `src/lib/severity.ts`):
`low → --color-low`, `medium → --color-medium`, `high → --color-high`,
`critical → --color-critical`.

Alert target status → chip: `queued`/`sent` gray "⏳ Alerted", `delivered` blue
"📨 Delivered", `acknowledged` green "✅ Acknowledged", `escalated` orange
"📞 Escalating", `no_response` red "❌ No response", `failed` red "⚠ Failed".

## 3. Routes and screens

| Route | Screen | Auth |
|---|---|---|
| `/` | Reporter Home | none (anonymous Supabase session auto-created) |
| `/silent` | Silent SOS | none |
| `/report/:id` | Report Status | same anonymous session |
| `/family` | Family Finder | phone OTP |
| `/join` | Join as donor / volunteer / register emergency profile | phone OTP |
| `/ack/:token` | Acknowledge confirmation | token |
| `/r/:token` | Responder inbox (web alerts + big ✅, F-10/F-13; replaces Telegram in the demo) | org inbox token |
| `/card/new`, `/card/:id`, `/card/:id/print` | Emergency Card wizard, card detail (scan count, delete), print sheet (F-36) | session (anonymous ok) |
| `/c/:token` | Public card scan page (F-36) | none |
| `/flow` | Live Flow architecture view (F-46) | `role:dispatcher,admin` |
| `/command` | 3D command view (F-47, Tier 3H-B) | `role:dispatcher,admin` |
| `/about` | Public landing with decorative 3D scene (F-47) | none |
| `/place/new`, `/place/:id`, `/place/:id/print` | Place Plan wizard, detail, poster (F-37) | session (anonymous ok) |
| `/p/:token` | Public place scan page (F-37) | none |
| `/login` | Responder login | none |
| `/dashboard` | Dispatcher / responder map + incidents | role ≠ reporter |
| `/dashboard/incidents/:id` | Incident detail (also opens as side panel) | role |
| `/dashboard/hospital` | Hospital console | `hospital_staff` |
| `/dashboard/analytics` | Analytics | `dispatcher`, `admin` |
| `/dashboard/settings` | Link Telegram (optional), profile | role ≠ reporter |

### 3.1 Reporter Home (`/`) — mobile first, white background

Layout top → bottom:
1. Header bar (56 px): logo "Golden Minute" (left), language toggle `EN | ES | اردو` (right; only languages in config), round 🔊 `ListenButton`.
   Below it a `SafetyPromise` card (F-42) and, at the bottom, a tile "🪪 Make my emergency card" → `/card/new`.
2. Optional red banner (from `GET /api/v1/public/alerts`): "⚠ Emergency near Downtown —
   avoid the area".
3. **SOS button**: circle, diameter `min(70vw, 320px)`, `bg-sos`, white 800-weight text
   "SOS" (48 px) + subtext `t('sos.subtitle')`. Pulse
   animation (`animate-ping` ring, disabled when `prefers-reduced-motion`).
4. Row of 3 large secondary buttons (each ≥ 64 px tall, icons from lucide):
   🎤 `Mic` "Hold to speak" · 📷 `Camera` "Photo" · ✍ `Type` "Type".
5. "Silent mode" switch (shadcn Switch) with `EyeOff` icon → navigates to `/silent`.
6. Footer: emergency call buttons from `config.emergency_numbers` (`tel:` links;
   US: one full-width "Call 911" button; PK: 2×2 grid Rescue 1122 / Police 15 / Edhi 115 / Fire 16).
7. Small links: "Find a family member" → `/family`, "Become a donor/volunteer" → `/join`,
   "Warn me about danger nearby" (toggle → push subscribe).

Interactions:
- SOS tap → full-screen overlay: big countdown "Sending in 3…2…1", huge "Cancel" button.
- Hold-to-speak: press and hold; while recording show red waveform bar + timer "0:07 / 1:00";
  release = send; slide up = cancel. Accessible fallback: tap once to start, tap again
  to stop.
- Photo: opens camera; preview with optional caption field + "Send" button.
- Type: shadcn Sheet from bottom with Textarea (placeholder "What happened? Where?") +
  "Send".
- Location permission is requested on first interaction, not on page load; while
  resolving show "📍 Getting your location…" in the overlay. If permission was already
  granted earlier, read the location on load.
- **Location-aware profile (F-35):** once a location is known, call
  `GET /api/v1/config?lat&lng` and swap the emergency buttons, default language (unless the
  user chose one), units and time zone. Show a small chip under the header:
  "📍 {location_label} · {primary_emergency_number}". While detecting, keep the fallback
  buttons plus a "Call 112" button visible; never show an empty footer.
- **Nearest hospitals card (F-35):** below the secondary buttons, a compact Card titled
  `t('nearby.title')` listing up to 5 hospitals: name, distance ("2.4 mi" / "3.1 km"),
  phone shown as selectable text with a `tel:` link, and a "Map" link. Loading state:
  skeleton rows + "Finding hospitals near you…". Empty state: "No hospitals found nearby.
  Call {primary_emergency_number}." The same card appears on the status page below the
  service ticks.

### 3.2 Report Status (`/report/:id`)

1. Big status header: "Help is being alerted" → when ≥ 1 ack: "Help is on the way".
   Under it, when `incident.landmark_local` exists: `t('landmark.heading')` + the line (F-38).
   A huge 🗣 **Talk me through it** button (`t('coach.button')`) opens the `CoachSheet` (F-39).
2. Incident code chip `GM-7K3Q` (copy button).
3. Service ticks list (one row each, 56 px): 🏥 Hospital · 🚑 Ambulance/Rescue ·
   👮 Police · 🚒 Fire (only rows in `needs`). Each row: ⏳ Alerted → ✅ Acknowledged
   (with time "in 42 s").
4. Follow-up question card (if any): question text + Input + mic + "Send".
5. First-aid cards (max 3): Card with title, numbered steps, icon. Language per toggle (EN/ES/UR).
6. "What we understood": transcript/summary (collapsible).
7. Footer call buttons (same as home).
8. Offline state: yellow Alert "Saved on your phone – will send when connected".

### 3.3 Silent SOS (`/silent`)

- Entire screen `#000`, no header. Center: a dark-gray (`#111`) circle 200 px with the
  text "Hold 2s" in `#333`.
- Holding 2 s fills a thin ring (`#222` → `#444`); release early = nothing.
- After send: tiny `#444` text "Sent ✓ GM-XXXX" at bottom. No sound, no vibration
  (`navigator.vibrate` never called), no toast. Exit by swiping/back.

### 3.4 Family Finder (`/family`)

Step 1: phone input (country code from config prefilled) → "Send code" → 6-digit OTP input (Supabase).
Step 2: "Name of the person" Input + optional "Incident code" Input → "Search".
Results: Cards "May be at: {hospital} · Call help desk {phone} · Arrived {date}". Empty
state: "No match yet. Hospitals update every few minutes. Try again later or call {primary_emergency_number}."
Privacy note text under results.

### 3.5 Join (`/join`)

Phone OTP, then form: name, role checkboxes (Blood donor / CPR / First aid / Nurse /
Doctor), blood type Select (8 groups + "Don't know"), "Use my current location as home
area" button (stores coarse location), consent checkbox (required) "I agree to receive
emergency requests. I can leave any time." Then "Link Telegram" deep-link button (shown only when `TELEGRAM_ENABLED`).

### 3.6a Responder inbox (`/r/:token`) — the demo's responder channel

Mobile-first, white background, no login. Sticky header: organization name (left), "● Live"
(green radio icon), language toggle `EN | ES | اردو` (default = the organization's `lang`
on first visit, then the saved choice). Body: one card per alert, newest first, polled every
3 s (React Query `refetchInterval`). Card = 8 px severity colour bar; first template line as
the headline (🚨/🏥/🟡 STANDBY, with a "Standby" badge for unverified hospital alerts); the
remaining fixed-template lines (location, 🧭 landmark line, casualties, injuries, 🩸, ETA,
⚠ danger/silent); an "Open map" outline button; then ONE huge green button
(`h-20`, ✅ icon, "I am responding" / "میں جا رہا ہوں"). After a press the button is replaced
by a green "Confirmed · time" panel (the page never reloads). Empty state: inbox icon,
"No alerts yet — keep this page open." Invalid/expired link state: link icon + "Ask the
control room for a new link." All text via `t('responder.*')` in `en/es/ur.json`; alert text
comes from the backend in all three languages. RTL when Urdu is selected.

### 3.6 Acknowledge (`/ack/:token`)

Card: incident summary (fetched with token), recipient name, one huge green button
"✅ Acknowledge – we are responding". Success state: "Acknowledged at 14:32. Thank you."
Expired/used token state: "This link was already used or expired."
(GET must never acknowledge — link previews would trigger it.)

### 3.7 Login (`/login`)

Email + password (Supabase). Demo accounts listed in `11_ENV_SETUP.md`.

### 3.8 Dashboard (`/dashboard`) — desktop first, dark theme

Grid: `[incidents 340px][map 1fr][agent feed 380px]`, header 56 px, below the header an
**Agent Lights strip** (40 px, see 3.12). Below 1280 px width the agent feed collapses
into a tab next to the incident list.
- Header: logo, role badge, org name, live clock (profile time zone), connection dot
  (Realtime status), user menu.
- Sidebar tabs: **Active** · **Review** (dispatcher only, count badge) · **Closed**.
  Incident card: severity color strip (left 4 px), short code, type icon + label,
  location label, time ago, report count "×5", confidence %, status badge,
  ack progress "3/5 ✅", silent icon if silent.
- Map (react-leaflet): OSM tiles; markers:
  - Incident: circle marker radius by severity (10/14/18/22 px), fill severity color,
    pulsing ring if unacked targets exist.
  - Hospital: `Hospital` lucide icon in white square; tooltip "Name · 6 beds · burns,
    trauma"; assigned hospitals outlined in blue with label "+4 (2 critical)".
  - Police/Rescue/Fire stations: icons `Shield`, `Ambulance`, `Flame`.
  - Ambulances: small `Ambulance` icon moving; route polyline dashed.
  - Selected incident: 500 m merge circle (dashed, 30 % opacity).
- Clicking an incident opens a right Sheet (520 px) with the detail view (3.9).
- New incident → `sonner` toast + sound `public/sounds/alert.mp3` (dashboard only,
  user-toggleable).

### 3.9 Incident detail

Sections in order: header (code, type, severity Badge, status, Verify/Dismiss/Close
buttons by role) → Summary EN + local language (with language chip) → Key facts grid (casualties min–max, injuries
chips, needs chips, ongoing danger, confidence with Progress bar + breakdown tooltip) →
**Alert targets** table (recipient, kind, channels icons, status chip, ack time,
escalation level) → **Hospital assignments** table (hospital, patients, critical, ETA,
reason) → **Doctors** (hospital staff view) → **Community** (donors/volunteers coming
counts) → **Reports** list (channel icon, time, transcript/text, photo thumbnail via
signed URL, AI confidence) → **Timeline** (`incident_events`, newest first) →
After-action report (closed incidents).

### 3.12 Agent Activity feed + Agent Lights (F-33) — the judges' favorite screen

**Agent Lights strip:** nine pills in a row (the last three can wrap on narrow screens), one
per agent: `🧠 Intake`, `🔎 Verification`, `🏥 Triage`, `📣 Dispatch`, `🩺 Hospital Prep`,
`📝 Debrief`, `🧭 Landmark`, `🗣 Voice Coach`, `🪪 Preparedness`. State from the latest
`agent_activity` row for the selected incident (or the most recent incident):
- idle — gray outline;
- working (`started`/`tool_call` in last 10 s without `finished`/`decision`) — blue fill with
  a subtle pulse (`animate-pulse`, disabled for reduced motion);
- done (`decision`/`finished`) — green;
- autopilot/fallback (`fallback` or `rule`) — amber with ⚙;
- blocked (`guardrail_block` in this run) — small 🛡 badge on the pill.

**Feed panel** (right column, dark panel, newest on top, max 200 rows, virtualized not
needed): each row = 2 lines:
- line 1: agent emoji + name (agent color), kind icon (🧠 decision · 🔧 tool_call ·
  📥 tool_result · 🛡 guardrail_block · ⚙ fallback/rule · ⚠ error · ▶ started · ✔ finished),
  relative time ("4 s ago"), model chip (e.g. `gemini-flash`, `groq`, or `autopilot`).
- line 2: `message` (≤ 200 chars).
- New rows slide in from the top (CSS transform 150 ms) and flash a 1 s highlight.
- Filter chips: `All`, `This incident`, per agent.
- Agent colors (fixed): Intake `#8B5CF6`, Verification `#06B6D4`, Triage `#22C55E`,
  Dispatch `#F97316`, Hospital Prep `#EC4899`, Debrief `#94A3B8`, Orchestrator `#64748B`.

Example rows (demo):
```
🧠 Intake · decision · gemini-flash · 2s ago
   Spanish voice report: active shooting at concert, 5–20 injured, police + EMS needed.
🔎 Verification · ⚙ rule · 1s ago
   Same event as GM-7K3Q (80 m away, same type) — merged. 3 reporters now.
🏥 Triage · 🛡 guardrail_block · groq · now
   Plan rejected: Hospital B has only 3 free beds (planned 5). Agent retrying.
🏥 Triage · decision · groq · now
   6 critical → 2 trauma centers (7 and 11 min); 8 minor → 2 community hospitals.
```

### 3.10 Hospital console (`/dashboard/hospital`)

Three cards: **Capacity** (number inputs ER beds, ICU, 8 blood-group inputs, accepting
switch, Save, last updated), **Incoming** (assignments for my hospital with ETA
countdown and ambulance list), **On-call doctors** (table + add/edit dialog + on-duty
switch), **Arrivals** (form: name optional, approx age, sex, wristband code; list).

### 3.15 Live Flow and 3D command view (F-46, F-47) — judge-facing, dispatcher-only

**Style:** these two screens are allowed to be dramatic: dark navy background, glowing
accents, subtle bloom-like glow via CSS `filter: drop-shadow`. The reporter app is NOT
changed (Common-person rules in §1 still apply there; no 3D).

**Live Flow (`/flow`):** left 70% the diagram (SVG from `architecture.html`), right 30% a
live log (time · agent · message, newest on top, max 40). Top bar: `Live` / `Replay`
toggle, incident picker, speed `×1 ×4`, language toggle. Node states: idle (grey), `active`
(glow, 2 s), `done` (soft colour), `blocked` (red flash), `autopilot` (amber dashed).

Event → node mapping (`components/flow/flowMap.ts`, source of truth for the animation):

| `agent_activity` row | Lights up (SVG ids from `architecture.html`) |
|---|---|
| `agent=orchestrator` started | `n-api`, `e-report` |
| `agent=intake` | `e-intake`, `a-intake`, `g-intake` |
| `agent=landmark` | `e-lm`, `a-landmark` |
| `agent=verification` | `e-iv`, `a-verif`, `g-verif`, `n-guard` |
| `agent=triage` | `e-vt`, `a-triage`, `g-triage`, `n-guard` |
| `agent=dispatch` | `e-td`, `a-dispatch`, `g-dispatch`, `n-guard`, plus `e-police`/`r-police`, `e-ems`/`r-ems`, `e-hosp`/`r-hosp`, `e-fire`/`r-fire` by the `org_type` of each target in `meta` |
| `agent=hospital_prep` | `e-dp`, `a-prep`, `g-prep`, `e-doc`, `r-doc` |
| `agent=voice_coach` | `e-coach`, `a-coach` |
| `agent=preparedness` | `e-prepared`, `a-prepared` |
| `agent=debrief` | `e-debrief`, `a-debrief`, `n-db` |
| any row kind `blocked` | add class `blocked` to `n-guard` |
| any row kind `fallback` | add class `autopilot` to that agent's node |
| `alert_targets.status = acknowledged` | `e-ack`, `l-ack`, `e-status`, `n-reporter` |
| any insert | `e-write`, `n-db` (brief) |

**3D command view (`/command`, `/about`):** full-bleed canvas, HUD overlay (incident
count, "alerts sent", "acks"), glass-style cards for the selected incident. Scene objects:
ground grid plane (dark navy, faint lines) tilted ~55°; hospitals/police = small boxes with
a type colour and `Html` label; incident = pulsing cylinder (height ∝ casualties_max,
colour by status: unverified amber, verified red, closed grey); alert arc = dashed
`QuadraticBezierLine` from incident to each target, dash offset animated, turns green on ack;
ambient `Float` particles are optional. Fallback component: the 2D Leaflet map.
`/about` shows the same scene with scripted demo data (no login) next to the product pitch
and three call-to-action buttons: Open app, See live flow, Make an Emergency Card.

### 3.14 Common-person screens (F-36 … F-42) — picture-first, voice-first

All of these follow the **Common-person rules** in §1. Every screen has a round 🔊 button
(top-right, 64 px) that reads the screen aloud; each tappable option has an icon.

**Emergency Card set-up (`/card/new`)** — a wizard with ONE question per screen, big
progress dots, 🔊 on each:
1. 🎤 "Tell me about yourself" — one huge mic button ("Hold and speak: your name, blood
   group, and a family number"). Below it: "or answer one by one" → guided form.
2. Name (large input, mic icon inside it fills it from speech).
3. Blood group — `BloodGroupPicker`: 8 big colored tiles (A+, A−, B+, B−, AB+, AB−, O+, O−)
   plus "I don't know".
4. Allergy — big "None" button + mic/text field (food or medicine names only).
5. Family contacts (1–3): name, relation icons (father/mother/brother/wife/…), phone keypad.
6. Confirm — the card shown full-screen exactly as a stranger will see it, read aloud,
   blood group as a large badge, "Is this correct?" with huge ✅ **Yes, save** / ✏ **Change**.
   Consent line (read aloud) and two switches: consent (required) and "Show my family
   number to people who scan" (`show_phone`).
7. Done — QR sticker preview + "Print" (`window.print()` of `/card/:id/print`) + "Show to
   family" (copies the scan link).

**Card print (`/card/:id/print`)** — A4 print CSS with 6 sticker cells: QR (`GET
/cards/{id}/qr.svg`), name, "اگر میں زخمی ہوں تو اسکین کریں / Scan if I am hurt", blood
group. Cut-lines. Navy text, maroon border.

**Scan page (`/c/:token`)** — what a stranger sees; mobile, no login, no navigation:
1. Red/white header with name (large) and blood-group badge; allergies line if present.
2. 🔊 reads: "This person is hurt? Press Get help." in the card's language.
3. Two huge buttons stacked: 🚑 **Get help** (red, ≥ 96 px tall) and 📞 **Call family**
   (outline; only if `show_phone`). Under them: emergency number buttons from the config.
4. `SafetyPromise` line (F-42) at the bottom.
5. After **Get help**: the normal status page (`/report/:id`) opens with the coach button.

**Place Plan (`/place/new`, `/place/:id/print`, `/p/:token`)** — same wizard pattern:
place type tiles with pictures (🏠 🏪 🏫 🕌 🏭 🏢), name, "Use my location" button, confirm.
The poster (`PlacePoster`) is a one-page A4: huge "Press for help / مدد کے لیے دبائیں"
and the QR, the landmark line, 3 nearest hospitals with distance/ETA and phone, and the
country's emergency numbers. Scan page `/p/:token` shows the same info and one huge
**Press for help** button.

**Voice Coach sheet (`CoachSheet`, opens from `/report/:id`)** — bottom sheet, full height:
1. Top: icon of the current card (lucide: `droplet`, `heart-pulse`, `flame`, `bone`, …),
   card title, step "2 of 4" dots.
2. Middle: the step text in very large type (28 px+), read aloud automatically; one icon
   illustration per step is optional.
3. Bottom: three huge buttons — ◀ **Repeat** · ▶ **Next** · 🎤 **Hold to speak**. A red
   📞 **Call {number}** button is always visible.
4. When the card is `cardiac`: a pulsing circle at 110 beats per minute with a soft tick
   sound (`CprMetronome`, Web Audio) and the text "Push hard and fast in the centre of
   the chest" (from the card file, not invented).
5. Disclaimer line `firstaid.disclaimer` at the bottom; `SafetyPromise` is not repeated here.

**Safety promise (F-42, `SafetyPromise`)** — a small calm card with a 🛡 icon on `/` and
`/c/:token`: `safety.promise` (see copy) + 🔊.

**Ride Mode (F-44, Tier L)** — toggle with a motorcycle icon on the home screen; the
"Are you OK?" overlay is full-screen red with a 20 s ring countdown, siren sound and one
huge green **I'M OK** button.

### 3.13 Settings → Simulate location (dev only, F-35)

Visible only when `/api/v1/config` reports `app_env = dev`. Select with presets Lahore,
Houston, Karachi, London, Mexico City, plus "Use real GPS". Stored in `sessionStorage` key
`gm:simLocation`; the reporter app uses it instead of `navigator.geolocation`. A yellow
banner "Simulated location: Lahore" shows on every reporter page while active.

### 3.11 Analytics (`/dashboard/analytics`)

KPI tiles row (5 tiles), Recharts BarChart "Median ack time by organization (s)",
LineChart "Incidents per day (30 d)", heatmap map card (leaflet.heat, radius 25,
blur 15). Use the dataviz skill guidance for chart colors if available.

## 4. Copy (i18n keys)

Store in `src/i18n/en.json`, `src/i18n/es.json`, `src/i18n/ur.json` (react-i18next,
`fallbackLng: 'en'`). Emergency-call button labels come from `config.emergency_numbers[].label`,
not from i18n files. Minimum keys:

| key | en | es | ur |
|---|---|---|---|
| `sos.button` | SOS | SOS | ایس او ایس |
| `sos.subtitle` | Press for emergency | Pulsa en caso de emergencia | ایمرجنسی کے لیے دبائیں |
| `sos.sending` | Sending in {{n}}… | Enviando en {{n}}… | {{n}} میں بھیجا جا رہا ہے… |
| `sos.cancel` | Cancel | Cancelar | منسوخ کریں |
| `report.speak` | Hold to speak | Mantén pulsado para hablar | بولنے کے لیے دبائے رکھیں |
| `report.photo` | Photo | Foto | تصویر |
| `report.type` | Type | Escribir | لکھیں |
| `report.placeholder` | What happened? Where? | ¿Qué pasó? ¿Dónde? | کیا ہوا؟ کہاں؟ |
| `status.alerting` | Help is being alerted | Estamos avisando a los servicios de emergencia | مدد کو اطلاع دی جا رہی ہے |
| `status.onTheWay` | Help is on the way | La ayuda está en camino | مدد راستے میں ہے |
| `status.hospital` | Hospital | Hospital | ہسپتال |
| `status.ambulance` | Ambulance | Ambulancia | ایمبولینس |
| `status.police` | Police | Policía | پولیس |
| `status.fire` | Fire department | Bomberos | فائر بریگیڈ |
| `status.alerted` | Alerted | Avisado | اطلاع دی گئی |
| `status.acknowledged` | Acknowledged | Confirmado | تصدیق ہو گئی |
| `offline.saved` | Saved on your phone – will send when connected | Guardado en tu teléfono – se enviará al conectarte | فون میں محفوظ – انٹرنیٹ ملتے ہی بھیج دیا جائے گا |
| `location.getting` | Getting your location… | Obteniendo tu ubicación… | آپ کی لوکیشن لی جا رہی ہے… |
| `location.ask` | Where are you? (landmark/area) | ¿Dónde estás? (referencia/zona) | آپ کہاں ہیں؟ (قریبی جگہ/علاقہ) |
| `silent.toggle` | Silent mode | Modo silencioso | خاموش موڈ |
| `silent.hold` | Hold 2s | Mantén 2 s | 2 سیکنڈ دبائیں |
| `firstaid.disclaimer` | Follow responders' instructions. This is basic guidance only. | Sigue las instrucciones del personal de emergencia. Esto es solo una guía básica. | امدادی عملے کی ہدایات پر عمل کریں۔ یہ صرف بنیادی رہنمائی ہے۔ |
| `danger.optin` | Warn me about danger nearby | Avísame de peligros cercanos | قریبی خطرے سے خبردار کریں |
| `family.link` | Find a family member | Buscar a un familiar | خاندان کے فرد کو تلاش کریں |
| `join.link` | Become a donor/volunteer | Ser donante/voluntario | ڈونر/رضاکار بنیں |
| `followup.send` | Send | Enviar | بھیجیں |
| `nearby.title` | Nearest hospitals | Hospitales más cercanos | قریب ترین ہسپتال |
| `nearby.loading` | Finding hospitals near you… | Buscando hospitales cerca de ti… | آپ کے قریب ہسپتال تلاش کیے جا رہے ہیں… |
| `nearby.empty` | No hospitals found nearby. Call {{number}}. | No se encontraron hospitales cerca. Llama al {{number}}. | قریب کوئی ہسپتال نہیں ملا۔ {{number}} پر کال کریں۔ |
| `location.chip` | 📍 {{label}} · {{number}} | 📍 {{label}} · {{number}} | 📍 {{label}} · {{number}} |
| `safety.promise` | You are helping. You do not need to give your name or phone. You will not be questioned or blamed. | Está ayudando. No necesita dar su nombre ni teléfono. No se le interrogará ni se le culpará. | آپ مدد کر رہے ہیں۔ آپ کو اپنا نام یا نمبر بتانے کی ضرورت نہیں۔ آپ سے کوئی سوال یا الزام نہیں ہوگا۔ |
| `listen.button` | Listen | Escuchar | سنیں |
| `card.title` | Emergency Card | Tarjeta de Emergencia | ایمرجنسی کارڈ |
| `card.new` | Make my emergency card | Crear mi tarjeta de emergencia | میرا ایمرجنسی کارڈ بنائیں |
| `card.speakPrompt` | Hold and speak: your name, blood group and a family number | Mantén pulsado y di: tu nombre, grupo sanguíneo y un número de familia | دبائے رکھیں اور بولیں: اپنا نام، خون کا گروپ اور گھر والوں کا نمبر |
| `card.bloodGroup` | Blood group | Grupo sanguíneo | خون کا گروپ |
| `card.dontKnow` | I don't know | No lo sé | مجھے نہیں معلوم |
| `card.allergy` | Allergy to food or medicine? | ¿Alergia a comida o medicina? | کھانے یا دوا سے الرجی؟ |
| `card.none` | None | Ninguna | کوئی نہیں |
| `card.family` | Family number | Número de un familiar | گھر والوں کا نمبر |
| `card.confirmQ` | Is this correct? | ¿Es correcto? | کیا یہ درست ہے؟ |
| `card.save` | Yes, save | Sí, guardar | ہاں، محفوظ کریں |
| `card.change` | Change | Cambiar | تبدیل کریں |
| `card.consent` | Anyone who scans this card will see these details | Cualquiera que escanee esta tarjeta verá estos datos | جو بھی یہ کارڈ اسکین کرے گا یہ معلومات دیکھ سکے گا |
| `card.showPhone` | Show my family number to people who scan | Mostrar mi número de familia a quien escanee | اسکین کرنے والوں کو میرے گھر والوں کا نمبر دکھائیں |
| `card.scanIfHurt` | Scan if I am hurt | Escanee si estoy herido | اگر میں زخمی ہوں تو اسکین کریں |
| `card.getHelp` | Get help | Pedir ayuda | مدد بلائیں |
| `card.callFamily` | Call family | Llamar a la familia | گھر والوں کو کال کریں |
| `card.inactive` | This card is no longer active | Esta tarjeta ya no está activa | یہ کارڈ اب فعال نہیں ہے |
| `place.new` | Prepare my place | Preparar mi lugar | اپنی جگہ تیار کریں |
| `place.pressForHelp` | Press for help | Pulse para pedir ayuda | مدد کے لیے دبائیں |
| `place.type.home` | Home | Casa | گھر |
| `place.type.shop` | Shop | Tienda | دکان |
| `place.type.school` | School | Escuela | سکول |
| `place.type.mosque` | Mosque | Mezquita | مسجد |
| `place.type.factory` | Factory | Fábrica | فیکٹری |
| `place.type.office` | Office | Oficina | دفتر |
| `place.type.other` | Other | Otro | دوسرا |
| `coach.button` | Talk me through it | Guíame paso a paso | مجھے بتائیں کیا کرنا ہے |
| `coach.next` | Next | Siguiente | اگلا |
| `coach.repeat` | Repeat | Repetir | دوبارہ |
| `coach.hold` | Hold to speak | Mantén pulsado para hablar | بولنے کے لیے دبائیں |
| `coach.call` | Call {{number}} | Llamar al {{number}} | {{number}} پر کال کریں |
| `landmark.heading` | Help is coming to: | La ayuda va hacia: | مدد یہاں آ رہی ہے: |
| `ride.areYouOk` | Are you OK? | ¿Estás bien? | کیا آپ ٹھیک ہیں؟ |
| `ride.imOk` | I'M OK | ESTOY BIEN | میں ٹھیک ہوں |

Also required in all three files for every enum value in `05_DATABASE_SCHEMA.md`:
`incidentType.<value>`, `severity.<value>`, `injury.<value>`, `need.<value>`,
`specialty.<value>`, `targetStatus.<value>`, `agent.<agent_name>`. Backend
`services/labels.py` must use the same wording for message templates.

## 5. Accessibility & motion

- Touch targets ≥ 48 px; SOS ≥ 200 px.
- All icon buttons have `aria-label` (translated).
- Respect `prefers-reduced-motion` (disable pulse and marker animations).
- Color is never the only signal: chips include icon + text.
- Status page uses `aria-live="polite"` for tick changes.

## 6. PWA manifest (`vite-plugin-pwa`)

```ts
manifest: {
  name: "Golden Minute",
  short_name: "GoldenMinute",
  description: "Report an emergency and alert help instantly",
  theme_color: "#E11D2E",
  background_color: "#FFFFFF",
  display: "standalone",
  start_url: "/",
  icons: [
    { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
  ]
}
```
Icons: red circle with white "GM" (generate once with any icon generator; place in
`frontend/public/icons/`).
