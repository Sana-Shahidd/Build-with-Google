import { z } from 'zod'

const langText = z.object({
  en: z.array(z.string()),
  es: z.array(z.string()),
  ur: z.array(z.string()),
})

export const responderAlert = z.object({
  target_id: z.string(),
  kind: z.string(),
  state: z.string(),
  acknowledged_at: z.string().nullable(),
  created_at: z.string(),
  ack_token: z.string().nullable(),
  incident: z.object({
    short_code: z.string(),
    incident_type: z.string(),
    severity: z.enum(['low', 'medium', 'high', 'critical']),
    status: z.string(),
    location_label: z.string().nullable(),
    map_url: z.string().nullable(),
  }),
  text: langText,
})

export const responderInbox = z.object({
  org: z.object({
    id: z.string(),
    name: z.string(),
    type: z.string(),
    lang: z.enum(['en', 'es', 'ur']),
  }),
  alerts: z.array(responderAlert),
})

export const ackResult = z.object({
  acknowledged: z.boolean(),
  acknowledged_at: z.string().nullable(),
  first: z.boolean(),
})

export const apiErrorBody = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
})

export type ResponderInbox = z.infer<typeof responderInbox>
export type ResponderAlert = z.infer<typeof responderAlert>

// ---- reporter app --------------------------------------------------------------------------
export const emergencyNumber = z.object({
  key: z.string(),
  label: z.record(z.string(), z.string()),
  number: z.string(),
})

export const appConfig = z.object({
  country: z.string(),
  detected: z.boolean(),
  location_label: z.string().nullable(),
  name: z.string(),
  languages: z.array(z.string()),
  default_lang: z.string(),
  primary_emergency_number: z.string(),
  emergency_numbers: z.array(emergencyNumber),
})

export const firstAidCard = z.object({
  key: z.string(),
  icon: z.string(),
  title: z.string(),
  steps: z.array(z.string()),
})

export const reportCreated = z.object({
  report_id: z.string(),
  status: z.string(),
  first_aid: z.array(firstAidCard),
})

export const serviceName = z.enum(['hospital', 'ambulance', 'police', 'fire'])

export const reportStatus = z.object({
  report_id: z.string(),
  report_status: z.enum(['received', 'processing', 'processed', 'failed']),
  transcript: z.string().nullable(),
  incident: z
    .object({
      short_code: z.string(),
      incident_type: z.string(),
      severity: z.enum(['low', 'medium', 'high', 'critical']),
      status: z.string(),
      silent: z.boolean(),
      needs: z.array(z.string()),
      landmark_text: z.string().nullable().optional(),
      landmark_local: z.string().nullable().optional(),
    })
    .nullable(),
  services: z.array(
    z.object({
      service: serviceName,
      state: z.enum(['pending', 'alerted', 'acknowledged']),
      acknowledged_at: z.string().nullable(),
      count_alerted: z.number(),
      count_acknowledged: z.number(),
    }),
  ),
  followup_question: z.string().nullable(),
  followup_answered: z.boolean(),
  first_aid: z.array(firstAidCard),
})

export type AppConfig = z.infer<typeof appConfig>
export type FirstAidCard = z.infer<typeof firstAidCard>
export type ReportStatus = z.infer<typeof reportStatus>

// ---- dashboard (Supabase reads under RLS; docs/03 section 10) ------------------------------
export const severity = z.enum(['low', 'medium', 'high', 'critical'])

export const incidentRow = z.object({
  id: z.string(),
  short_code: z.string(),
  incident_type: z.string(),
  severity,
  status: z.enum(['review', 'unverified', 'verified', 'closed', 'dismissed']),
  lat: z.number().nullable(),
  lng: z.number().nullable(),
  location_label: z.string().nullable(),
  landmark_text: z.string().nullable(),
  landmark_local: z.string().nullable(),
  summary_en: z.string().nullable(),
  summary_local: z.string().nullable(),
  local_lang: z.string().nullable(),
  est_casualties_min: z.number(),
  est_casualties_max: z.number(),
  injury_types: z.array(z.string()),
  needs: z.array(z.string()),
  ongoing_danger: z.boolean(),
  confidence: z.number(),
  report_count: z.number(),
  unique_reporters: z.number(),
  first_alert_at: z.string().nullable().optional(),
  first_ack_at: z.string().nullable().optional(),
  silent: z.boolean(),
  created_at: z.string(),
})

export const targetRow = z.object({
  id: z.string(),
  incident_id: z.string(),
  recipient_kind: z.string(),
  recipient_label: z.string(),
  is_standby: z.boolean(),
  status: z.string(),
  acknowledged_at: z.string().nullable(),
  acknowledged_via: z.string().nullable(),
  escalation_level: z.number(),
  created_at: z.string(),
})

export const assignmentRow = z.object({
  id: z.string(),
  incident_id: z.string(),
  hospital_id: z.string(),
  assigned_casualties: z.number(),
  critical: z.number(),
  eta_minutes: z.number().nullable(),
  over_capacity: z.boolean(),
  reason: z.string().nullable(),
  planned_by: z.string(),
  organizations: z.object({ name: z.string() }).nullable(),
})

export const orgRow = z.object({
  id: z.string(),
  type: z.enum(['hospital', 'police_station', 'rescue_station', 'fire_station']),
  name: z.string(),
  lat: z.number(),
  lng: z.number(),
  hospital_details: z
    .object({ er_beds_available: z.number(), capabilities: z.array(z.string()) })
    .nullable(),
})

export const activityRow = z.object({
  id: z.number(),
  incident_id: z.string().nullable(),
  agent: z.string(),
  kind: z.string(),
  message: z.string(),
  model: z.string().nullable(),
  tool: z.string().nullable(),
  latency_ms: z.number().nullable(),
  created_at: z.string(),
})

export const reportRow = z.object({
  id: z.string(),
  input_type: z.string(),
  raw_text: z.string().nullable(),
  transcript: z.string().nullable(),
  ai_provider: z.string().nullable(),
  ai_confidence: z.number().nullable(),
  created_at: z.string(),
})

export const eventRow = z.object({
  id: z.number(),
  kind: z.string(),
  message: z.string(),
  created_at: z.string(),
})

export const profileRow = z.object({
  role: z.string(),
  org_id: z.string().nullable(),
  display_name: z.string().nullable(),
})

export type IncidentRow = z.infer<typeof incidentRow>
export type TargetRow = z.infer<typeof targetRow>
export type AssignmentRow = z.infer<typeof assignmentRow>
export type OrgRow = z.infer<typeof orgRow>
export type ActivityRow = z.infer<typeof activityRow>
export type ReportRow = z.infer<typeof reportRow>
export type EventRow = z.infer<typeof eventRow>

export const coachReply = z.object({
  intent: z.string(),
  card_key: z.string(),
  step: z.number(),
  of: z.number(),
  ack: z.string(),
  text: z.string(),
  icon: z.string(),
  is_last: z.boolean(),
  source: z.enum(['agent', 'rules']),
})
export type CoachReply = z.infer<typeof coachReply>

export const cardCreated = z.object({
  card_id: z.string(),
  token: z.string(),
  scan_url: z.string(),
  print_url: z.string(),
})

export const publicCard = z.object({
  full_name: z.string(),
  blood_type: z.string().nullable(),
  allergies: z.string().nullable(),
  lang: z.string(),
  contacts: z.array(
    z.object({ name: z.string(), relation: z.string().nullable(), phone: z.string().optional() }),
  ),
  emergency_numbers: z.array(emergencyNumber),
})

export const alertCreated = z.object({ report_id: z.string() })
export type PublicCard = z.infer<typeof publicCard>
