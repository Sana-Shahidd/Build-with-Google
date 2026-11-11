// Agent display metadata (docs/09 section 3.12). Colours are fixed by the design doc.
export const AGENT_META: Record<string, { emoji: string; color: string }> = {
  orchestrator: { emoji: '⚙️', color: '#64748B' },
  intake: { emoji: '🧠', color: '#8B5CF6' },
  verification: { emoji: '🔎', color: '#06B6D4' },
  triage: { emoji: '🏥', color: '#22C55E' },
  dispatch: { emoji: '📣', color: '#F97316' },
  hospital_prep: { emoji: '🩺', color: '#EC4899' },
  debrief: { emoji: '📝', color: '#94A3B8' },
  landmark: { emoji: '🧭', color: '#14B8A6' },
  voice_coach: { emoji: '🗣', color: '#EAB308' },
  preparedness: { emoji: '🪪', color: '#A855F7' },
}

export const LIGHT_AGENTS = [
  'intake',
  'verification',
  'triage',
  'dispatch',
  'hospital_prep',
  'debrief',
  'landmark',
  'voice_coach',
  'preparedness',
] as const

export const KIND_ICON: Record<string, string> = {
  decision: '🧠',
  tool_call: '🔧',
  tool_result: '📥',
  guardrail_block: '🛡',
  fallback: '⚙',
  rule: '⚙',
  error: '⚠',
  started: '▶',
  finished: '✔',
}

export type LightState = 'idle' | 'working' | 'done' | 'autopilot'

const WORKING_WINDOW_MS = 10_000

/** Agent Lights state from the latest activity row of that agent (docs/09 section 3.12). */
export function lightState(rows: { agent: string; kind: string; created_at: string }[], agent: string, now: number): { state: LightState; blocked: boolean } {
  const mine = rows.filter((r) => r.agent === agent)
  const latest = mine[0] // rows are newest first
  if (!latest) return { state: 'idle', blocked: false }
  const blocked = mine.slice(0, 5).some((r) => r.kind === 'guardrail_block')
  const age = now - new Date(latest.created_at).getTime()
  if ((latest.kind === 'started' || latest.kind === 'tool_call') && age < WORKING_WINDOW_MS) return { state: 'working', blocked }
  if (latest.kind === 'fallback' || latest.kind === 'rule') return { state: 'autopilot', blocked }
  return { state: 'done', blocked }
}
