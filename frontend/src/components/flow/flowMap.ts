// Event -> SVG node ids (docs/09 section 3.15). Source of truth for the Live Flow animation.
// Ids come from the <svg> copied from docs/architecture.html (flow.svg).

export type FlowEffect = {
  /** ids that glow while the event is "active" (about 2 s), then settle to `done` */
  active: string[]
  /** id -> special state: the agent node shows autopilot, the guardrail node flashes red */
  autopilot?: string
  blocked?: boolean
}

type ActivityLike = { agent: string; kind: string }

const AGENT_IDS: Record<string, string[]> = {
  orchestrator: ['n-api', 'e-report'],
  intake: ['e-intake', 'a-intake', 'g-intake'],
  landmark: ['e-lm', 'a-landmark'],
  verification: ['e-iv', 'a-verif', 'g-verif', 'n-guard'],
  triage: ['e-vt', 'a-triage', 'g-triage', 'n-guard'],
  dispatch: ['e-td', 'a-dispatch', 'g-dispatch', 'n-guard'],
  hospital_prep: ['e-dp', 'a-prep', 'g-prep', 'e-doc', 'r-doc'],
  voice_coach: ['e-coach', 'a-coach'],
  preparedness: ['e-prepared', 'a-prepared'],
  debrief: ['e-debrief', 'a-debrief', 'n-db'],
}

/** The agent's own node (used for the autopilot state). */
const AGENT_NODE: Record<string, string> = {
  intake: 'a-intake',
  landmark: 'a-landmark',
  verification: 'a-verif',
  triage: 'a-triage',
  dispatch: 'a-dispatch',
  hospital_prep: 'a-prep',
  voice_coach: 'a-coach',
  preparedness: 'a-prepared',
  debrief: 'a-debrief',
}

/** recipient_kind of an alert target -> responder node + edge. */
const RESPONDER_IDS: Record<string, string[]> = {
  police: ['e-police', 'r-police'],
  rescue: ['e-ems', 'r-ems'],
  hospital: ['e-hosp', 'r-hosp'],
  fire: ['e-fire', 'r-fire'],
}

export const ACK_IDS = ['e-ack', 'l-ack', 'e-status', 'n-reporter']
export const WRITE_IDS = ['e-write', 'n-db']

/** Effect of one agent_activity row. `targetKinds` = recipient_kind of the incident's alert targets. */
export function effectForActivity(row: ActivityLike, targetKinds: string[] = []): FlowEffect {
  const active = [...(AGENT_IDS[row.agent] ?? [])]
  if (row.agent === 'dispatch') {
    for (const kind of new Set(targetKinds)) active.push(...(RESPONDER_IDS[kind] ?? []))
  }
  const effect: FlowEffect = { active: [...active, ...WRITE_IDS] }
  if (row.kind === 'guardrail_block') effect.blocked = true
  if (row.kind === 'fallback' || row.kind === 'rule') effect.autopilot = AGENT_NODE[row.agent]
  return effect
}

/** Effect of a responder acknowledging (alert_targets.status = acknowledged). */
export function effectForAck(): FlowEffect {
  return { active: [...ACK_IDS] }
}

export const ALL_IDS: string[] = [
  ...new Set([
    ...Object.values(AGENT_IDS).flat(),
    ...Object.values(RESPONDER_IDS).flat(),
    ...ACK_IDS,
    ...WRITE_IDS,
  ]),
]
