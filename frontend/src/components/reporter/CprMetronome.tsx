import { HeartPulse, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'

const BPM = 110 // within the 100-120 per minute range used for CPR compressions

/** CPR beat using the Web Audio API OscillatorNode (docs/AGENTS Rule 1: no audio libraries). */
export function CprMetronome() {
  const { t } = useTranslation()
  const [on, setOn] = useState(false)
  const ctx = useRef<AudioContext | null>(null)

  useEffect(() => {
    if (!on) return
    const audio = ctx.current ?? new AudioContext()
    ctx.current = audio
    const beep = () => {
      const osc = audio.createOscillator()
      const gain = audio.createGain()
      osc.frequency.value = 880
      gain.gain.setValueAtTime(0.4, audio.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.12)
      osc.connect(gain).connect(audio.destination)
      osc.start()
      osc.stop(audio.currentTime + 0.12)
    }
    void audio.resume()
    beep()
    const id = window.setInterval(beep, 60000 / BPM)
    return () => window.clearInterval(id)
  }, [on])

  useEffect(() => () => void ctx.current?.close(), [])

  return (
    <Button
      type="button"
      size="lg"
      variant={on ? 'default' : 'outline'}
      onClick={() => setOn((v) => !v)}
      className="h-16 w-full text-lg font-extrabold"
    >
      {on ? <Square className="size-6" /> : <HeartPulse className="size-7" />}
      {on ? t('coach.metronomeStop') : t('coach.metronome')}
    </Button>
  )
}
