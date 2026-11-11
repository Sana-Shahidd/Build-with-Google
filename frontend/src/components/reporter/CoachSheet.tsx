import { ChevronLeft, ChevronRight, MessageCircleHeart, RotateCcw, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { isLang } from '@/i18n'
import { apiAuthedPostForm } from '@/lib/api'
import { extensionFor, type Recording } from '@/lib/recorder'
import { speak, stopSpeaking } from '@/lib/speak'
import { coachReply, type CoachReply, type FirstAidCard } from '@/lib/schemas'
import { cn } from '@/lib/utils'
import { CprMetronome } from './CprMetronome'
import { HoldToSpeak } from './HoldToSpeak'

/**
 * "Talk me through it": reads the selected first-aid card one step at a time with Next / Repeat
 * (F-39 without the agent). The spoken words come only from the card file.
 */
export function CoachSheet({ cards, reportId }: { cards: FirstAidCard[]; reportId: string }) {
  const { t, i18n } = useTranslation()
  const lang = isLang(i18n.language) ? i18n.language : 'en'
  const [open, setOpen] = useState(false)
  const [cardIndex, setCardIndex] = useState(0)
  const [step, setStep] = useState(0)
  const [reply, setReply] = useState<CoachReply | null>(null)
  const card = cards[Math.min(cardIndex, cards.length - 1)]

  // Voice Coach turn: send the recording; the backend picks the card/step, the words come from the card file
  const talk = async (rec: Recording) => {
    const form = new FormData()
    form.set('audio', rec.blob, `coach.${extensionFor(rec.blob.type)}`)
    form.set('lang', lang)
    form.set('step', String(step))
    if (card) form.set('card_key', card.key)
    try {
      const r = await apiAuthedPostForm(`/reports/${reportId}/coach`, form, coachReply)
      const idx = cards.findIndex((c) => c.key === r.card_key)
      if (idx >= 0) {
        setCardIndex(idx)
        setStep(r.step)
        setReply({ ...r, text: '' })
      } else {
        setReply(r)
      }
      void speak(`${r.ack} ${r.text}`, lang)
    } catch {
      toast.error(t('report.failed'))
    }
  }

  const say = async (text: string) => {
    if (!(await speak(text, lang))) toast.error(t('listen.unavailable'))
  }

  // Read each step aloud when it changes (the sheet was opened by a tap, so audio is allowed).
  useEffect(() => {
    if (open && card) void speak(`${step === 0 ? card.title + '. ' : ''}${card.steps[step]}`, lang)
    return () => stopSpeaking()
  }, [open, card, step, lang])

  if (!card) return null
  const last = step >= card.steps.length - 1

  const pickCard = (i: number) => {
    setCardIndex(i)
    setStep(0)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button type="button" size="lg" className="h-20 w-full gap-3 bg-info text-xl font-extrabold text-white hover:bg-info/90">
          <MessageCircleHeart className="size-9" /> {t('coach.button')}
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="max-h-[92dvh] gap-3 overflow-y-auto p-4">
        <SheetHeader className="p-0">
          <SheetTitle className="text-2xl font-extrabold">{t('coach.title')}</SheetTitle>
        </SheetHeader>

        {cards.length > 1 && (
          <div className="flex flex-wrap gap-2">
            {cards.map((c, i) => (
              <Button
                key={c.key}
                size="sm"
                variant={i === cardIndex ? 'default' : 'outline'}
                onClick={() => pickCard(i)}
              >
                {c.title}
              </Button>
            ))}
          </div>
        )}

        <div className="rounded-xl border p-4">
          <p className="text-sm font-semibold text-muted-foreground">
            {card.title} · {t('coach.step', { n: step + 1, total: card.steps.length })}
          </p>
          <p className="mt-2 text-2xl font-extrabold leading-snug">{card.steps[step]}</p>
        </div>

        {reply && (
          <div className="rounded-xl bg-info/10 p-3">
            <p className="font-extrabold">{reply.ack}</p>
            {reply.text && <p className="mt-1 text-xl font-semibold leading-snug">{reply.text}</p>}
          </div>
        )}

        {(card.key === 'cardiac' || reply?.card_key === 'cardiac') && <CprMetronome />}

        <HoldToSpeak onRecorded={(r) => void talk(r)} />

        <div className="grid grid-cols-3 gap-2">
          <Button
            type="button"
            size="lg"
            variant="outline"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="h-16 text-lg"
          >
            <ChevronLeft className="size-6 rtl:rotate-180" />
          </Button>
          <Button
            type="button"
            size="lg"
            variant="outline"
            onClick={() => void say(card.steps[step])}
            className="h-16 text-lg font-extrabold"
          >
            <RotateCcw className="size-5" /> {t('coach.repeat')}
          </Button>
          <Button
            type="button"
            size="lg"
            onClick={() => (last ? setOpen(false) : setStep((s) => s + 1))}
            className={cn('h-16 text-lg font-extrabold', last ? 'bg-ack hover:bg-ack/90' : '')}
          >
            {last ? t('coach.done') : t('coach.next')}
            {!last && <ChevronRight className="size-6 rtl:rotate-180" />}
          </Button>
        </div>

        <Button type="button" variant="ghost" onClick={() => void say(card.steps.join('. '))}>
          <Volume2 className="size-5" /> {t('coach.listen')}
        </Button>
        <p className="text-sm text-muted-foreground">{t('coach.disclaimer')}</p>
      </SheetContent>
    </Sheet>
  )
}
