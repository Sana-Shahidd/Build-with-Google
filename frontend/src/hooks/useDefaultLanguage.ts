import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { isLang, savedLang } from '@/i18n'
import type { AppConfig } from '@/lib/schemas'

/** Use the country profile default language (Urdu for PK) until the person picks one. */
export function useDefaultLanguage(config: AppConfig | undefined) {
  const { i18n } = useTranslation()
  useEffect(() => {
    if (config && !savedLang() && isLang(config.default_lang) && i18n.language !== config.default_lang) {
      void i18n.changeLanguage(config.default_lang)
    }
  }, [config, i18n])
}
