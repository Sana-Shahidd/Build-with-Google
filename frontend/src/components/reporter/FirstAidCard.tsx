import {
  Bone,
  Brain,
  Building,
  Cloud,
  Droplet,
  Flame,
  Heart,
  HeartPulse,
  Phone,
  Shield,
  Waves,
  Wind,
  type LucideIcon,
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import type { FirstAidCard as Card_ } from '@/lib/schemas'

// icon names come from data/first_aid.json
const ICONS: Record<string, LucideIcon> = {
  shield: Shield,
  phone: Phone,
  droplet: Droplet,
  flame: Flame,
  bone: Bone,
  brain: Brain,
  'heart-pulse': HeartPulse,
  heart: Heart,
  wind: Wind,
  cloud: Cloud,
  waves: Waves,
  building: Building,
}

/** One vetted first-aid card: the words come only from first_aid.json (never an agent). */
export function FirstAidCard({ card }: { card: Card_ }) {
  const Icon = ICONS[card.icon] ?? Shield
  return (
    <Card className="gap-3 p-4">
      <div className="flex items-center gap-3">
        <Icon className="size-9 shrink-0 text-info" />
        <h3 className="text-xl font-extrabold leading-snug">{card.title}</h3>
      </div>
      <ol className="space-y-2 ps-1">
        {card.steps.map((step, i) => (
          <li key={step} className="flex gap-3 text-lg leading-snug">
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-info font-extrabold text-white">
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </Card>
  )
}
