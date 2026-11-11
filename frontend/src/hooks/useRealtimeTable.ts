import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export type LiveStatus = 'connecting' | 'live' | 'offline'

/**
 * Subscribe to Postgres changes on the given tables (Supabase Realtime, RLS applies) and
 * invalidate the React Query caches whose key starts with the table name. Returns the connection
 * state for the header dot. React Query still re-fetches on an interval as a safety net.
 */
export function useRealtimeTables(
  tables: string[],
  onInsert?: (table: string, row: Record<string, unknown>) => void,
): LiveStatus {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<LiveStatus>('connecting')
  const key = tables.join(',')

  useEffect(() => {
    const channel = supabase.channel(`dashboard-${key}`)
    for (const table of key.split(',')) {
      channel.on('postgres_changes', { event: '*', schema: 'public', table }, (payload) => {
        void queryClient.invalidateQueries({ queryKey: [table] })
        if (payload.eventType === 'INSERT') onInsert?.(table, payload.new)
      })
    }
    channel.subscribe((s) => {
      setStatus(s === 'SUBSCRIBED' ? 'live' : s === 'CLOSED' || s === 'CHANNEL_ERROR' ? 'offline' : 'connecting')
    })
    return () => {
      void supabase.removeChannel(channel)
    }
    // onInsert is intentionally read once per mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, queryClient])

  return status
}
