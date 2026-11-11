import type { Lang } from '@/i18n'

const VOICE_LANG: Record<Lang, string> = { en: 'en-US', es: 'es-US', ur: 'ur-PK' }

function pickVoice(lang: Lang): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices()
  const want = VOICE_LANG[lang].toLowerCase()
  return (
    voices.find((v) => v.lang.toLowerCase() === want) ??
    voices.find((v) => v.lang.toLowerCase().startsWith(lang)) ??
    null
  )
}

export function stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/**
 * Read text aloud with the browser voice. Resolves true when it finished, false when this phone
 * has no voice for the language or speech is unsupported. A backend gTTS fallback
 * (GET /api/v1/tts/ui) is added with the Voice Coach task; until then the caller shows a message.
 */
export function speak(text: string, lang: Lang): Promise<boolean> {
  if (!('speechSynthesis' in window) || !text.trim()) return Promise.resolve(false)
  window.speechSynthesis.cancel()
  const voice = pickVoice(lang)
  if (!voice) return Promise.resolve(false)
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text)
    u.voice = voice
    u.lang = voice.lang
    u.onend = () => resolve(true)
    u.onerror = () => resolve(false)
    window.speechSynthesis.speak(u)
  })
}
