import { Ambulance, CheckCircle2, Clock, Flame, Hospital, Siren, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { ReportStatus } from '@/lib/schemas'

const ICONS: Record<string, LucideIcon> = {
  hospital: Hospital,
  ambulance: Ambulance,
  police: Siren,
  fire: Flame,
}

/** Service ticks (F-15): waiting -> alerted -> acknowledged. Only services the incident needs. */
export function StatusTicks({ services, lang }: { services: ReportStatus['services']; lang: string }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-2">
      {services.map((s) => {
        const Icon = ICONS[s.service] ?? Hospital
        const acked = s.state === 'acknowledged'
        const time = s.acknowledged_at
          ? new Date(s.acknowledged_at).toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' })
          : null
        return (
          <Card
            key={s.service}
            className={cn('h-16 flex-row items-center gap-3 px-4 py-0', acked && 'border-ack bg-ack/10')}
          >
            <Icon className={cn('size-8 shrink-0', acked ? 'text-ack' : 'text-muted-foreground')} />
            <span className="flex-1 text-lg font-extrabold">{t(`status.${s.service}`)}</span>
            {acked ? (
              <span className="flex items-center gap-1 font-extrabold text-ack">
                <CheckCircle2 className="size-7" /> {t('status.acknowledged')}
                {time && <span className="text-sm font-normal">· {time}</span>}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="size-6" />
                {s.state === 'alerted' ? t('status.alerted') : t('status.pending')}
              </span>
            )}
          </Card>
        )
      })}
    </div>
  )
}
