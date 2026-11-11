import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { getLocation, type Coords } from '@/hooks/useGeolocation'

const COUNTDOWN_S = 3

type Props = {
  /** Called after the countdown with the best location we have (or null). */
  onSend: (coords: Coords | null) => Promise<void>
  disabled?: boolean
}

/** F-01: one big SOS button, 3 second cancel countdown, then submit. No typing. */
export function SosButton({ onSend, disabled }: Props) {
  const { t } = useTranslation()
  const [left, setLeft] = useState<number | null>(null)
  const [sending, setSending] = useState(false)
  const location = useRef<Promise<Coords | null> | null>(null)

  // Ask for the location on the first interaction (not on page load) while the countdown runs.
  const start = () => {
    location.current = getLocation()
    setLeft(COUNTDOWN_S)
  }

  useEffect(() => {
    if (left === null || sending) return
    if (left === 0) {
      setSending(true)
      void (location.current ?? Promise.resolve(null))
        .then((coords) => onSend(coords))
        .finally(() => {
          setSending(false)
          setLeft(null)
        })
      return
    }
    const id = window.setTimeout(() => setLeft(left - 1), 1000)
    return () => window.clearTimeout(id)
  }, [left, sending, onSend])

  const cancel = () => {
    location.current = null
    setLeft(null)
  }

  return (
    <>
      <div className="flex justify-center py-2">
        <button
          type="button"
          onClick={start}
          disabled={disabled || left !== null}
          aria-label={t('sos.button')}
          className="relative grid size-[min(70vw,320px)] place-items-center rounded-full bg-sos text-white shadow-xl active:bg-sos-dark disabled:opacity-70"
        >
          <span className="absolute inset-0 -z-10 animate-ping rounded-full bg-sos/30 motion-reduce:hidden" />
          <span className="text-center">
            <span className="block text-5xl font-extrabold">{t('sos.button')}</span>
            <span className="mt-2 block px-6 text-lg font-semibold">{t('sos.subtitle')}</span>
          </span>
        </button>
      </div>

      {left !== null && (
        <div
          role="alertdialog"
          aria-live="assertive"
          className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-8 bg-sos p-6 text-white"
        >
          {sending ? (
            <>
              <Loader2 className="size-20 animate-spin" />
              <p className="text-3xl font-extrabold">{t('sos.gettingLocation')}</p>
            </>
          ) : (
            <>
              <p className="text-3xl font-extrabold">{t('sos.sending', { n: left })}</p>
              <p className="text-9xl font-extrabold tabular-nums">{left}</p>
              <Button
                type="button"
                size="lg"
                variant="secondary"
                onClick={cancel}
                className="h-24 w-full max-w-sm text-3xl font-extrabold"
              >
                {t('sos.cancel')}
              </Button>
            </>
          )}
        </div>
      )}
    </>
  )
}
