import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  BookOpen,
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  Headphones,
  Home,
  Keyboard,
  LogOut,
  MapPin,
  Mic,
  Phone,
  ShieldCheck,
  Workflow,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'
import { toast } from 'sonner'
import { LanguageToggle } from '@/components/LanguageToggle'
import { AgentActivityFeed } from '@/components/dashboard/AgentActivityFeed'
import { AgentLights } from '@/components/dashboard/AgentLights'
import { IncidentDetail } from '@/components/dashboard/IncidentDetail'
import { IncidentList, bucketOf, type Bucket } from '@/components/dashboard/IncidentList'
import { IncidentMap } from '@/components/dashboard/IncidentMap'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useRealtimeTables } from '@/hooks/useRealtimeTable'
import { useRole } from '@/hooks/useRole'
import { fetchActivity, fetchAssignments, fetchIncidents, fetchOrgs, fetchTargets } from '@/lib/dashboard'
import type { IncidentRow } from '@/lib/schemas'
import { supabase } from '@/lib/supabase'
import { cn } from '@/lib/utils'

const TABLES = ['incidents', 'alert_targets', 'hospital_assignments', 'agent_activity', 'incident_events']
const SAFETY_POLL_MS = 5000
const card = 'rounded-2xl border border-[#2F7FB8]/15 bg-white/85 shadow-sm backdrop-blur'

/** Average seconds between two timestamp columns over the incidents that have both. */
function avgSeconds(rows: IncidentRow[], from: 'created_at' | 'first_alert_at', to: 'first_alert_at' | 'first_ack_at') {
  const diffs = rows
    .filter((r) => r[from] && r[to])
    .map((r) => (new Date(String(r[to])).getTime() - new Date(String(r[from])).getTime()) / 1000)
    .filter((s) => s >= 0)
  return diffs.length ? diffs.reduce((a, b) => a + b, 0) / diffs.length : null
}

function Kpi({ icon, tone, value, label }: { icon: React.ReactNode; tone: string; value: string; label: string }) {
  return (
    <div className={cn(card, 'flex items-center gap-3 p-3')}>
      <span className={cn('grid size-10 shrink-0 place-items-center rounded-full', tone)}>{icon}</span>
      <div className="min-w-0">
        <p className="text-xl font-extrabold leading-tight">{value}</p>
        <p className="truncate text-xs text-[#4F6E84]">{label}</p>
      </div>
    </div>
  )
}

function NavLink({ href, icon, label, active }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <a
      href={href}
      className={cn(
        'flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold',
        active ? 'bg-[#CFE6F6] text-[#12324A]' : 'text-[#4F6E84] hover:bg-[#E3F1FA]',
      )}
    >
      {icon} {label}
    </a>
  )
}

/** Dispatcher / responder dashboard (docs/09 section 3.8) in the light-blue + cream design. */
export default function Dashboard() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const role = useRole()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [bucket, setBucket] = useState<Bucket>('active')
  const [clock, setClock] = useState(() => new Date())

  useEffect(() => {
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const live = useRealtimeTables(TABLES, (table, row) => {
    if (table === 'incidents') toast(t('dash.newIncident', { code: String(row.short_code ?? '') }))
  })

  const enabled = !!role.data
  const poll = { refetchInterval: SAFETY_POLL_MS, enabled }
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: fetchIncidents, ...poll })
  const targets = useQuery({ queryKey: ['alert_targets'], queryFn: fetchTargets, ...poll })
  const assignments = useQuery({ queryKey: ['hospital_assignments'], queryFn: fetchAssignments, ...poll })
  const activity = useQuery({ queryKey: ['agent_activity'], queryFn: fetchActivity, ...poll })
  const orgs = useQuery({ queryKey: ['organizations'], queryFn: fetchOrgs, enabled, staleTime: 5 * 60_000 })

  const stats = useMemo(() => {
    const all = incidents.data ?? []
    const alerted = all.filter((i) => i.first_alert_at)
    const acked = alerted.filter((i) => i.first_ack_at)
    const toAlert = avgSeconds(all, 'created_at', 'first_alert_at')
    return {
      active: all.filter((i) => bucketOf(i) !== 'closed').length,
      toAlert,
      ackRate: alerted.length ? Math.round((acked.length / alerted.length) * 100) : null,
      reports: all.reduce((n, i) => n + i.report_count, 0),
    }
  }, [incidents.data])

  if (role.isPending) return <Skeleton className="m-8 h-40" />
  if (!role.data) return <Navigate to="/login" replace />
  if (role.data.role === 'admin') return <Navigate to="/control-room" replace /> // control room has no dispatcher access

  const selected = incidents.data?.find((i) => i.id === selectedId) ?? null
  const signOut = async () => {
    await supabase.auth.signOut()
    queryClient.clear()
  }
  const alertTime =
    stats.toAlert == null ? '-' : stats.toAlert < 90 ? t('dash.seconds', { n: Math.round(stats.toAlert) }) : t('dash.minutes', { n: Math.round(stats.toAlert / 60) })

  return (
    <div className="min-h-dvh bg-[#F4F8FC] text-[#12324A]">
      {/* Header: video background, wave cut-out at the bottom */}
      <header className="relative isolate overflow-hidden rounded-b-[2rem] text-white">
        <video className="absolute inset-0 z-0 size-full object-cover" src="/headervideo.mp4" autoPlay muted loop playsInline />
        <div className="absolute inset-0 z-0 bg-gradient-to-r from-[#0B2A4A]/70 via-[#12406B]/20 to-transparent" />
        <div className="relative z-10 mx-auto flex max-w-[1500px] flex-wrap items-start justify-between gap-4 px-5 pt-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className="size-9 text-[#F2C14E]" strokeWidth={1.6} />
            <div>
              <h1 className="text-xl font-extrabold leading-tight">{t('app.name')}</h1>
              <p className="text-[11px] text-white/80">{t('dash.tagline')}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-[#12324A] shadow [&_button]:h-7 [&_button]:px-2 [&_button]:text-xs">
            <span className={cn('flex items-center gap-1.5', live === 'live' ? 'text-ack' : live === 'offline' ? 'text-escalated' : 'text-medium')}>
              <span className="size-2.5 rounded-full bg-current" /> {t(`dash.${live}`)}
            </span>
            <span className="font-mono tabular-nums">{clock.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            <LanguageToggle />
            <Badge variant="outline">{role.data.role}</Badge>
            <Button size="sm" variant="ghost" onClick={() => void signOut()} aria-label={t('dash.signOut')}>
              <LogOut />
            </Button>
          </div>
        </div>
        <div className="relative z-10 mx-auto flex max-w-[1500px] flex-wrap items-end justify-between gap-4 px-5 pb-8 pt-3">
          <div className="max-w-xl">
            <p className="text-2xl font-extrabold leading-tight md:text-3xl">
              {t('dash.heroTitle1')}
              <br />
              {t('dash.heroTitle2')}
            </p>
            <p className="mt-2 text-sm text-white/90">{t('dash.heroSub')}</p>
          </div>
          <div className="space-y-2">
            <Link to="/" className="flex items-center gap-3 rounded-full bg-white p-2 pe-4 text-[#12324A] shadow-xl">
              <span className="grid size-10 place-items-center rounded-full bg-sos text-white">
                <Phone className="size-5" />
              </span>
              <span>
                <span className="block text-base font-extrabold">{t('dash.reportEmergency')}</span>
                <span className="block text-xs text-[#4F6E84]">{t('dash.tapToStart')}</span>
              </span>
              <ArrowRight className="ms-3 size-7 rounded-full bg-sos/10 p-1.5 text-sos" />
            </Link>
            <div className="flex justify-center gap-5 text-xs font-medium">
              <Link to="/" className="flex items-center gap-1.5"><Mic className="size-4" /> {t('dash.voiceReport')}</Link>
              <Link to="/" className="flex items-center gap-1.5"><Keyboard className="size-4" /> {t('dash.textReport')}</Link>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-5 px-5 py-5 lg:grid-cols-[150px_1fr]">
        <aside className="hidden space-y-1 lg:block">
          <nav className="space-y-1">
            <NavLink href="#top" icon={<Home className="size-5" />} label={t('dash.homeNav')} active />
            <NavLink href="#map" icon={<MapPin className="size-5" />} label={t('dash.liveMapNav')} />
            <NavLink href="#activity" icon={<Activity className="size-5" />} label={t('dash.feedNav')} />
            <Link to="/flow" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-[#4F6E84] hover:bg-[#E3F1FA]">
              <Workflow className="size-5" /> {t('dash.flowNav')}
            </Link>
            <Link to="/guide" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-[#4F6E84] hover:bg-[#E3F1FA]">
              <BookOpen className="size-5" /> {t('dash.guideNav')}
            </Link>
          </nav>
          <a href="tel:1122" className="mt-8 flex items-center gap-2 rounded-2xl bg-[#E3F1FA] p-3 text-xs">
            <Headphones className="size-7 shrink-0" />
            <span>
              <span className="block font-bold">{t('dash.needHelp')}</span>
              <span className="text-[#2F7FB8]">{t('dash.callRescue')}</span>
            </span>
          </a>
        </aside>

        <main id="top" className="min-w-0 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi icon={<AlertTriangle className="size-6 text-sos" />} tone="bg-sos/10" value={String(stats.active)} label={t('dash.kpiActive')} />
            <Kpi icon={<Clock className="size-6 text-[#2F7FB8]" />} tone="bg-[#CFE6F6]" value={alertTime} label={t('dash.kpiAlert')} />
            <Kpi icon={<CheckCircle2 className="size-6 text-ack" />} tone="bg-ack/15" value={stats.ackRate == null ? '-' : `${stats.ackRate}%`} label={t('dash.kpiAck')} />
            <Kpi icon={<FileText className="size-6 text-[#6D4FD6]" />} tone="bg-[#E9E3FA]" value={String(stats.reports)} label={t('dash.kpiReports')} />
          </div>

          <AgentLights rows={activity.data ?? []} />

          <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
            <section id="map" className={cn(card, 'flex h-[400px] flex-col overflow-hidden')}>
              <h2 className="flex items-center gap-2 border-b border-[#2F7FB8]/10 px-4 py-3 font-extrabold">
                <MapPin className="size-5" /> {t('dash.liveMapTitle')}
              </h2>
              <div className="min-h-0 flex-1">
                <IncidentMap
                  incidents={incidents.data ?? []}
                  orgs={orgs.data ?? []}
                  assignments={assignments.data ?? []}
                  targets={targets.data ?? []}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              </div>
            </section>
            <section className={cn(card, 'flex h-[400px] flex-col overflow-hidden')}>
              <h2 className="flex items-center gap-2 border-b border-[#2F7FB8]/10 px-4 py-3 font-extrabold">
                <Activity className="size-5 text-sos" /> {t('dash.liveIncidents')}
              </h2>
              <div className="min-h-0 flex-1">
                <IncidentList
                  incidents={incidents.data ?? []}
                  targets={targets.data ?? []}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  bucket={bucket}
                  onBucket={setBucket}
                />
              </div>
            </section>
          </div>

          <section id="activity" className={cn(card, 'flex h-[300px] flex-col overflow-hidden')}>
            <div className="min-h-0 flex-1">
              <AgentActivityFeed rows={activity.data ?? []} selectedId={selectedId} />
            </div>
          </section>

          <div className="flex items-center gap-4 rounded-2xl bg-gradient-to-r from-[#D6E8F8] to-[#EAF4FB] px-5 py-4">
            <ShieldCheck className="size-9 shrink-0 text-[#2F7FB8]" />
            <p>
              <span className="font-bold">{t('dash.safetyTitle')}</span> {t('dash.safetyBody')}
            </p>
          </div>
        </main>
      </div>

      <IncidentDetail
        incident={selected}
        targets={(targets.data ?? []).filter((x) => x.incident_id === selectedId)}
        assignments={(assignments.data ?? []).filter((a) => a.incident_id === selectedId)}
        canAct={role.data.role === 'dispatcher'}
        onClose={() => setSelectedId(null)}
      />
    </div>
  )
}
