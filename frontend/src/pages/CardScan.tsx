import { VideoBackdrop } from '@/components/VideoBackdrop'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Droplet, Phone, Siren } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { LanguageToggle } from '@/components/LanguageToggle'
import { CallButtons } from '@/components/reporter/CallButtons'
import { ListenButton } from '@/components/reporter/ListenButton'
import { SafetyPromise } from '@/components/reporter/SafetyPromise'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { getLocation } from '@/hooks/useGeolocation'
import { chooseLang, isLang } from '@/i18n'
import { ApiError, apiAuthedPostJson, apiGet } from '@/lib/api'
import { alertCreated, publicCard } from '@/lib/schemas'

/** Public scan page (F-36): what a stranger sees. Name, blood group, allergy, family, Get help. */
export default function CardScan() {
  const { token = '' } = useParams()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const card = useQuery({
    queryKey: ['public-card', token],
    queryFn: () => apiGet(`/public/card/${token}`, publicCard),
    retry: false,
    staleTime: Infinity,
  })

  // Show the page in the card language first (the owner chose it for the people who will read it).
  useEffect(() => {
    if (card.data && isLang(card.data.lang)) chooseLang(card.data.lang)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [card.data?.lang])

  const help = useMutation({
    mutationFn: async () => {
      const where = await getLocation()
      return apiAuthedPostJson(
        `/public/card/${token}/alert`,
        { client_report_id: crypto.randomUUID(), ...(where ?? {}) },
        alertCreated,
      )
    },
    onSuccess: (r) => navigate(`/report/${r.report_id}`),
    onError: () => toast.error(t('report.failed')),
  })

  if (card.error instanceof ApiError && card.error.status === 404) {
    return <p className="p-8 text-center text-xl font-extrabold">{t('card.inactive')}</p>
  }
  const c = card.data
  const listen = c
    ? [c.full_name, c.blood_type ? `${t('card.bloodGroup')} ${c.blood_type}` : '', c.allergies ? `${t('card.allergy')} ${c.allergies}` : '', t('safety.promise')]
        .filter(Boolean)
        .join('. ')
    : ''

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 p-4 text-ink">
      <VideoBackdrop />
      <header className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold">{t('card.title')}</h1>
        <div className="flex items-center gap-2">
          <LanguageToggle />
          <ListenButton text={listen} />
        </div>
      </header>

      {!c ? (
        <Skeleton className="h-48 w-full rounded-xl" />
      ) : (
        <>
          <Card className="gap-2 p-5">
            <p className="text-4xl font-extrabold leading-tight">{c.full_name}</p>
            <p className="flex items-center gap-2 text-3xl font-extrabold text-sos">
              <Droplet className="size-8" /> {c.blood_type ?? t('card.dontKnow')}
            </p>
            <p className="text-xl">
              {t('card.allergy')} <b>{c.allergies ?? t('card.none')}</b>
            </p>
          </Card>

          <Button
            size="lg"
            disabled={help.isPending}
            onClick={() => help.mutate()}
            className="h-24 w-full bg-sos text-2xl font-extrabold text-white hover:bg-sos-dark"
          >
            <Siren className="size-9" /> {t('card.getHelp')}
          </Button>

          {c.contacts.map((contact) => (
            <Card key={contact.name} className="flex-row items-center gap-3 p-4">
              <div className="flex-1">
                <p className="text-xl font-extrabold">{contact.name}</p>
                {contact.relation && <p className="text-muted-foreground">{contact.relation}</p>}
              </div>
              {contact.phone && (
                <Button asChild size="lg" className="h-14 bg-ack text-white hover:bg-ack/90">
                  <a href={`tel:${contact.phone}`}>
                    <Phone /> {t('card.callFamily')}
                  </a>
                </Button>
              )}
            </Card>
          ))}

          <SafetyPromise />
          <CallButtons config={{ emergency_numbers: c.emergency_numbers } as never} lang={i18n.language} />
        </>
      )}
    </div>
  )
}
