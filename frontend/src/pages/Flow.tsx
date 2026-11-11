import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Play, Radio } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'
import { LanguageToggle } from '@/components/LanguageToggle'
import { LiveFlow, type FlowMode } from '@/components/flow/LiveFlow'
import { Button } from '@/components/ui/button'
import { useRole } from '@/hooks/useRole'
import { fetchIncidents } from '@/lib/dashboard'
import { cn } from '@/lib/utils'

/** Live Flow (F-46): judge-facing architecture view, dispatcher/admin only. */
export default function Flow() {
  const { t } = useTranslation()
  const role = useRole()
  const [mode, setMode] = useState<FlowMode>('live')
  const [incidentId, setIncidentId] = useState<string | null>(null)
  const [speed, setSpeed] = useState(1)
  const [nonce, setNonce] = useState(0)
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: fetchIncidents, enabled: !!role.data })

  if (role.isPending) return null
  if (!role.data || role.data.role !== 'dispatcher') return <Navigate to="/login" replace />

  return (
    <div className="flex h-dvh flex-col bg-dash-bg text-dash-text">
      <header className="flex flex-wrap items-center gap-3 border-b border-dash-border bg-dash-panel px-4 py-2">
        <Button asChild size="icon" variant="ghost">
          <Link to="/dashboard" aria-label={t('dash.title')}>
            <ArrowLeft />
          </Link>
        </Button>
        <h1 className="text-lg font-extrabold">{t('flow.title')}</h1>

        <div className="flex gap-1">
          <Button size="sm" variant={mode === 'live' ? 'default' : 'outline'} onClick={() => setMode('live')}>
            <Radio /> {t('flow.live')}
          </Button>
          <Button size="sm" variant={mode === 'replay' ? 'default' : 'outline'} onClick={() => setMode('replay')}>
            {t('flow.replay')}
          </Button>
        </div>

        <select
          aria-label={t('flow.incident')}
          value={incidentId ?? ''}
          onChange={(e) => setIncidentId(e.target.value || null)}
          className="h-9 rounded-md border border-dash-border bg-dash-bg px-2 text-sm"
        >
          <option value="">{t('flow.allIncidents')}</option>
          {incidents.data?.map((i) => (
            <option key={i.id} value={i.id}>
              {i.short_code} · {t(`incidentType.${i.incident_type}`)}
            </option>
          ))}
        </select>

        {mode === 'replay' && (
          <>
            <div className="flex gap-1">
              {[1, 4].map((s) => (
                <Button key={s} size="sm" variant={speed === s ? 'default' : 'outline'} onClick={() => setSpeed(s)}>
                  ×{s}
                </Button>
              ))}
            </div>
            <Button size="sm" className={cn('bg-ack text-white hover:bg-ack/90')} disabled={!incidentId} onClick={() => setNonce((n) => n + 1)}>
              <Play /> {t('flow.play')}
            </Button>
          </>
        )}
        <span className="ms-auto">
          <LanguageToggle />
        </span>
      </header>
      <LiveFlow mode={mode} incidentId={incidentId} speed={speed} replayNonce={nonce} />
    </div>
  )
}
