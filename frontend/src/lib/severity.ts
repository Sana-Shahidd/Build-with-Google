export type Severity = 'low' | 'medium' | 'high' | 'critical'

// Single source for severity colours (docs/09 section 2). Values mirror the @theme tokens.
export const SEVERITY_COLOR: Record<Severity, string> = {
  low: '#22C55E',
  medium: '#EAB308',
  high: '#F97316',
  critical: '#E11D2E',
}

export const SEVERITY_RADIUS: Record<Severity, number> = { low: 10, medium: 14, high: 18, critical: 22 }

export const SEVERITY_BAR: Record<Severity, string> = {
  low: 'bg-low',
  medium: 'bg-medium',
  high: 'bg-high',
  critical: 'bg-critical',
}
