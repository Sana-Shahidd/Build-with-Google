import { useCallback, useEffect, useSyncExternalStore } from 'react'

export type Coords = { lat: number; lng: number; accuracy_m: number }

// One shared, last-known location for the whole app.
let current: Coords | null = null
const listeners = new Set<() => void>()
const subscribe = (fn: () => void) => {
  listeners.add(fn)
  return () => {
    listeners.delete(fn)
  }
}
const set = (c: Coords) => {
  current = c
  listeners.forEach((fn) => fn())
}

/** GPS fix per docs/02 F-01 (high accuracy, 8 s timeout). Resolves the last fix or null. */
export function getLocation(): Promise<Coords | null> {
  if (!('geolocation' in navigator)) return Promise.resolve(null)
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const c = { lat: p.coords.latitude, lng: p.coords.longitude, accuracy_m: p.coords.accuracy }
        set(c)
        resolve(c)
      },
      () => resolve(current),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 },
    )
  })
}

/** Location state. Reads on load only when permission was already granted (never prompts on load). */
export function useGeolocation() {
  const coords = useSyncExternalStore(subscribe, () => current)
  useEffect(() => {
    void navigator.permissions
      ?.query({ name: 'geolocation' })
      .then((s) => (s.state === 'granted' ? getLocation() : null))
      .catch(() => undefined)
  }, [])
  const request = useCallback(() => getLocation(), [])
  return { coords, request }
}
