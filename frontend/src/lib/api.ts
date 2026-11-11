import type { ZodType } from 'zod'
import { apiErrorBody } from './schemas'
import { accessToken } from './supabase'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, schema: ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, init)
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const parsed = apiErrorBody.safeParse(body)
    throw new ApiError(
      res.status,
      parsed.success ? parsed.data.error.code : 'INTERNAL',
      parsed.success ? parsed.data.error.message : `HTTP ${res.status}`,
    )
  }
  return schema.parse(body)
}

export const apiGet = <T>(path: string, schema: ZodType<T>) => request(path, schema)
export const apiPost = <T>(path: string, schema: ZodType<T>) =>
  request(path, schema, { method: 'POST' })

/** Calls that need the anonymous reporter session (Authorization: Bearer access_token). */
async function authed<T>(path: string, schema: ZodType<T>, init: RequestInit = {}): Promise<T> {
  const token = await accessToken()
  return request(path, schema, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  })
}

export const apiAuthedGet = <T>(path: string, schema: ZodType<T>) => authed(path, schema)
export const apiAuthedPostForm = <T>(path: string, form: FormData, schema: ZodType<T>) =>
  authed(path, schema, { method: 'POST', body: form })
export const apiAuthedPostJson = <T>(path: string, body: object, schema: ZodType<T>) =>
  authed(path, schema, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

/** The owner-only QR sticker as inline SVG markup. */
export async function fetchCardQr(cardId: string): Promise<string> {
  const token = await accessToken()
  const res = await fetch(`${BASE}/api/v1/cards/${cardId}/qr.svg`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new ApiError(res.status, 'INTERNAL', 'qr failed')
  return res.text()
}
