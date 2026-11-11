import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import es from './es.json'
import ur from './ur.json'

export const LANGS = ['en', 'es', 'ur'] as const
export type Lang = (typeof LANGS)[number]
const STORAGE_KEY = 'gm_lang'

export function isLang(value: unknown): value is Lang {
  return typeof value === 'string' && (LANGS as readonly string[]).includes(value)
}

export function savedLang(): Lang | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return isLang(v) ? v : null
  } catch {
    return null
  }
}

export function chooseLang(lang: Lang) {
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    /* storage can be blocked: the language still changes for this visit */
  }
  void i18n.changeLanguage(lang)
}

function applyDirection(lang: string) {
  document.documentElement.lang = lang
  document.documentElement.dir = lang === 'ur' ? 'rtl' : 'ltr'
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, es: { translation: es }, ur: { translation: ur } },
  lng: savedLang() ?? 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})
i18n.on('languageChanged', applyDirection)
applyDirection(i18n.language)

export default i18n
