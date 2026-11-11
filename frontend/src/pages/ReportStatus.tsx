import { VideoBackdrop } from '@/components/VideoBackdrop'
import { useQuery } from '@tanstack/react-query'
import { Check, Copy, Home, Loader2, SearchX } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { LanguageToggle } from '@/components/LanguageToggle'
import { CallButtons } from '@/components/reporter/CallButtons'
import { CoachSheet } from '@/components/reporter/CoachSheet'
import { FirstAidCard } from '@/components/reporter/FirstAidCard'
import { ListenButton } from '@/components/reporter/ListenButton'
import { StatusTicks } from '@/components/reporter/StatusTicks'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useConfig } from '@/hooks/useConfig'
import { useDefaultLanguage } from '@/hooks/useDefaultLanguage'
import { useGeolocation } from '@/hooks/useGeolocation'
import { isLang } from '@/i18n'
import { ApiError, apiAuthedGet } from '@/lib/api'
import { reportStatus } from '@/lib/schemas'

const POLL_MS = 3000

/** Report Status (docs/09 section 3.2, F-15): polls every 3 s until the report is processed. */
export default function ReportStatus() {
  const { id = '' } = useParams()
  const { t, i18n } = useTranslation()
  const lang = isLang(i18n.language) ? i18n.language : 'en'
  const { coords } = useGeolocation()
  const { data: config } = useConfig(coords)
  useDefaultLanguage(config)
  const [copied, setCopied] = useState(false)

  const { data, error } = useQuery({
    queryKey: ['report-status', id],
    queryFn: () => apiAuthedGet(`/reports/${id}/status`, reportStatus),
    refetchInterval: POLL_MS,
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 3,
  })

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 p-8 text-center">
        <SearchX className="size-16 text-muted-foreground" />
        <p className="text-xl font-extrabold">{t('status.notFound')}</p>
        <Button asChild size="lg">
          <Link to="/">
            <Home /> {t('status.home')}
          </Link>
        </Button>
      </div>
    )
  }

  const acked = data?.services.some((s) => s.state === 'acknowledged') ?? false
  const headline = !data
    ? t('status.alerting')
    : data.report_status === 'failed'
      ? t('status.failed')
      : acked
        ? t('status.onTheWay')
        : data.incident
          ? t('status.alerting')
          : t('status.processing')

  const copy = async () => {
    if (!data?.incident) return
    try {
      await navigator.clipboard.writeText(data.incident.short_code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard can be blocked: the code is still shown on screen */
    }
  }

  const listen = [headline, ...(data?.services ?? []).map((s) => `${t(`status.${s.service}`)}: ${t(s.state === 'acknowledged' ? 'status.acknowledged' : 'status.alerted')}`), data?.first_aid[0]?.steps[0] ?? '']
    .filter(Boolean)
    .join('. ')

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 p-4 text-ink">
      <VideoBackdrop />
      <header className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="icon" className="size-12">
          <Link to="/" aria-label={t('status.home')}>
            <Home className="size-6" />
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <LanguageToggle only={config?.languages} />
          <ListenButton text={listen} />
        </div>
      </header>

      <section className={`rounded-2xl p-5 text-white ${acked ? 'bg-ack' : 'bg-info'}`} aria-live="polite">
        <div className="flex items-center gap-3">
          {!acked && data?.report_status !== 'failed' && <Loader2 className="size-8 shrink-0 animate-spin motion-reduce:animate-none" />}
          <p className="text-2xl font-extrabold leading-snug">{headline}</p>
        </div>
        {(data?.incident?.landmark_local ?? data?.incident?.landmark_text) && (
          <p className="mt-3 text-lg leading-snug" dir="auto">
            <span className="block text-sm font-semibold opacity-80">{t('landmark.heading')}</span>
            {lang === 'ur' ? (data?.incident?.landmark_local ?? data?.incident?.landmark_text) : (data?.incident?.landmark_text ?? data?.incident?.landmark_local)}
          </p>
        )}
        {data?.incident && (
          <button
            type="button"
            onClick={() => void copy()}
            className="mt-3 flex items-center gap-2 rounded-lg bg-white/20 px-3 py-2 text-lg font-extrabold"
            aria-label={t('status.code')}
          >
            {data.incident.short_code}
            {copied ? <Check className="size-5" /> : <Copy className="size-5" />}
          </button>
        )}
      </section>

      {!data ? (
        <Skeleton className="h-40 w-full rounded-xl" />
      ) : (
        <>
          {data.first_aid.length > 0 && <CoachSheet cards={data.first_aid} reportId={id} />}
          {data.services.length > 0 && <StatusTicks services={data.services} lang={lang} />}
          {data.first_aid.map((card) => (
            <FirstAidCard key={card.key} card={card} />
          ))}
          <p className="text-sm text-muted-foreground">{t('firstaid.disclaimer')}</p>
          {data.transcript && (
            <details className="rounded-xl border p-3">
              <summary className="cursor-pointer text-lg font-extrabold">{t('status.understood')}</summary>
              <p className="mt-2 text-lg">{data.transcript}</p>
            </details>
          )}
        </>
      )}

      <footer className="mt-auto space-y-3 pt-2">
        <CallButtons config={config} lang={lang} />
      </footer>
    </div>
  )
}
