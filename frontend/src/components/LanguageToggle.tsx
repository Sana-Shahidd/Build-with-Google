import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { chooseLang, isLang, LANGS } from '@/i18n'

/** EN | ES | اردو. `only` limits the choices (the country profile languages on the reporter app). */
export function LanguageToggle({ only }: { only?: string[] }) {
  const { t, i18n } = useTranslation()
  const current = isLang(i18n.language) ? i18n.language : 'en'
  const choices = LANGS.filter((code) => !only || only.includes(code))
  return (
    <div className="flex gap-1">
      {choices.map((code) => (
        <Button
          key={code}
          size="sm"
          variant={current === code ? 'default' : 'outline'}
          onClick={() => chooseLang(code)}
        >
          {t(`lang.${code}`)}
        </Button>
      ))}
    </div>
  )
}
