import { formatDistanceToNowStrict } from 'date-fns'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { AGENT_META, KIND_ICON } from '@/lib/agents'
import type { ActivityRow } from '@/lib/schemas'

function modelChip(model: string | null): string {
  if (!model) return 'autopilot'
  const id = model.includes(':') ? model.split(':')[1] : model
  return id.replace('gemini-', 'gemini ').slice(0, 22)
}

/** Live feed of agent activity (F-33): newest first, max 200 rows, filter chips. */
export function AgentActivityFeed({ rows, selectedId }: { rows: ActivityRow[]; selectedId: string | null }) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<'all' | 'incident'>('all')
  const shown = filter === 'incident' && selectedId ? rows.filter((r) => r.incident_id === selectedId) : rows

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-dash-border p-3">
        <h2 className="flex-1 text-sm font-extrabold">{t('dash.feed')}</h2>
        <Button size="sm" variant={filter === 'all' ? 'default' : 'outline'} onClick={() => setFilter('all')}>
          {t('dash.filterAll')}
        </Button>
        <Button
          size="sm"
          variant={filter === 'incident' ? 'default' : 'outline'}
          disabled={!selectedId}
          onClick={() => setFilter('incident')}
        >
          {t('dash.filterIncident')}
        </Button>
      </div>
      <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {shown.length === 0 && <li className="py-8 text-center text-sm text-dash-text/60">{t('dash.noActivity')}</li>}
        {shown.map((row) => {
          const meta = AGENT_META[row.agent] ?? AGENT_META.orchestrator
          return (
            <li key={row.id} className="rounded-lg border border-dash-border bg-dash-bg/60 p-2.5">
              <p className="flex flex-wrap items-center gap-x-2 text-xs">
                <span className="font-extrabold" style={{ color: meta.color }}>
                  {meta.emoji} {t(`agent.${row.agent}`, { defaultValue: row.agent })}
                </span>
                <span>{KIND_ICON[row.kind] ?? '•'} {row.kind}</span>
                <span className="rounded bg-[#2F7FB8]/15 px-1.5">{modelChip(row.model)}</span>
                <span className="ms-auto text-dash-text/60">
                  {formatDistanceToNowStrict(new Date(row.created_at), { addSuffix: true })}
                </span>
              </p>
              <p className="mt-1 text-sm leading-snug">{row.message}</p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
