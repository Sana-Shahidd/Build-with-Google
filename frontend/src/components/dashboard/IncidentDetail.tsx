import { useQuery, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNowStrict } from 'date-fns'
import { CheckCircle2, Clock } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { fetchEvents, fetchReports, incidentAction } from '@/lib/dashboard'
import { SEVERITY_BAR } from '@/lib/severity'
import type { AssignmentRow, IncidentRow, TargetRow } from '@/lib/schemas'
import { cn } from '@/lib/utils'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-extrabold uppercase tracking-wide text-dash-text/60">{title}</h3>
      {children}
    </section>
  )
}

/** Incident detail sheet (docs/09 section 3.9): facts, alert targets, assignments, reports, timeline. */
export function IncidentDetail({
  incident,
  targets,
  assignments,
  canAct,
  onClose,
}: {
  incident: IncidentRow | null
  targets: TargetRow[]
  assignments: AssignmentRow[]
  canAct: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const id = incident?.id ?? ''
  const reports = useQuery({ queryKey: ['reports', id], queryFn: () => fetchReports(id), enabled: !!incident, refetchInterval: 5000 })
  const events = useQuery({ queryKey: ['incident_events', id], queryFn: () => fetchEvents(id), enabled: !!incident, refetchInterval: 5000 })

  const act = async (action: 'verify' | 'dismiss' | 'close') => {
    if (!incident) return
    try {
      await incidentAction(incident.id, action, action === 'dismiss' ? { reason: t('dash.dismissReason') } : undefined)
      await queryClient.invalidateQueries({ queryKey: ['incidents'] })
    } catch {
      toast.error(t('dash.actionFailed'))
    }
  }

  const open = incident !== null
  const open_ = incident && incident.status !== 'closed' && incident.status !== 'dismissed'

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full max-w-[560px] gap-0 overflow-y-auto bg-dash-panel p-0 text-dash-text sm:max-w-[560px]">
        {incident && (
          <>
            <div className={cn('h-1.5', SEVERITY_BAR[incident.severity])} />
            <SheetHeader className="gap-2 p-4">
              <SheetTitle className="flex flex-wrap items-center gap-2 text-xl font-extrabold">
                {incident.short_code}
                <Badge>{t(`severity.${incident.severity}`)}</Badge>
                <Badge variant="outline">{t(`incidentStatus.${incident.status}`)}</Badge>
              </SheetTitle>
              <p className="text-sm">{t(`incidentType.${incident.incident_type}`)} · {incident.location_label ?? '-'}</p>
              {canAct && open_ && (
                <div className="flex flex-wrap gap-2">
                  {incident.status !== 'verified' && (
                    <Button size="sm" className="bg-ack text-white hover:bg-ack/90" onClick={() => void act('verify')}>
                      {t('dash.verify')}
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => void act('dismiss')}>{t('dash.dismiss')}</Button>
                  <Button size="sm" variant="outline" onClick={() => void act('close')}>{t('dash.close')}</Button>
                </div>
              )}
            </SheetHeader>

            <div className="space-y-5 p-4 pt-0">
              <Section title={t('dash.summary')}>
                <p className="text-sm">{incident.summary_en}</p>
                {incident.local_lang && incident.local_lang !== 'en' && incident.summary_local && (
                  <p className="text-sm" dir="auto">🌐 {incident.summary_local}</p>
                )}
                {(incident.landmark_text || incident.landmark_local) && (
                  <p className="text-sm" dir="auto">🧭 {incident.landmark_local ?? incident.landmark_text}</p>
                )}
              </Section>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-dash-text/60">{t('dash.casualties')}</p>
                  <p className="font-extrabold">{incident.est_casualties_min}–{incident.est_casualties_max}</p>
                </div>
                <div>
                  <p className="text-dash-text/60">{t('dash.confidence')}</p>
                  <p className="font-extrabold">{Math.round(incident.confidence * 100)}% · ×{incident.report_count}</p>
                  <Progress value={incident.confidence * 100} className="mt-1" />
                </div>
                <div className="col-span-2 flex flex-wrap gap-1">
                  {incident.injury_types.map((x) => <Badge key={x} variant="secondary">{t(`injury.${x}`)}</Badge>)}
                  {incident.needs.map((x) => <Badge key={x} variant="outline">{t(`need.${x}`)}</Badge>)}
                  {incident.ongoing_danger && <Badge variant="destructive">{t('dash.danger')}</Badge>}
                  {incident.silent && <Badge variant="destructive">{t('dash.silentReport')}</Badge>}
                </div>
              </div>

              <Section title={t('dash.targets')}>
                {targets.length === 0 ? <p className="text-sm text-dash-text/60">-</p> : (
                  <Table>
                    <TableHeader>
                      <TableRow><TableHead>{t('dash.recipient')}</TableHead><TableHead>{t('dash.status')}</TableHead></TableRow>
                    </TableHeader>
                    <TableBody>
                      {targets.map((x) => (
                        <TableRow key={x.id}>
                          <TableCell>{x.recipient_label}{x.is_standby && <span className="text-xs text-medium"> · {t('dash.standby')}</span>}</TableCell>
                          <TableCell>
                            {x.status === 'acknowledged' ? (
                              <span className="flex items-center gap-1 text-ack"><CheckCircle2 className="size-4" /> {t('targetStatus.acknowledged')}{x.acknowledged_via && ` (${x.acknowledged_via})`}</span>
                            ) : (
                              <span className="flex items-center gap-1 text-dash-text/70"><Clock className="size-4" /> {t(`targetStatus.${x.status}`)}</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Section>

              <Section title={t('dash.assignments')}>
                {assignments.length === 0 ? <p className="text-sm text-dash-text/60">-</p> : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('dash.hospital')}</TableHead><TableHead>{t('dash.patients')}</TableHead>
                        <TableHead>{t('dash.criticalCount')}</TableHead><TableHead>{t('dash.eta')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {assignments.map((a) => (
                        <TableRow key={a.id}>
                          <TableCell>{a.organizations?.name}{a.over_capacity && <span className="text-xs text-medium"> · {t('dash.overCapacity')}</span>}</TableCell>
                          <TableCell>{a.assigned_casualties}</TableCell>
                          <TableCell>{a.critical}</TableCell>
                          <TableCell>{a.eta_minutes != null ? `${Math.round(a.eta_minutes)} min` : '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Section>

              <Section title={t('dash.reportsList')}>
                {reports.data?.length === 0 && <p className="text-sm text-dash-text/60">{t('dash.noReports')}</p>}
                <ul className="space-y-2">
                  {reports.data?.map((r) => (
                    <li key={r.id} className="rounded-lg border border-dash-border p-2 text-sm">
                      <p className="flex gap-2 text-xs text-dash-text/60">
                        <span>{r.input_type}</span>
                        <span>{r.ai_provider ?? '-'}</span>
                        {r.ai_confidence != null && <span>{Math.round(r.ai_confidence * 100)}%</span>}
                        <span className="ms-auto">{formatDistanceToNowStrict(new Date(r.created_at), { addSuffix: true })}</span>
                      </p>
                      <p dir="auto">{r.transcript ?? r.raw_text ?? '(SOS)'}</p>
                    </li>
                  ))}
                </ul>
              </Section>

              <Section title={t('dash.timeline')}>
                <ul className="space-y-1 text-sm">
                  {events.data?.map((e) => (
                    <li key={e.id} className="flex gap-2">
                      <span className="shrink-0 text-xs text-dash-text/60">
                        {new Date(e.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                      <span>{e.message}</span>
                    </li>
                  ))}
                </ul>
              </Section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
