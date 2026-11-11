import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, LogOut, MonitorCheck } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'
import { LanguageToggle } from '@/components/LanguageToggle'
import { AgentActivityFeed } from '@/components/dashboard/AgentActivityFeed'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useRole } from '@/hooks/useRole'
import { AGENT_META, LIGHT_AGENTS } from '@/lib/agents'
import { supabase } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import { fetchActivityLarge } from '@/lib/dashboard'
import type { ActivityRow } from '@/lib/schemas'

const card = 'rounded-2xl border border-[#2F7FB8]/15 bg-white/90 shadow-sm'
const REVIEW_KINDS = ['guardrail_block', 'error', 'fallback']
const STORAGE_KEY = 'gm-reviewed-activity'

type Health = 'healthy' | 'degraded' | 'attention' | 'idle'
const HEALTH_STYLE: Record<Health, string> = {
  healthy: 'bg-ack/15 text-ack',
  degraded: 'bg-medium/20 text-[#8A6A00]',
  attention: 'bg-escalated/15 text-escalated',
  idle: 'bg-[#E3F1FA] text-[#4F6E84]',
}

function loadReviewed(): Set<number> {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as number[])
  } catch {
    return new Set()
  }
}

function agentStats(rows: ActivityRow[], agent: string) {
  const mine = rows.filter((r) => r.agent === agent)
  const count = (k: string) => mine.filter((r) => r.kind === k).length
  const decisions = count('decision')
  const autopilot = count('rule') + count('fallback')
  const blocks = count('guardrail_block')
  const errors = count('error')
  const lat = mine.map((r) => r.latency_ms).filter((n): n is number => n != null)
  const health: Health =
    mine.length === 0 ? 'idle' : errors > 0 || blocks > 0 ? 'attention' : autopilot > decisions ? 'degraded' : 'healthy'
  return {
    mine,
    decisions,
    autopilot,
    blocks,
    errors,
    avgMs: lat.length ? Math.round(lat.reduce((a, b) => a + b, 0) / lat.length) : null,
    model: mine.find((r) => r.model)?.model?.split(':').pop() ?? '-',
    last: mine[0]?.created_at ?? null,
    health,
  }
}

/** Control Room (admin login): humans check that every agent works correctly. */
export default function ControlRoom() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const role = useRole()
  const [reviewed, setReviewed] = useState<Set<number>>(loadReviewed)
  const [showReviewed, setShowReviewed] = useState(false)
  const activity = useQuery({
    queryKey: ['agent_activity_large'],
    queryFn: fetchActivityLarge,
    refetchInterval: 5000,
    enabled: role.data?.role === 'admin',
  })
  const rows = useMemo(() => activity.data ?? [], [activity.data])
  const stats = useMemo(() => LIGHT_AGENTS.map((a) => [a, agentStats(rows, a)] as const), [rows])
  const queue = rows.filter((r) => REVIEW_KINDS.includes(r.kind) && (showReviewed || !reviewed.has(r.id))).slice(0, 40)

  if (role.isPending) return <Skeleton className="m-8 h-40" />
  if (!role.data || role.data.role !== 'admin') return <Navigate to="/login" replace />

  const toggle = (id: number) => {
    const next = new Set(reviewed)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setReviewed(next)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...next]))
    } catch {
      /* private mode: marks last for this visit only */
    }
  }
  const signOut = async () => {
    await supabase.auth.signOut()
    queryClient.clear()
  }
  const total = (k: 'decisions' | 'autopilot' | 'blocks' | 'errors') => stats.reduce((n, [, s]) => n + s[k], 0)

  return (
    <div className="min-h-dvh bg-[#F4F8FC] text-[#12324A]">
      <header className="border-b border-[#2F7FB8]/15 bg-white/80 px-5 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
          <MonitorCheck className="size-6 text-[#6D4FD6]" />
          <div>
            <h1 className="text-lg font-extrabold leading-tight">{t('control.title')}</h1>
            <p className="text-xs text-[#4F6E84]">{t('control.subtitle')}</p>
          </div>
          <div className="ms-auto flex items-center gap-2">
            <Button asChild size="sm" variant="outline">
              <Link to="/guide"><BookOpen /> {t('dash.guideNav')}</Link>
            </Button>
            <LanguageToggle />
            <Button size="sm" variant="ghost" onClick={() => void signOut()} aria-label={t('dash.signOut')}>
              <LogOut />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-5 py-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {([['decisions', 'text-[#2F7FB8]'], ['autopilot', 'text-[#8A6A00]'], ['blocks', 'text-escalated'], ['errors', 'text-escalated']] as const).map(([k, tone]) => (
            <div key={k} className={cn(card, 'p-4')}>
              <p className={cn('text-3xl font-extrabold', tone)}>{total(k)}</p>
              <p className="text-sm text-[#4F6E84]">{t(`control.${k}`)}</p>
            </div>
          ))}
        </div>

        <section className={cn(card, 'overflow-x-auto')}>
          <h2 className="border-b border-[#2F7FB8]/10 px-4 py-3 font-extrabold">{t('control.agentHealth')}</h2>
          <table className="w-full min-w-[760px] text-sm">
            <thead className="text-start text-xs uppercase text-[#4F6E84]">
              <tr className="[&>th]:px-4 [&>th]:py-2 [&>th]:text-start">
                <th>Agent</th>
                <th>Status</th>
                <th>{t('control.decisions')}</th>
                <th>{t('control.autopilot')}</th>
                <th>{t('control.blocks')}</th>
                <th>{t('control.errors')}</th>
                <th>{t('control.latency')}</th>
                <th>{t('control.lastModel')}</th>
                <th>{t('control.lastSeen')}</th>
              </tr>
            </thead>
            <tbody>
              {stats.map(([agent, s]) => (
                <tr key={agent} className="border-t border-[#2F7FB8]/10 [&>td]:px-4 [&>td]:py-2.5">
                  <td className="font-bold">{AGENT_META[agent].emoji} {t(`agent.${agent}`)}</td>
                  <td>
                    <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-bold', HEALTH_STYLE[s.health])}>{t(`control.${s.health}`)}</span>
                  </td>
                  <td>{s.decisions}</td>
                  <td>{s.autopilot}</td>
                  <td>{s.blocks}</td>
                  <td>{s.errors}</td>
                  <td>{s.avgMs == null ? '-' : `${(s.avgMs / 1000).toFixed(1)} s`}</td>
                  <td className="max-w-[160px] truncate">{s.model}</td>
                  <td className="whitespace-nowrap">{s.last ? new Date(s.last).toLocaleTimeString([], { hour12: false }) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className={cn(card, 'p-4')}>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-extrabold">{t('control.reviewQueue')}</h2>
            <label className="ms-auto flex items-center gap-2 text-sm">
              <input type="checkbox" checked={showReviewed} onChange={(e) => setShowReviewed(e.target.checked)} /> {t('control.showReviewed')}
            </label>
          </div>
          <p className="mt-1 text-sm text-[#4F6E84]">{t('control.reviewHelp')}</p>
          <ul className="mt-3 space-y-2">
            {queue.length === 0 && <li className="py-6 text-center text-sm text-[#4F6E84]">{t('control.queueEmpty')}</li>}
            {queue.map((r) => (
              <li key={r.id} className={cn('flex items-center gap-3 rounded-xl border border-[#2F7FB8]/15 p-3 text-sm', reviewed.has(r.id) && 'opacity-60')}>
                <span className="text-lg">{r.kind === 'guardrail_block' ? '🛡' : r.kind === 'error' ? '⚠' : '⚙'}</span>
                <span className="min-w-0 flex-1">
                  <span className="font-bold">{AGENT_META[r.agent]?.emoji} {t(`agent.${r.agent}`)}</span>
                  <span className="ms-2 text-[#4F6E84]">{new Date(r.created_at).toLocaleTimeString([], { hour12: false })}</span>
                  <span className="block truncate">{r.message}</span>
                </span>
                <label className="flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold">
                  <input type="checkbox" checked={reviewed.has(r.id)} onChange={() => toggle(r.id)} /> {t('control.reviewed')}
                </label>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-[#4F6E84]">{t('control.reviewNote')}</p>
        </section>

        <section className={cn(card, 'flex h-[420px] flex-col overflow-hidden')}>
          <AgentActivityFeed rows={rows} selectedId={null} />
        </section>
      </main>
    </div>
  )
}
