import { ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Card } from '@/components/ui/card'

/** F-42: calm one-line promise. Never asks for a name or phone. */
export function SafetyPromise() {
  const { t } = useTranslation()
  return (
    <Card className="flex-row items-center gap-3 border-ack/30 bg-[#FFFBF2]/90 p-4 text-[#12324A]">
      <ShieldCheck className="size-10 shrink-0 text-ack" />
      <div>
        <p className="font-extrabold">{t('home.safetyTitle')}</p>
        <p className="text-base leading-snug text-muted-foreground">{t('safety.promise')}</p>
      </div>
    </Card>
  )
}
