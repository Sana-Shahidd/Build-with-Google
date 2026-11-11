import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// Public values only (docs/08 S-13). The backend does all writes; this client is used for the
// anonymous reporter session and, later, dashboard reads.
export const supabase = createClient(url ?? 'http://localhost', key ?? 'missing-key')

/** Anonymous session token for the reporter (no account, nothing asked: docs/01 section 3.1). */
export async function accessToken(): Promise<string> {
  const { data } = await supabase.auth.getSession()
  if (data.session) return data.session.access_token
  const { data: created, error } = await supabase.auth.signInAnonymously()
  if (error || !created.session) throw new Error('anonymous session failed')
  return created.session.access_token
}
