import { ArrowLeft, BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

const card = 'rounded-2xl border border-[#2F7FB8]/15 bg-white/90 p-5 shadow-sm'

type Agent = { emoji: string; name: string; job: string; example: string; safety: string; ifDown: string }

const AGENTS: Agent[] = [
  {
    emoji: '🧠',
    name: 'Intake Agent',
    job: 'Reads what a bystander said or typed (in Urdu, English, Spanish or Roman Urdu) and turns it into a tidy form: what happened, how serious, how many people are hurt, what help is needed (ambulance, police, fire, rescue), and whether danger is still going on.',
    example: '"Gaari ka accident ho gaya, do log zakhmi hain" becomes: road accident, severity high, 2 hurt, needs ambulance + police.',
    safety: 'It only extracts facts. Anything written inside the report that looks like an instruction (for example "ignore your rules") is treated as plain text and ignored.',
    ifDown: 'A keyword classifier (no AI) reads the same text. A bare SOS press with no words uses a fixed default.',
  },
  {
    emoji: '🔎',
    name: 'Verification Agent',
    job: 'Decides whether a new report is about an event we already know (same place, same time) or a brand-new event. Ten people reporting the same crash become ONE incident, not ten.',
    example: 'A report 120 m from an open crash incident, 3 minutes later, says "fire after the crash". It is merged into the same incident.',
    safety: 'It may only merge into incidents the system itself listed as nearby candidates, and only when it is at least 60% sure. Otherwise the report becomes a new incident.',
    ifDown: 'A distance rule merges into the nearest incident within 500 m of a compatible type.',
  },
  {
    emoji: '🏥',
    name: 'Triage Agent',
    job: 'Spreads the expected injured people across nearby hospitals so every patient gets the right care and no emergency room is overwhelmed: critical patients go to hospitals with the right unit (trauma, burns, neuro), minor ones to the nearest hospitals with free beds.',
    example: '8 people hurt, 4 critical: 4 critical to the trauma hospital 6 minutes away, 4 minor to two closer hospitals with free beds.',
    safety: 'Code checks the plan: numbers must add up exactly, 1 to 5 hospitals, critical patients only where the capability exists. Travel times and "over capacity" flags are set by code, never by the AI.',
    ifDown: 'A built-in spreading rule makes the same kind of plan.',
  },
  {
    emoji: '📣',
    name: 'Dispatch Agent',
    job: 'Chooses the ORDER in which responders are alerted (police first for gunfire, ambulance and the busiest hospital first for mass injuries, fire early for fires).',
    example: 'Active shooter: police first, then rescue, then the hospital, then fire.',
    safety: 'It cannot add or remove anyone, cannot write messages and cannot invent recipients. Who must be alerted is decided by code; anyone the agent forgets is added automatically. Messages are fixed templates.',
    ifDown: 'A default order is used (rescue, hospitals, police, fire).',
  },
  {
    emoji: '🩺',
    name: 'Hospital Prep Agent',
    job: 'Gets receiving hospitals ready before patients arrive: queues on-call doctors with the needed specialty, asks nearby blood donors of the needed groups, and asks trained volunteers close to the scene to help until the ambulance arrives (only if it is safe).',
    example: 'Critical gunshot incident: queue a trauma surgeon and an anaesthetist at the receiving hospital, O-negative donors within 10 km.',
    safety: 'Each action has eligibility rules written in code (severity, number of injured, injury type, distance, cooldown so people are not pinged repeatedly). The agent only chooses among allowed actions and sees counts, never names or phone numbers.',
    ifDown: 'Every eligible action is done by rule. NOTE: in this version nobody is actually contacted (see "Current limits").',
  },
  {
    emoji: '📝',
    name: 'Debrief Agent',
    job: 'When an incident is closed, writes a short after-action report for the control room: summary, timeline, how fast alerts and acknowledgements were, delays, and recommendations.',
    example: '"First alert 30 s after the first report. Police did not acknowledge. Recommendation: follow up with non-responding units."',
    safety: 'Uses only the incident record. No names, no phone numbers, no medical advice. A report that is missing sections or contains phone-like numbers is rejected.',
    ifDown: 'A template fills the same sections with numbers calculated by code.',
  },
  {
    emoji: '🧭',
    name: 'Landmark Agent',
    job: 'Helps ambulance crews find the spot the way locals give directions: "near the petrol pump, opposite the mosque".',
    example: '"Near Madni Masjid, 50 m north of PSO Petrol Pump."',
    safety: 'Code looks up real named places from OpenStreetMap within 300 m. The agent can only use those places, distances and directions; a sentence with an invented name or number is rejected.',
    ifDown: 'A template builds the sentence from the same places. If the map service is busy, alerts go out with coordinates and the area name instead.',
  },
  {
    emoji: '🗣',
    name: 'Voice Coach Agent',
    job: 'Stays with the bystander and reads first-aid steps aloud one at a time, listening for "next", "repeat", "he is not breathing" and similar.',
    example: 'The bystander says "khoon nahi ruk raha" and the coach switches to the bleeding card.',
    safety: 'It never writes medical advice. It only chooses which pre-written, vetted card and step to read; the words spoken always come from the card file.',
    ifDown: 'Keyword matching chooses the card and step.',
  },
  {
    emoji: '🪪',
    name: 'Preparedness Agent',
    job: 'Meant to help people set up their Emergency Card or Place Plan by speaking instead of typing.',
    example: 'Planned: "My name is Ahmad, blood group O positive, call my brother."',
    safety: 'Planned: no illnesses, medicines or ID numbers, and phone numbers replaced before any AI sees the text.',
    ifDown: 'NOT BUILT in this version. Cards are created with the guided step-by-step form instead.',
  },
]

const STEPS = [
  ['1. Someone reports', 'A bystander presses SOS, holds the microphone and speaks, types a few words, or scans an Emergency Card / place QR code and presses "Get help". No account, no name, no phone number needed.'],
  ['2. The Intake Agent reads it', 'The report becomes a structured incident record: type, severity, number hurt, needs. First-aid cards are picked at the same moment so the bystander can start helping.'],
  ['3. Verification checks for duplicates', 'Nearby reports of the same event are merged. Several independent reports, a photo, or a precise location raise the confidence score. Confidence is calculated by code, not the AI.'],
  ['4. Status is set', 'Review (very low confidence: a dispatcher must look), Unverified (probably real: alerts go out), Verified (enough evidence or a dispatcher confirmed: full alerts, hospital preparation).'],
  ['5. Triage and Landmark run', 'Triage spreads patients over hospitals. Landmark writes the local-style directions. Neither can delay the alert.'],
  ['6. Dispatch alerts responders', 'Police, rescue, fire and receiving hospitals get a fixed-template alert on their private responder page with an "Acknowledge" button. A hospital gets a short standby notice while unverified and the full brief once verified.'],
  ['7. Responders acknowledge', 'Each tap on "Acknowledge" is recorded, and the reporter\'s phone shows green ticks ("Hospital confirmed", "Police confirmed"). Unacknowledged alerts are flagged.'],
  ['8. Hospital Prep and ambulances', 'For verified incidents, doctors, donors and volunteers are queued, and in simulation mode ambulances drive to the scene and to the hospital on the map.'],
  ['9. Close and debrief', 'A dispatcher closes the incident and the Debrief Agent writes the after-action report.'],
]

const FIXED_BY_CODE = [
  ['Confidence and status', 'How sure we are an incident is real, and when it becomes verified.'],
  ['Who must be alerted', 'Police for violence, ambulance for injuries, fire for fire or explosions, plus the assigned hospitals.'],
  ['Alert wording', 'Fixed templates in English, Spanish and Urdu. No AI-written alerts.'],
  ['First-aid steps', 'Pre-written, vetted cards. The AI can only pick which one to read.'],
  ['Hospital plan checks', 'Totals, capability fit, ETA and over-capacity flags.'],
]

const PAGES = [
  ['Reporter app  ( / )', 'Big SOS button, hold-to-speak microphone, text report, Emergency Card, call buttons (1122, 15). After sending: a status page with ticks, first-aid cards read step by step, and a Listen button.'],
  ['Dashboard  ( /dashboard )', 'For dispatchers. Live map, live incident list, KPI cards, nine agent lights, and the Agent Activity feed. Click an incident to verify, dismiss or close it and to see its alerts and hospital plan.'],
  ['Control Room  ( /control-room )', 'For the control-room team (admin login). Shows whether every agent is healthy, how often the backup rules took over, and a queue of guardrail blocks and failures for a person to review. It cannot act on incidents.'],
  ['Live Flow  ( /flow )', 'An animated architecture diagram that lights up as a real incident moves through the agents. A Replay mode re-runs a past incident.'],
  ['Responder page  ( /r/... )', 'A private link for one hospital, police station or rescue unit. It shows only that unit\'s alerts, with an Acknowledge button.'],
  ['Emergency Card  ( /card/new, /c/... )', 'A person sets up name, blood group, allergies and up to 3 family contacts once. Anyone scanning the card\'s QR sees only those details and can press "Get help".'],
  ['Place Plan  ( API ready )', 'A shop, school or mosque is registered once with its 3 nearest hospitals; a poster QR lets anyone press "Get help" with the exact location. Its screens are still to be designed.'],
  ['User Guide  ( /guide )', 'This page.'],
]

const GLOSSARY = [
  ['Status: Review', 'Low confidence. A dispatcher should look before anyone is alerted.'],
  ['Status: Unverified', 'Probably real. Police/rescue are alerted; one hospital gets a standby notice.'],
  ['Status: Verified', 'Enough evidence, or a dispatcher confirmed. All responders and hospitals alerted, prep starts.'],
  ['Status: Closed / Dismissed', 'Finished, or judged a false alarm.'],
  ['Severity', 'Low, medium, high, critical. Decided from number hurt, type of danger and what the reporters said.'],
  ['Agent light green', 'The agent finished its work.'],
  ['Agent light blue (pulsing)', 'The agent is working now.'],
  ['Agent light amber ⚙', 'The built-in rules (autopilot) did the work because the AI was slow or unavailable. The alert still went out.'],
  ['Shield 🛡 on an agent', 'A guardrail rejected something the agent proposed.'],
  ['Autopilot', 'The plain, non-AI backup every agent has. Alerts never depend on an AI answering.'],
]

const LIMITS = [
  'Doctors, blood donors and volunteers are only QUEUED in the records; no message, call or push is sent to them yet because no channel for that is set up.',
  'Telegram alerts are switched off. Hospitals and police receive alerts on their private web responder page instead. Family contacts of a scanned card appear on a "call manually" list.',
  'The Preparedness Agent (voice set-up of cards) is not built; cards use a guided form.',
  'The AI models are on a free tier and are sometimes slow. When that happens the amber autopilot lights show and alerts still go out within about 35 seconds.',
  'Place names on the map need the public OpenStreetMap service; if it is busy, directions fall back to coordinates and the area name.',
  'Ambulances are a simulation (3 vehicles), not real tracking.',
]

const FAQ = [
  ['Does the AI make life-or-death decisions?', 'No. Agents propose; code and people decide. Every agent has a rule-based backup and a dispatcher can verify or dismiss any incident.'],
  ['What if two people report the same crash?', 'They are merged into one incident and the confidence goes up, so responders get one alert, not two.'],
  ['What if a report is a prank?', 'Low-confidence single reports stay in Review for a dispatcher. Repeated reports from the same device are rate-limited.'],
  ['What happens to my phone number?', 'The reporter app never asks for it. Card family numbers are encrypted, never shown to any AI, and shown to a stranger only for contact 1 if the owner allowed it.'],
  ['Why do alerts sometimes show an amber light?', 'The AI was slow or busy, so the built-in rules took over. The alert is the same fixed template either way.'],
]

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6 space-y-4">
      <h2 className="text-2xl font-extrabold text-[#12324A]">{title}</h2>
      {children}
    </section>
  )
}

/** Layman's user guide: how the whole application and each agent works. */
export default function Guide() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const toc = [
    ['what', 'What is Golden Minute?'],
    ['journey', 'The journey of one report'],
    ['agents', 'The nine agents'],
    ['code', 'What code decides'],
    ['pages', 'Pages and who uses them'],
    ['glossary', 'Words on the dashboard'],
    ['limits', 'Current limits'],
    ['faq', 'Questions'],
  ]
  return (
    <div className="min-h-dvh bg-[#F4F8FC] text-[#12324A]">
      <header className="border-b border-[#2F7FB8]/15 bg-white/80 px-5 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <button
            type="button"
            onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/login'))}
            className="flex items-center gap-1 text-sm font-semibold text-[#2F7FB8]"
          >
            <ArrowLeft className="size-4" /> {t('login.back')}
          </button>
          <h1 className="ms-auto flex items-center gap-2 text-lg font-extrabold">
            <BookOpen className="size-5 text-[#2F7FB8]" /> User Guide
          </h1>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-8 px-5 py-8 lg:grid-cols-[220px_1fr]">
        <nav className="hidden lg:block">
          <ul className="sticky top-6 space-y-1 text-sm">
            {toc.map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`} className="block rounded-lg px-3 py-2 font-semibold text-[#4F6E84] hover:bg-[#E3F1FA]">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <main className="min-w-0 space-y-14">
          <Section id="what" title="What is Golden Minute?">
            <p className="text-lg leading-relaxed">
              Golden Minute is an emergency coordination system. When something goes wrong (a crash, a fire, a shooting, a collapse), the first
              minute matters most. A frightened bystander should be able to get help with <b>one tap, one spoken sentence or one QR scan</b>,
              and the right police, rescue and hospital teams should hear about it together, with the details they need.
            </p>
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ['For the bystander', 'No account, no typing, Urdu / English / Spanish, first-aid steps read aloud while help comes.'],
                ['For responders', 'One clear alert with type, place, number hurt and an Acknowledge button. Hospitals know what is coming.'],
                ['For the control room', 'A live map, one merged incident per event, and a feed that shows what every agent is doing.'],
              ].map(([t, d]) => (
                <div key={t} className={card}>
                  <p className="font-extrabold">{t}</p>
                  <p className="mt-1 text-sm text-[#4F6E84]">{d}</p>
                </div>
              ))}
            </div>
            <p className={cn(card, 'bg-[#E3F1FA]/80')}>
              <b>The big idea:</b> AI assists, people decide. Nine specialist AI "agents" each do one job. They <i>propose</i>; fixed rules ("guardrails")
              <i> check</i>; and every agent has a plain backup so an alert is never stuck waiting for an AI.
            </p>
          </Section>

          <Section id="journey" title="The journey of one report">
            <ol className="space-y-3">
              {STEPS.map(([t, d]) => (
                <li key={t} className={card}>
                  <p className="font-extrabold">{t}</p>
                  <p className="mt-1 text-[#35566E]">{d}</p>
                </li>
              ))}
            </ol>
          </Section>

          <Section id="agents" title="The nine agents, in plain words">
            <p className="text-[#35566E]">Think of them as nine colleagues in a control room, each with one job and a supervisor (the rules) looking over their shoulder.</p>
            <div className="space-y-4">
              {AGENTS.map((a, i) => (
                <article key={a.name} className={card}>
                  <h3 className="text-lg font-extrabold">
                    {a.emoji} {i + 1}. {a.name}
                  </h3>
                  <dl className="mt-3 space-y-2 text-sm">
                    {[
                      ['What it does', a.job],
                      ['Example', a.example],
                      ['What keeps it safe', a.safety],
                      ['If the AI is unavailable', a.ifDown],
                    ].map(([k, v]) => (
                      <div key={k} className="grid gap-1 sm:grid-cols-[170px_1fr]">
                        <dt className="font-bold text-[#2F7FB8]">{k}</dt>
                        <dd className="text-[#35566E]">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
          </Section>

          <Section id="code" title="What fixed rules decide (not the AI)">
            <div className="grid gap-3 md:grid-cols-2">
              {FIXED_BY_CODE.map(([t, d]) => (
                <div key={t} className={card}>
                  <p className="font-extrabold">{t}</p>
                  <p className="text-sm text-[#4F6E84]">{d}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section id="pages" title="Pages and who uses them">
            <div className="space-y-3">
              {PAGES.map(([t, d]) => (
                <div key={t} className={card}>
                  <p className="font-mono text-sm font-bold text-[#2F7FB8]">{t}</p>
                  <p className="mt-1 text-[#35566E]">{d}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section id="glossary" title="Words you will see on the dashboard">
            <div className="space-y-2">
              {GLOSSARY.map(([t, d]) => (
                <div key={t} className={cn(card, 'grid gap-1 !p-4 sm:grid-cols-[230px_1fr]')}>
                  <p className="font-bold">{t}</p>
                  <p className="text-sm text-[#35566E]">{d}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section id="limits" title="Current limits (honest list)">
            <ul className="list-disc space-y-2 ps-6 text-[#35566E]">
              {LIMITS.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </Section>

          <Section id="faq" title="Questions people ask">
            <div className="space-y-3">
              {FAQ.map(([q, a]) => (
                <details key={q} className={card}>
                  <summary className="cursor-pointer font-extrabold">{q}</summary>
                  <p className="mt-2 text-[#35566E]">{a}</p>
                </details>
              ))}
            </div>
          </Section>
        </main>
      </div>
    </div>
  )
}
