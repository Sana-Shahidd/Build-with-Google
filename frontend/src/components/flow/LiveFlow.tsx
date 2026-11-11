import { formatDistanceToNowStrict } from 'date-fns'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AGENT_META } from '@/lib/agents'
import { fetchEvents } from '@/lib/dashboard'
import { activityRow, type ActivityRow } from '@/lib/schemas'
import { supabase } from '@/lib/supabase'
import flowSvg from './flow.svg?raw'
import './flow.css'
import { ALL_IDS, effectForAck, effectForActivity, type FlowEffect } from './flowMap'

export type FlowMode = 'live' | 'replay'

type LogLine = { key: string; time: Date; agent: string; message: string }

const ACTIVE_MS = 2000
const MAX_LOG = 40
const MAX_GAP_MS = 3000

/** Live architecture view (F-46): the docs SVG animates from Supabase Realtime or from a replay. */
export function LiveFlow({
  mode,
  incidentId,
  speed,
  replayNonce,
}: {
  mode: FlowMode
  incidentId: string | null
  speed: number
  /** bump to (re)start a replay */
  replayNonce: number
}) {
  const { t } = useTranslation()
  const root = useRef<HTMLDivElement>(null)
  const timers = useRef<number[]>([])
  const [log, setLog] = useState<LogLine[]>([])

  const el = (id: string) => root.current?.querySelector<SVGElement>(`#${id}`) ?? null

  const reset = useCallback(() => {
    timers.current.forEach((id) => window.clearTimeout(id))
    timers.current = []
    root.current?.querySelectorAll('.active, .done, .autopilot, .blocked').forEach((n) => {
      n.classList.remove('active', 'done', 'autopilot', 'blocked')
    })
  }, [])

  const play = useCallback((effect: FlowEffect) => {
    const get = (id: string) => root.current?.querySelector<SVGElement>(`#${id}`) ?? null
    for (const id of effect.active) get(id)?.classList.add('active')
    if (effect.autopilot) get(effect.autopilot)?.classList.add('autopilot')
    if (effect.blocked) get('n-guard')?.classList.add('blocked')
    const timer = window.setTimeout(() => {
      for (const id of effect.active) {
        const n = get(id)
        n?.classList.remove('active')
        n?.classList.add('done')
      }
      if (effect.blocked) get('n-guard')?.classList.remove('blocked')
    }, ACTIVE_MS)
    timers.current.push(timer)
  }, [])

  const addLog = useCallback((line: Omit<LogLine, 'key'>) => {
    setLog((prev) => [{ ...line, key: `${line.time.getTime()}-${Math.random()}` }, ...prev].slice(0, MAX_LOG))
  }, [])

  const targetKinds = useCallback(async (iid: string | null) => {
    if (!iid) return []
    const { data } = await supabase.from('alert_targets').select('recipient_kind').eq('incident_id', iid)
    return (data ?? []).map((r) => r.recipient_kind as string)
  }, [])

  // ---- Live mode: Supabase Realtime --------------------------------------------------------
  useEffect(() => {
    if (mode !== 'live') return
    reset()
    setLog([])
    const channel = supabase
      .channel('flow-live')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_activity' }, (payload) => {
        const row = activityRow.safeParse(payload.new)
        if (!row.success) return
        if (incidentId && row.data.incident_id && row.data.incident_id !== incidentId) return
        void (async () => {
          const kinds = row.data.agent === 'dispatch' ? await targetKinds(row.data.incident_id) : []
          play(effectForActivity(row.data, kinds))
          addLog({ time: new Date(row.data.created_at), agent: row.data.agent, message: row.data.message })
        })()
      })
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'alert_targets' }, (payload) => {
        const next = payload.new as { status?: string; incident_id?: string; recipient_label?: string }
        if (next.status !== 'acknowledged') return
        if (incidentId && next.incident_id !== incidentId) return
        play(effectForAck())
        addLog({ time: new Date(), agent: 'dispatch', message: `✅ ${next.recipient_label ?? ''} acknowledged` })
      })
      .subscribe()
    return () => {
      void supabase.removeChannel(channel)
      reset()
    }
  }, [mode, incidentId, play, reset, addLog, targetKinds])

  // ---- Replay mode: re-run a stored incident at x1 / x4 ------------------------------------
  useEffect(() => {
    if (mode !== 'replay' || !incidentId || replayNonce === 0) return
    reset()
    setLog([])
    let cancelled = false
    void (async () => {
      const { data } = await supabase
        .from('agent_activity')
        .select('*')
        .eq('incident_id', incidentId)
        .order('id', { ascending: true })
      const rows = ((data ?? []) as unknown[]).map((r) => activityRow.parse(r))
      const events = (await fetchEvents(incidentId)).filter((e) => e.kind === 'acknowledged')
      const kinds = await targetKinds(incidentId)
      if (cancelled) return

      type Step = { at: number; run: () => void }
      const steps: Step[] = [
        ...rows.map((r): Step => ({
          at: new Date(r.created_at).getTime(),
          run: () => {
            play(effectForActivity(r, r.agent === 'dispatch' ? kinds : []))
            addLog({ time: new Date(r.created_at), agent: r.agent, message: r.message })
          },
        })),
        ...events.map((e): Step => ({
          at: new Date(e.created_at).getTime(),
          run: () => {
            play(effectForAck())
            addLog({ time: new Date(e.created_at), agent: 'dispatch', message: `✅ ${e.message}` })
          },
        })),
      ].sort((a, b) => a.at - b.at)

      let delay = 0
      let prev = steps[0]?.at ?? 0
      for (const step of steps) {
        delay += Math.min(step.at - prev, MAX_GAP_MS) / speed
        prev = step.at
        timers.current.push(window.setTimeout(step.run, delay))
      }
    })()
    return () => {
      cancelled = true
      reset()
    }
  }, [mode, incidentId, speed, replayNonce, play, reset, addLog, targetKinds])

  // make sure every mapped id really exists in the copied SVG (dev sanity check)
  useEffect(() => {
    if (import.meta.env.DEV) {
      const missing = ALL_IDS.filter((id) => !el(id))
      if (missing.length) console.warn('flowMap ids missing in flow.svg:', missing)
    }
  })

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-[7fr_3fr]">
      <div className="min-h-0 overflow-auto p-3">
        <div ref={root} className="flow-diagram min-w-[900px]" dangerouslySetInnerHTML={{ __html: flowSvg }} />
      </div>
      <aside className="min-h-0 overflow-y-auto border-s border-dash-border bg-dash-panel p-3">
        <h2 className="mb-2 text-sm font-extrabold">{t('flow.log')}</h2>
        {log.length === 0 && <p className="text-sm text-dash-text/60">{t(mode === 'live' ? 'flow.waiting' : 'flow.pressReplay')}</p>}
        <ul className="space-y-2">
          {log.map((l) => (
            <li key={l.key} className="rounded-lg border border-dash-border p-2 text-sm">
              <p className="flex gap-2 text-xs">
                <span className="text-dash-text/60">{l.time.toLocaleTimeString([], { hour12: false })}</span>
                <span className="font-extrabold" style={{ color: (AGENT_META[l.agent] ?? AGENT_META.orchestrator).color }}>
                  {(AGENT_META[l.agent] ?? AGENT_META.orchestrator).emoji} {t(`agent.${l.agent}`, { defaultValue: l.agent })}
                </span>
                <span className="ms-auto text-dash-text/50">{formatDistanceToNowStrict(l.time, { addSuffix: true })}</span>
              </p>
              <p>{l.message}</p>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}

export type { ActivityRow }
