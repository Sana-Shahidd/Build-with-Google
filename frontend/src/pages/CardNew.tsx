import { VideoBackdrop } from '@/components/VideoBackdrop'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Check, Printer } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { LanguageToggle } from '@/components/LanguageToggle'
import { ListenButton } from '@/components/reporter/ListenButton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { isLang } from '@/i18n'
import { apiAuthedPostJson, fetchCardQr } from '@/lib/api'
import { cardCreated } from '@/lib/schemas'
import { cn } from '@/lib/utils'

const BLOOD = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] as const
const STEPS = 5

/** Emergency Card set-up (F-36): ONE question per screen, big targets, read aloud. Guided form. */
export default function CardNew() {
  const { t, i18n } = useTranslation()
  const lang = isLang(i18n.language) ? i18n.language : 'ur'
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [blood, setBlood] = useState<string | null>(null)
  const [allergy, setAllergy] = useState('')
  const [contactName, setContactName] = useState('')
  const [relation, setRelation] = useState('')
  const [phone, setPhone] = useState('')
  const [showPhone, setShowPhone] = useState(true)

  const save = useMutation({
    mutationFn: () =>
      apiAuthedPostJson(
        '/cards',
        {
          full_name: name.trim(),
          blood_type: blood,
          allergies: allergy.trim() || null,
          contacts: [{ name: contactName.trim(), relation: relation.trim() || null, phone: phone.trim() }],
          lang,
          show_phone: showPhone,
          consent: true,
        },
        cardCreated,
      ),
    onError: () => toast.error(t('card.error')),
  })
  const qr = useQuery({
    queryKey: ['card-qr', save.data?.card_id],
    queryFn: () => fetchCardQr(save.data!.card_id),
    enabled: !!save.data,
  })

  const questions = [t('card.name'), t('card.bloodGroup'), t('card.allergy'), t('card.family'), t('card.confirmQ')]
  const canNext = [name.trim().length >= 2, true, true, contactName.trim() && phone.trim().length >= 5, true][step]

  if (save.data) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-md flex-col items-center gap-4 p-4 text-center text-ink print:max-w-none">
      <VideoBackdrop />
        <h1 className="text-2xl font-extrabold">{t('card.created')}</h1>
        <p className="text-4xl font-extrabold">{name}</p>
        <p className="text-xl">{blood ?? ''} {allergy && `· ${t('card.allergy')} ${allergy}`}</p>
        <div className="w-64 max-w-full rounded-xl border p-2 [&>svg]:h-auto [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: qr.data ?? '' }} />
        <p className="text-lg font-extrabold">{t('card.scanIfHurt')}</p>
        <p className="break-all text-xs text-muted-foreground">{t('card.scanUrl')}: {save.data.scan_url}</p>
        <div className="flex w-full gap-2 print:hidden">
          <Button size="lg" className="h-16 flex-1 text-lg font-extrabold" onClick={() => window.print()}>
            <Printer /> {t('card.print')}
          </Button>
          <Button asChild size="lg" variant="outline" className="h-16 flex-1 text-lg">
            <Link to="/">{t('status.home')}</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 p-4 text-ink">
      <VideoBackdrop />
      <header className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="icon" className="size-12">
          <Link to="/" aria-label={t('status.home')}><ArrowLeft className="rtl:rotate-180" /></Link>
        </Button>
        <div className="flex items-center gap-2">
          <LanguageToggle />
          <ListenButton text={`${questions[step]}`} />
        </div>
      </header>

      <div className="flex justify-center gap-2" aria-label={t('card.step', { n: step + 1, total: STEPS })}>
        {Array.from({ length: STEPS }, (_, i) => (
          <span key={i} className={cn('size-3 rounded-full', i <= step ? 'bg-info' : 'bg-muted')} />
        ))}
      </div>

      <h1 className="text-center text-2xl font-extrabold leading-snug">{questions[step]}</h1>

      <div className="flex flex-1 flex-col gap-3">
        {step === 0 && <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} maxLength={80} className="h-16 text-2xl" />}
        {step === 1 && (
          <div className="grid grid-cols-4 gap-2">
            {BLOOD.map((b) => (
              <Button key={b} variant={blood === b ? 'default' : 'outline'} onClick={() => setBlood(b)} className="h-20 text-2xl font-extrabold">
                {b}
              </Button>
            ))}
            <Button variant={blood === null ? 'default' : 'outline'} onClick={() => setBlood(null)} className="col-span-4 h-16 text-lg">
              {t('card.dontKnow')}
            </Button>
          </div>
        )}
        {step === 2 && (
          <>
            <Button variant={allergy === '' ? 'default' : 'outline'} onClick={() => setAllergy('')} className="h-20 text-2xl font-extrabold">
              {t('card.none')}
            </Button>
            <Input value={allergy} onChange={(e) => setAllergy(e.target.value)} maxLength={120} className="h-16 text-xl" />
          </>
        )}
        {step === 3 && (
          <>
            <Input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder={t('card.contactName')} maxLength={60} className="h-16 text-xl" />
            <Input value={relation} onChange={(e) => setRelation(e.target.value)} placeholder={t('card.relation')} maxLength={30} className="h-16 text-xl" />
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder={t('card.phone')} type="tel" inputMode="tel" className="h-16 text-xl" />
          </>
        )}
        {step === 4 && (
          <div className="space-y-3 rounded-xl border p-4 text-xl">
            <p className="text-3xl font-extrabold">{name}</p>
            <p>{t('card.bloodGroup')}: <b>{blood ?? t('card.dontKnow')}</b></p>
            <p>{t('card.allergy')} <b>{allergy || t('card.none')}</b></p>
            <p>{contactName} {relation && `(${relation})`}</p>
            <label className="flex items-start gap-3 text-base">
              <input type="checkbox" checked={showPhone} onChange={(e) => setShowPhone(e.target.checked)} className="mt-1 size-6" />
              {t('card.showPhone')}
            </label>
            <p className="text-sm text-muted-foreground">{t('card.consent')}</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Button variant="outline" size="lg" disabled={step === 0} onClick={() => setStep(step - 1)} className="h-16 text-lg">
          <ArrowLeft className="rtl:rotate-180" /> {t('card.back')}
        </Button>
        {step < STEPS - 1 ? (
          <Button size="lg" disabled={!canNext} onClick={() => setStep(step + 1)} className="h-16 text-lg font-extrabold">
            {t('card.next')} <ArrowRight className="rtl:rotate-180" />
          </Button>
        ) : (
          <Button size="lg" disabled={save.isPending} onClick={() => save.mutate()} className="h-16 bg-ack text-lg font-extrabold text-white hover:bg-ack/90">
            <Check /> {t('card.save')}
          </Button>
        )}
      </div>
    </div>
  )
}
