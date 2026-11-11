import { Square, Volume2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { isLang } from '@/i18n'
import { speak, stopSpeaking } from '@/lib/speak'

/** Round 64 px button that reads the screen aloud (docs/09 section 1, rule 7). */
export function ListenButton({ text }: { text: string }) {
  const { t, i18n } = useTranslation()
  const [speaking, setSpeaking] = useState(false)

  const toggle = async () => {
    if (speaking) {
      stopSpeaking()
      setSpeaking(false)
      return
    }
    setSpeaking(true)
    const ok = await speak(text, isLang(i18n.language) ? i18n.language : 'en')
    setSpeaking(false)
    if (!ok) toast.error(t('listen.unavailable'))
  }

  return (
    <Button
      type="button"
      size="icon"
      variant={speaking ? 'default' : 'outline'}
      onClick={() => void toggle()}
      aria-label={speaking ? t('listen.stop') : t('listen.button')}
      className="size-16 shrink-0 rounded-full"
    >
      {speaking ? <Square className="size-7" /> : <Volume2 className="size-8" />}
    </Button>
  )
}
