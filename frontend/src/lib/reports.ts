import { apiAuthedPostForm } from './api'
import { extensionFor, type Recording } from './recorder'
import { reportCreated } from './schemas'
import type { Coords } from '@/hooks/useGeolocation'

export type NewReport = {
  inputType: 'sos' | 'voice' | 'text'
  text?: string
  audio?: Recording
  coords: Coords | null
  lang: string
}

/** POST /api/v1/reports (multipart). The client id makes retries idempotent (docs/06 section 2). */
export function sendReport(r: NewReport) {
  const form = new FormData()
  form.set('client_report_id', crypto.randomUUID())
  form.set('input_type', r.inputType)
  form.set('lang', r.lang)
  if (r.coords) {
    form.set('lat', String(r.coords.lat))
    form.set('lng', String(r.coords.lng))
    form.set('accuracy_m', String(Math.max(0, r.coords.accuracy_m)))
  }
  if (r.text) form.set('text', r.text)
  if (r.audio) {
    form.set('audio', r.audio.blob, `report.${extensionFor(r.audio.blob.type)}`)
  }
  return apiAuthedPostForm('/reports', form, reportCreated)
}
