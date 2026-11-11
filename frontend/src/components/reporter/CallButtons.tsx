import { Phone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { AppConfig } from '@/lib/schemas'

/** Emergency call buttons from the country profile (tel: links). Labels come from the profile. */
export function CallButtons({ config, lang }: { config: AppConfig | undefined; lang: string }) {
  // Never an empty footer: fall back to the international number while the profile loads.
  const numbers = config?.emergency_numbers ?? [
    { key: 'intl', label: { en: 'Call 112', ur: '112 پر کال کریں', es: 'Llamar al 112' }, number: '112' },
  ]
  return (
    <div className={cn('grid gap-3', numbers.length > 1 ? 'grid-cols-2' : 'grid-cols-1')}>
      {numbers.map((n) => (
        <Button key={n.key} asChild size="lg" variant="outline" className="h-16 text-lg font-extrabold">
          <a href={`tel:${n.number}`}>
            <Phone className="size-6" /> {n.label[lang] ?? n.label.en ?? n.number}
          </a>
        </Button>
      ))}
    </div>
  )
}
