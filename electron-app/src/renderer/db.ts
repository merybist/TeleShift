/**
 * Unified database abstraction for the renderer process.
 * Uses Supabase JS client when in Supabase mode,
 * or proxies through IPC to main process when in PG mode.
 *
 * Detection: if VITE_DATABASE_URL is set → PG mode, else → Supabase mode.
 */
import { createClient, SupabaseClient } from '@supabase/supabase-js'

declare global {
  interface Window {
    electronAPI: typeof import('../preload/index').ElectronAPI extends infer T ? T : never
  }
}

const api = window.electronAPI

const DATABASE_URL = import.meta.env.VITE_DATABASE_URL || ''
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const usePg = !!DATABASE_URL

// Supabase client (only created in Supabase mode)
let _supabase: SupabaseClient | null = null
if (!usePg && SUPABASE_URL && SUPABASE_KEY) {
  _supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
    auth: { persistSession: false }
  })
}

// Export raw supabase client for backward compat (null in PG mode)
export const supabase = _supabase

// ── CRUD API ──────────────────────────────────────────────

export async function dbSelect(
  table: string,
  columns = '*',
  filters: Record<string, any> = {},
  options?: { orderBy?: string; ascending?: boolean; limit?: number }
): Promise<any[]> {
  if (usePg) {
    return api.dbSelect({
      table, columns, filters,
      orderBy: options?.orderBy,
      ascending: options?.ascending,
      limit: options?.limit
    })
  } else {
    let q = _supabase!.from(table).select(columns)
    for (const [k, v] of Object.entries(filters)) q = q.eq(k, v)
    if (options?.orderBy) q = q.order(options.orderBy, { ascending: options.ascending ?? true })
    if (options?.limit) q = q.limit(options.limit)
    const { data } = await q
    return data || []
  }
}

export async function dbSelectOne(
  table: string,
  columns = '*',
  filters: Record<string, any> = {}
): Promise<any | null> {
  if (usePg) {
    return api.dbSelectOne({ table, columns, filters })
  } else {
    let q = _supabase!.from(table).select(columns)
    for (const [k, v] of Object.entries(filters)) q = q.eq(k, v)
    const { data } = await q.single()
    return data
  }
}

export async function dbInsert(table: string, data: Record<string, any>): Promise<any | null> {
  if (usePg) {
    return api.dbInsert({ table, data })
  } else {
    const { data: result } = await _supabase!.from(table).insert([data]).select().single()
    return result
  }
}

export async function dbUpdate(table: string, data: Record<string, any>, filters: Record<string, any> = {}): Promise<void> {
  if (usePg) {
    await api.dbUpdate({ table, data, filters })
  } else {
    let q = _supabase!.from(table).update(data)
    for (const [k, v] of Object.entries(filters)) q = q.eq(k, v)
    await q
  }
}

export async function dbDelete(table: string, filters: Record<string, any> = {}): Promise<void> {
  if (usePg) {
    await api.dbDelete({ table, filters })
  } else {
    let q = _supabase!.from(table).delete()
    for (const [k, v] of Object.entries(filters)) q = q.eq(k, v)
    await q
  }
}

// ── Realtime subscriptions ──────────────────────────────────

type SubCallback = (payload: any) => void

interface Subscription {
  id: string
  unsubscribe: () => void
}

export function dbSubscribe(
  channel: string,
  table: string,
  callback: SubCallback,
  options?: { eventType?: string; filter?: string }
): Subscription {
  if (usePg) {
    let subId = ''

    // Set up IPC listener for notifications
    const removeListener = api.onDbNotification((data) => {
      if (data.subId === subId) {
        callback(data.payload)
      }
    })

    // Register subscription in main process
    api.dbSubscribe({
      channel,
      table,
      eventType: options?.eventType || '*',
      filter: options?.filter
    }).then((id: string) => {
      subId = id
    })

    return {
      get id() { return subId },
      unsubscribe: () => {
        removeListener()
        if (subId) api.dbUnsubscribe({ subId })
      }
    }
  } else {
    const sub = _supabase!
      .channel(channel)
      .on('postgres_changes', {
        event: (options?.eventType || '*') as any,
        schema: 'public',
        table,
        filter: options?.filter
      }, (payload: any) => {
        callback(payload.new)
      })
      .subscribe()

    return {
      id: channel,
      unsubscribe: () => {
        _supabase!.removeChannel(sub)
      }
    }
  }
}
