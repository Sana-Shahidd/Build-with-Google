import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api'
import { appConfig } from '@/lib/schemas'
import type { Coords } from './useGeolocation'

/** Country profile for the reporter location (F-35); the fallback profile before a location is known. */
export function useConfig(coords: Coords | null) {
  const key = coords ? `${coords.lat.toFixed(2)},${coords.lng.toFixed(2)}` : 'none'
  return useQuery({
    queryKey: ['config', key],
    queryFn: () =>
      apiGet(coords ? `/config?lat=${coords.lat}&lng=${coords.lng}` : '/config', appConfig),
    staleTime: Infinity,
  })
}
