import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AGENT_META, LIGHT_AGENTS, lightState, type LightState } from '@/lib/agents'
import type { ActivityRow } from '@/lib/schemas'
import { cn } from '@/lib/utils'

const STYLE: Record<LightState, string> = {
  idle: 'border-dash-border text-dash-text/50',
  working: 'animate-pulse border-info bg-info/20 text-dash-text motion-reduce:animate-none',
  done: 'border-ack bg-ack/20 text-ack',
  autopilot: 'border-medium bg-medium/20 text-medium',
}

/** Nine agent pills: idle / working / done / autopilot (+ guardrail badge). */
export function AgentLights({ rows }: { rows: ActivityRow[] }) {
  const { t } = useTranslation()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 2000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-[#2F7FB8]/15 bg-white/85 px-3 py-2">
      {LIGHT_AGENTS.map((agent) => {
        const { state, blocked } = lightState(rows, agent, now)
        return (
          <span
            key={agent}
            className={cn('flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold', STYLE[state])}
          >
            {AGENT_META[agent].emoji} {t(`agent.${agent}`)}
            {state === 'autopilot' && ' ⚙'}
            {blocked && ' 🛡'}
          </span>
        )
      })}
    </div>
  )
}
