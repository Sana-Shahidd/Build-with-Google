import { BookOpen, IdCard, MapPin } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { VideoBackdrop } from '@/components/VideoBackdrop'
import { LanguageToggle } from '@/components/LanguageToggle'
import { Button } from '@/components/ui/button'
import { CallButtons } from '@/components/reporter/CallButtons'
import { HoldToSpeak } from '@/components/reporter/HoldToSpeak'
import { ListenButton } from '@/components/reporter/ListenButton'
import { SafetyPromise } from '@/components/reporter/SafetyPromise'
import { SosButton } from '@/components/reporter/SosButton'
import { TextReportSheet } from '@/components/reporter/TextReportSheet'
import { useAnonSession } from '@/hooks/useAnonSession'
import { useConfig } from '@/hooks/useConfig'
import { useDefaultLanguage } from '@/hooks/useDefaultLanguage'
import { getLocation, useGeolocation, type Coords } from '@/hooks/useGeolocation'
import { isLang } from '@/i18n'
import type { Recording } from '@/lib/recorder'
import { sendReport } from '@/lib/reports'

/** Reporter Home (docs/09 section 3.1): picture-first, voice-first, nothing to type. */
export default function Home() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const lang = isLang(i18n.language) ? i18n.language : 'en'
  const { coords } = useGeolocation()
  const { data: config } = useConfig(coords)
  const session = useAnonSession()
  const [busy, setBusy] = useState(false)
  useDefaultLanguage(config)

  const submit = async (
    inputType: 'sos' | 'voice' | 'text',
    extra: { text?: string; audio?: Recording },
    where: Coords | null,
  ) => {
    setBusy(true)
    try {
      const created = await sendReport({ inputType, coords: where ?? coords, lang, ...extra })
      navigate(`/report/${created.report_id}`)
    } catch {
      toast.error(t('report.failed'))
      throw new Error('send failed')
    } finally {
      setBusy(false)
    }
  }

  // Voice and text ask for the location on the first interaction, then send with whatever we have.
  const withLocation = async (fn: (where: Coords | null) => Promise<void>) => fn(coords ?? (await getLocation()))

  const listen = [t('home.safetyTitle'), t('safety.promise'), t('sos.subtitle')].join('. ')

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 p-4 text-[#12324A]">
      <VideoBackdrop />
      <header className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold">{t('app.name')}</h1>
        <div className="flex items-center gap-2">
          <LanguageToggle only={config?.languages} />
          <Link to="/guide" aria-label={t('dash.guideNav')} className="grid size-10 place-items-center rounded-full border border-[#2F7FB8]/30 bg-[#FFFBF2]/90">
            <BookOpen className="size-5" />
          </Link>
          <ListenButton text={listen} />
        </div>
      </header>

      {config?.location_label && (
        <p className="flex items-center gap-1 text-sm text-muted-foreground">
          <MapPin className="size-4" />
          {t('location.chip', { label: config.location_label, number: config.primary_emergency_number })}
        </p>
      )}

      <SafetyPromise />

      <SosButton
        disabled={busy || session.isError}
        onSend={(where) => submit('sos', {}, where).catch(() => undefined)}
      />

      <div className="grid grid-cols-2 gap-3 [&>*]:min-w-0">
        <HoldToSpeak
          disabled={busy}
          onRecorded={(audio) =>
            void withLocation((where) => submit('voice', { audio }, where)).catch(() => undefined)
          }
        />
        <TextReportSheet
          disabled={busy}
          onSend={(text) => withLocation((where) => submit('text', { text }, where))}
        />
      </div>

      <Button asChild variant="outline" size="lg" className="h-16 border-[#2F7FB8]/40 bg-[#FFFBF2]/85 text-lg font-extrabold text-[#12324A] hover:bg-[#CFE6F6]">
        <Link to="/card/new">
          <IdCard className="size-7" /> {t('card.new')}
        </Link>
      </Button>

      <footer className="mt-auto space-y-3 pt-2">
        <p className="text-center text-sm font-semibold text-muted-foreground">{t('home.callNow')}</p>
        <CallButtons config={config} lang={lang} />
      </footer>
    </div>
  )
}
