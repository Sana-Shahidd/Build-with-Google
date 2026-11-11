import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Inbox, LinkIcon, MapPin, Radio, Siren } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { chooseLang, isLang, LANGS, savedLang } from '@/i18n'
import { ApiError, apiGet, apiPost } from '@/lib/api'
import { ackResult, responderInbox, type ResponderAlert } from '@/lib/schemas'
import { cn } from '@/lib/utils'

const POLL_MS = 3000

const SEVERITY_BAR: Record<string, string> = {
  low: 'bg-low',
  medium: 'bg-medium',
  high: 'bg-high',
  critical: 'bg-critical',
}

function AlertCard({ alert, lang }: { alert: ResponderAlert; lang: 'en' | 'es' | 'ur' }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const acked = alert.state === 'acknowledged'
  const ack = useMutation({
    mutationFn: () => apiPost(`/ack/${alert.ack_token}`, ackResult),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['responder'] }),
    onError: () => toast.error(t('responder.ackFailed')),
  })
  const [headline, ...rest] = alert.text[lang]
  const time = alert.acknowledged_at
    ? new Date(alert.acknowledged_at).toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <Card className="gap-0 overflow-hidden p-0">
      <div className={cn('h-2', SEVERITY_BAR[alert.incident.severity])} />
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-lg font-extrabold leading-snug">{headline}</p>
          {alert.kind === 'standby' && <Badge variant="secondary">{t('responder.standby')}</Badge>}
        </div>
        <ul className="space-y-1.5 text-base">
          {rest.slice(0, -1).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        {alert.incident.map_url && (
          <Button asChild variant="outline" size="lg" className="h-12 w-full">
            <a href={alert.incident.map_url} target="_blank" rel="noreferrer">
              <MapPin /> {t('responder.openMap')}
            </a>
          </Button>
        )}
        {acked ? (
          <div className="flex items-center gap-3 rounded-xl bg-ack/10 p-4 text-ack">
            <CheckCircle2 className="size-8 shrink-0" />
            <div>
              <p className="text-lg font-extrabold">{t('responder.acked')}</p>
              <p className="text-sm">{t('responder.ackedAt', { time })}</p>
            </div>
          </div>
        ) : (
          <Button
            size="lg"
            disabled={ack.isPending || !alert.ack_token}
            onClick={() => ack.mutate()}
            className="h-20 w-full rounded-xl bg-ack text-xl font-extrabold text-white hover:bg-ack/90"
          >
            <CheckCircle2 className="size-8" />
            {ack.isPending ? t('responder.sending') : t('responder.ack')}
          </Button>
        )}
      </div>
    </Card>
  )
}

function LinkProblem({ expired }: { expired: boolean }) {
  const { t } = useTranslation()
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 p-8 text-center">
      <LinkIcon className="size-14 text-muted-foreground" />
      <p className="text-xl font-extrabold">{expired ? t('responder.expired') : t('responder.invalid')}</p>
      <p className="text-muted-foreground">{t('responder.askNew')}</p>
    </div>
  )
}

export default function Responder() {
  const { token = '' } = useParams()
  const { t, i18n } = useTranslation()
  const { data, error, isPending } = useQuery({
    queryKey: ['responder', token],
    queryFn: () => apiGet(`/responder/${token}`, responderInbox),
    refetchInterval: POLL_MS,
    retry: (count, err) => !(err instanceof ApiError && [404, 410].includes(err.status)) && count < 3,
  })

  // First visit: use the organization's language unless the person already chose one.
  useEffect(() => {
    if (data && !savedLang() && isLang(data.org.lang)) void i18n.changeLanguage(data.org.lang)
  }, [data, i18n])

  const lang = isLang(i18n.language) ? i18n.language : 'en'
  const linkError = error instanceof ApiError && [404, 410].includes(error.status) ? error : null

  return (
    <div className="min-h-dvh bg-surface text-ink">
      <header className="sticky top-0 z-10 flex items-center justify-between gap-2 border-b bg-surface px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-lg font-extrabold">{data?.org.name ?? t('responder.title')}</p>
          <p className="flex items-center gap-1 text-sm text-ack">
            <Radio className="size-4" /> {t('responder.live')}
          </p>
        </div>
        <div className="flex gap-1">
          {LANGS.map((code) => (
            <Button
              key={code}
              size="sm"
              variant={lang === code ? 'default' : 'outline'}
              onClick={() => chooseLang(code)}
            >
              {t(`lang.${code}`)}
            </Button>
          ))}
        </div>
      </header>

      <main className="mx-auto max-w-md space-y-4 p-4">
        {linkError ? (
          <LinkProblem expired={linkError.status === 410} />
        ) : isPending ? (
          <Skeleton className="h-64 w-full rounded-xl" />
        ) : (
          <>
            {error && (
              <p className="flex items-center gap-2 text-sm text-escalated">
                <AlertTriangle className="size-4" /> {t('responder.offline')}
              </p>
            )}
            {data?.alerts.length === 0 && (
              <div className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
                <Inbox className="size-14" />
                <p className="text-xl font-extrabold text-ink">{t('responder.empty')}</p>
                <p>{t('responder.keepOpen')}</p>
              </div>
            )}
            {data?.alerts.map((alert) => (
              <AlertCard key={alert.target_id} alert={alert} lang={lang} />
            ))}
          </>
        )}
      </main>
      {data && data.alerts.some((a) => a.state !== 'acknowledged') && (
        <div className="pointer-events-none fixed inset-x-0 bottom-3 flex justify-center">
          <Siren className="size-6 animate-pulse text-sos" />
        </div>
      )}
    </div>
  )
}
