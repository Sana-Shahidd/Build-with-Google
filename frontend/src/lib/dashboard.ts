import { z, type ZodType } from 'zod'
import {
  activityRow,
  assignmentRow,
  eventRow,
  incidentRow,
  orgRow,
  reportRow,
  targetRow,
} from './schemas'
import { accessToken, supabase } from './supabase'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function parse<T>(schema: ZodType<T>, data: unknown): T[] {
  return z.array(schema).parse(data)
}

export async function fetchIncidents() {
  const { data, error } = await supabase
    .from('incidents')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100)
  if (error) throw error
  return parse(incidentRow, data)
}

export async function fetchTargets() {
  const { data, error } = await supabase.from('alert_targets').select('*').order('created_at', { ascending: false })
  if (error) throw error
  return parse(targetRow, data)
}

export async function fetchAssignments() {
  const { data, error } = await supabase
    .from('hospital_assignments')
    .select('*, organizations:hospital_id(name)')
  if (error) throw error
  return parse(assignmentRow, data)
}

export async function fetchOrgs() {
  const { data, error } = await supabase
    .from('organizations')
    .select('id,type,name,lat,lng,hospital_details(er_beds_available,capabilities)')
  if (error) throw error
  return parse(orgRow, data)
}

export async function fetchActivity() {
  const { data, error } = await supabase
    .from('agent_activity')
    .select('*')
    .order('id', { ascending: false })
    .limit(200)
  if (error) throw error
  return parse(activityRow, data)
}

export async function fetchActivityLarge() {
  const { data, error } = await supabase
    .from('agent_activity')
    .select('*')
    .order('id', { ascending: false })
    .limit(1000)
  if (error) throw error
  return parse(activityRow, data)
}

export async function fetchReports(incidentId: string) {
  const { data, error } = await supabase
    .from('reports')
    .select('id,input_type,raw_text,transcript,ai_provider,ai_confidence,created_at')
    .eq('incident_id', incidentId)
    .order('created_at', { ascending: false })
  if (error) throw error
  return parse(reportRow, data)
}

export async function fetchEvents(incidentId: string) {
  const { data, error } = await supabase
    .from('incident_events')
    .select('id,kind,message,created_at')
    .eq('incident_id', incidentId)
    .order('id', { ascending: false })
  if (error) throw error
  return parse(eventRow, data)
}

/** Dispatcher actions go through the backend (never direct table writes). */
export async function incidentAction(id: string, action: 'verify' | 'dismiss' | 'close', body?: object) {
  const token = await accessToken()
  const res = await fetch(`${BASE}/api/v1/incidents/${id}/${action}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${action} failed (${res.status})`)
}
