import { useQuery } from '@tanstack/react-query'
import { accessToken } from '@/lib/supabase'

/** Creates the anonymous Supabase session as soon as the app opens, so SOS never waits for it. */
export function useAnonSession() {
  return useQuery({
    queryKey: ['anon-session'],
    queryFn: async () => {
      await accessToken()
      return true
    },
    staleTime: Infinity,
    retry: 2,
  })
}
