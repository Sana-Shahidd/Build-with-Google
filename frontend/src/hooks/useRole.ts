import { useQuery } from '@tanstack/react-query'
import { profileRow } from '@/lib/schemas'
import { supabase } from '@/lib/supabase'

export const RESPONDER_ROLES = ['dispatcher', 'admin', 'hospital_staff', 'police', 'rescue', 'fire']

/** Current responder session: null when logged out or when the user is only a reporter. */
export function useRole() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data: auth } = await supabase.auth.getUser()
      if (!auth.user) return null
      const { data, error } = await supabase
        .from('profiles')
        .select('role,org_id,display_name')
        .eq('id', auth.user.id)
        .single()
      if (error) throw error
      const profile = profileRow.parse(data)
      return RESPONDER_ROLES.includes(profile.role) ? { ...profile, email: auth.user.email ?? '' } : null
    },
    staleTime: 60_000,
    retry: false,
  })
}
