import { Link } from 'react-router-dom'
import { VideoBackdrop } from '@/components/VideoBackdrop'

const card = 'rounded-2xl border border-[#2F7FB8]/15 bg-[#FFFBF2]/80 p-5 shadow-sm backdrop-blur-md'
const eyebrow = 'text-[11px] font-bold uppercase tracking-widest text-[#2F7FB8]'

const AGENTS = [
  ['Intake', 'Turns a report into a structured incident.'],
  ['Verification', 'Merges duplicates and scores confidence.'],
  ['Triage', 'Helps distribute patients by need and capacity.'],
  ['Dispatch', 'Selects recipients and sends fixed templates.'],
  ['Hospital prep', 'Shares a concise pre-arrival brief.'],
  ['Debrief', 'Builds an after-action timeline.'],
  ['Landmark', 'Translates coordinates into familiar places.'],
  ['Voice coach', 'Reads vetted first-aid steps aloud.'],
  ['Preparedness', 'Creates a personal emergency QR card.'],
]

/** Public landing page (light blue + cream) with the looping video behind it. */
export default function Landing() {
  return (
    <div className="min-h-dvh text-[#12324A]">
      <VideoBackdrop />

      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-5">
        <div className="flex items-center gap-2 font-extrabold">
          <span className="grid size-9 place-items-center rounded-full bg-[#F2C14E]"><span className="size-4 rounded-full bg-[#FFF8EA]" /></span>
          GOLDEN MINUTE
        </div>
        <nav className="hidden gap-8 text-sm font-medium md:flex">
          <a href="#how">How it works</a><a href="#agents">AI agents</a><a href="#safety">Safety</a><Link to="/">Live demo</Link>
        </nav>
        <Link to="/login" className="rounded-lg bg-[#2F7FB8] px-4 py-2 text-sm font-bold text-[#FFF8EA] shadow hover:bg-[#256a9c]">
          Open command dashboard
        </Link>
      </header>

      <main className="mx-auto max-w-6xl space-y-20 px-5 pb-16 pt-6">
        <section className="grid items-center gap-8 md:grid-cols-2">
          <div className="space-y-5">
            <span className="inline-block rounded-full border border-[#2F7FB8]/30 bg-[#FFFBF2]/70 px-3 py-1 text-[11px] font-bold uppercase tracking-widest text-[#2F7FB8]">
              Multi-agent emergency response
            </span>
            <h1 className="text-5xl font-extrabold leading-tight md:text-6xl">
              Every second counts.<br /><span className="text-[#C98A12]">Every responder ready.</span>
            </h1>
            <p className="max-w-md text-[#35566E]">
              One tap, one spoken sentence, or one QR scan. Golden Minute coordinates emergency reporting, location
              intelligence and responder preparation in one connected flow.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/" className="rounded-lg bg-[#F2C14E] px-5 py-3 text-sm font-bold text-[#12324A] shadow hover:bg-[#e8b53d]">Explore the live demo →</Link>
              <a href="#how" className="rounded-lg border border-[#2F7FB8]/30 bg-[#FFFBF2]/70 px-5 py-3 text-sm font-bold">See how it works</a>
            </div>
            <p className="text-xs text-[#35566E]">Built for real people. Designed for the first 60 seconds of coordination.</p>
          </div>
          <div className={`${card} space-y-4`}>
            <p className={eyebrow}>Live incident coordination</p>
            <p className="font-bold">Lahore · Demo scenario</p>
            <div className="h-44 rounded-xl bg-gradient-to-br from-[#CFE6F6] to-[#FFF1D0]" />
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl bg-[#EAF4FB] p-3"><span className="font-bold text-[#2E9E6B]">● ACTIVE</span><br />Road collision · Kalma Chowk</div>
              <div className="rounded-xl bg-[#EAF4FB] p-3"><span className={eyebrow}>Responders notified</span><br />Ambulance ✓ Police ✓ Hospital ✓</div>
            </div>
          </div>
        </section>

        <section className={`${card} grid grid-cols-2 gap-4 md:grid-cols-4`}>
          {[['01', 'One action', 'No account. No typing.'], ['09', 'Specialist agents', 'One coordinated workflow.'], ['24/7', 'Responder network', 'Alerts sent together.'], ['UR / EN', 'Voice-first', 'Built for local language.']].map(([n, a, b]) => (
            <div key={a}><p className="text-2xl font-extrabold text-[#2F7FB8]">{n}</p><p className="font-bold">{a}</p><p className="text-xs text-[#35566E]">{b}</p></div>
          ))}
        </section>

        <section className="space-y-6">
          <p className={eyebrow}>The problem we are solving</p>
          <h2 className="text-3xl font-extrabold">An emergency is already chaotic.</h2>
          <p className="max-w-xl text-[#35566E]">The first person on scene may be scared, unable to type, may not speak English, and may not know who to call first.</p>
          <div className="grid gap-4 md:grid-cols-3">
            {[['01', 'Hard to explain', 'A witness may be scared or unsure how to describe the location.'], ['02', 'Disconnected response', 'Ambulance, police and hospitals are often contacted separately, and late.'], ['03', 'Critical context missing', 'Duplicate reports and unavailable patient details slow down decisions.']].map(([n, a, b]) => (
              <div key={n} className={card}><p className="text-xs font-bold text-[#C98A12]">{n}</p><h3 className="mt-2 font-bold">{a}</h3><p className="mt-1 text-sm text-[#35566E]">{b}</p></div>
            ))}
          </div>
          <p className="text-xl font-bold text-[#2F7FB8]">One simple start. A coordinated response.</p>
        </section>

        <section id="how" className="space-y-6">
          <p className={eyebrow}>How Golden Minute works</p>
          <h2 className="text-3xl font-extrabold">From first signal to shared situational awareness.</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {[['Report', 'One tap, voice or QR', 'Start without an account or a typed form. Voice-first intake supports Urdu and English.'], ['Coordinate', 'Nine agents work together', 'Verify reports, identify landmarks, structure triage and prepare responder briefings.'], ['Notify', 'One coordinated alert', 'Send fixed-format alerts to relevant services and track acknowledgements in one view.']].map(([k, a, b], i) => (
              <div key={k} className={card}>
                <span className="grid size-8 place-items-center rounded-full bg-[#CFE6F6] text-xs font-bold">0{i + 1}</span>
                <p className={`${eyebrow} mt-3`}>{k}</p><h3 className="font-bold">{a}</h3><p className="mt-1 text-sm text-[#35566E]">{b}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="agents" className="space-y-6">
          <p className={eyebrow}>The coordination engine</p>
          <h2 className="text-3xl font-extrabold">Nine specialists. One shared mission.</h2>
          <p className="max-w-xl text-[#35566E]">Each agent proposes a focused result. Deterministic code applies the rules, and people stay in control.</p>
          <div className="grid gap-3 md:grid-cols-3">
            {AGENTS.map(([a, b], i) => (
              <div key={a} className={`${card} flex gap-3 !p-4`}>
                <span className="text-xs font-bold text-[#C98A12]">0{i + 1}</span>
                <div><p className="font-bold">{a}</p><p className="text-xs text-[#35566E]">{b}</p></div>
              </div>
            ))}
          </div>
        </section>

        <section id="safety" className="space-y-4">
          <p className={eyebrow}>Safety is part of the design</p>
          <h2 className="text-3xl font-extrabold">AI assists. People decide.</h2>
          <p className="max-w-xl text-[#35566E]">No AI-written emergency alerts or unverified medical advice. Fixed templates, vetted first-aid cards, privacy safeguards and human review keep the system accountable.</p>
          <div className="flex flex-wrap gap-3 text-xs font-bold">
            {['Human-controlled', 'Privacy-first', 'Vetted guidance'].map((t) => <span key={t} className="rounded-full border border-[#2F7FB8]/30 bg-[#FFFBF2]/80 px-4 py-2 text-[#2F7FB8]">{t}</span>)}
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 border-t border-[#2F7FB8]/20 px-5 py-6 text-xs text-[#35566E]">
        <span>GOLDEN MINUTE · Every second matters.</span><span>A coordination layer, not a replacement for emergency services.</span>
      </footer>
    </div>
  )
}
