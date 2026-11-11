import { Mic, Square } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { MAX_RECORD_S, startRecording, type Recorder, type Recording } from '@/lib/recorder'
import { cn } from '@/lib/utils'

const TAP_MS = 400 // a press shorter than this is a tap: tap once to start, tap again to stop
const CANCEL_PX = 80 // slide up this far while holding to cancel

/** F-02: hold to speak in any language; release sends. Tap-tap fallback for accessibility. */
export function HoldToSpeak({
  onRecorded,
  disabled,
}: {
  onRecorded: (r: Recording) => void
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const [seconds, setSeconds] = useState<number | null>(null)
  const recorder = useRef<Recorder | null>(null)
  const pressedAt = useRef(0)
  const startY = useRef(0)
  const toggled = useRef(false)

  const finish = async (cancel: boolean) => {
    const rec = recorder.current
    recorder.current = null
    toggled.current = false
    setSeconds(null)
    if (!rec) return
    const result = await rec.stop(cancel)
    if (result) onRecorded(result)
    else if (!cancel) toast.error(t('report.tooShort'))
  }

  const down = async (e: React.PointerEvent) => {
    if (disabled) return
    if (toggled.current) return void finish(false) // second tap of tap-tap mode
    startY.current = e.clientY
    pressedAt.current = Date.now()
    try {
      setSeconds(0)
      recorder.current = await startRecording(setSeconds)
    } catch {
      setSeconds(null)
      toast.error(t('report.micDenied'))
    }
  }

  const up = (e: React.PointerEvent) => {
    if (!recorder.current || toggled.current) return
    if (Date.now() - pressedAt.current < TAP_MS) {
      toggled.current = true // keep recording until the next tap
      return
    }
    void finish(startY.current - e.clientY > CANCEL_PX)
  }

  const recording = seconds !== null
  return (
    <div className="flex flex-col items-center gap-1">
      <Button
        type="button"
        size="lg"
        variant={recording ? 'default' : 'outline'}
        disabled={disabled}
        onPointerDown={(e) => void down(e)}
        onPointerUp={up}
        className={cn(
          'h-24 w-full min-w-0 touch-none select-none flex-col gap-1 whitespace-normal px-2 text-center text-base font-extrabold leading-tight',
          recording && 'bg-sos text-white hover:bg-sos',
        )}
      >
        {recording ? <Square className="size-8" /> : <Mic className="size-9" />}
        {recording ? `${seconds}s / ${MAX_RECORD_S}s` : t('report.speak')}
      </Button>
      {recording && (
        <p className="text-sm text-muted-foreground">
          {toggled.current ? t('report.tapToStop') : t('report.recording')}
        </p>
      )}
    </div>
  )
}
