import { formatDistanceToNowStrict } from 'date-fns'
import { EyeOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SEVERITY_BAR } from '@/lib/severity'
import type { IncidentRow, TargetRow } from '@/lib/schemas'
import { cn } from '@/lib/utils'

export type Bucket = 'active' | 'review' | 'closed'

export function bucketOf(i: IncidentRow): Bucket {
  if (i.status === 'closed' || i.status === 'dismissed') return 'closed'
  return i.status === 'review' ? 'review' : 'active'
}

function IncidentCard({
  incident,
  targets,
  selected,
  onSelect,
}: {
  incident: IncidentRow
  targets: TargetRow[]
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation()
  const acked = targets.filter((x) => x.status === 'acknowledged').length
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'flex w-full overflow-hidden rounded-lg border bg-dash-bg/60 text-start',
        selected ? 'border-info' : 'border-dash-border hover:border-dash-text/40',
      )}
    >
      <span className={cn('w-1 shrink-0', SEVERITY_BAR[incident.severity])} />
      <span className="min-w-0 flex-1 space-y-1 p-2.5">
        <span className="flex items-center gap-2">
          <span className="font-extrabold">{incident.short_code}</span>
          <Badge variant="outline" className="text-[11px]">{t(`incidentStatus.${incident.status}`)}</Badge>
          {incident.silent && <EyeOff className="size-4 text-medium" />}
          <span className="ms-auto text-xs text-dash-text/60">
            {formatDistanceToNowStrict(new Date(incident.created_at), { addSuffix: true })}
          </span>
        </span>
        <span className="block text-sm font-semibold">{t(`incidentType.${incident.incident_type}`)}</span>
        <span className="block truncate text-xs text-dash-text/70">{incident.location_label ?? '-'}</span>
        <span className="flex gap-3 text-xs text-dash-text/80">
          <span>×{incident.report_count}</span>
          <span>{Math.round(incident.confidence * 100)}%</span>
          {targets.length > 0 && <span>{acked}/{targets.length} ✅</span>}
        </span>
      </span>
    </button>
  )
}

export function IncidentList({
  incidents,
  targets,
  selectedId,
  onSelect,
  bucket,
  onBucket,
}: {
  incidents: IncidentRow[]
  targets: TargetRow[]
  selectedId: string | null
  onSelect: (id: string) => void
  bucket: Bucket
  onBucket: (b: Bucket) => void
}) {
  const { t } = useTranslation()
  const counts = { active: 0, review: 0, closed: 0 }
  incidents.forEach((i) => (counts[bucketOf(i)] += 1))
  const shown = incidents.filter((i) => bucketOf(i) === bucket)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Tabs value={bucket} onValueChange={(v) => onBucket(v as Bucket)} className="border-b border-dash-border p-2">
        <TabsList className="w-full">
          {(['active', 'review', 'closed'] as const).map((b) => (
            <TabsTrigger key={b} value={b} className="flex-1">
              {t(`dash.${b}`)} {counts[b] > 0 && <Badge className="ms-1 px-1.5">{counts[b]}</Badge>}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
        {shown.length === 0 && <p className="py-8 text-center text-sm text-dash-text/60">{t('dash.none')}</p>}
        {shown.map((i) => (
          <IncidentCard
            key={i.id}
            incident={i}
            targets={targets.filter((x) => x.incident_id === i.id)}
            selected={i.id === selectedId}
            onSelect={() => onSelect(i.id)}
          />
        ))}
      </div>
    </div>
  )
}
