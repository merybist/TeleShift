import { contextBridge, ipcRenderer } from 'electron'

const electronAPI = {
  // ── Window controls ──
  showWindow: () => ipcRenderer.send('show-window'),
  quitApp: () => ipcRenderer.send('quit-app'),

  // ── File dialog ──
  selectFile: () => ipcRenderer.invoke('select-file'),

  // ── Startup settings ──
  getLaunchAtStartup: () => ipcRenderer.invoke('get-launch-at-startup'),
  setLaunchAtStartup: (openAtLogin: boolean) => ipcRenderer.invoke('set-launch-at-startup', openAtLogin),

  // ── Auto-update ──
  checkForUpdate: () => ipcRenderer.invoke('check-for-update'),
  installUpdate: () => ipcRenderer.send('install-update'),
  onUpdateAvailable: (callback: (info: { version: string }) => void) => {
    const listener = (_event: any, info: any) => callback(info)
    ipcRenderer.on('update-available', listener)
    return () => ipcRenderer.removeListener('update-available', listener)
  },
  onUpdateProgress: (callback: (percent: number) => void) => {
    const listener = (_event: any, percent: number) => callback(percent)
    ipcRenderer.on('update-progress', listener)
    return () => ipcRenderer.removeListener('update-progress', listener)
  },
  onUpdateReady: (callback: (info: { version: string }) => void) => {
    const listener = (_event: any, info: any) => callback(info)
    ipcRenderer.on('update-ready', listener)
    return () => ipcRenderer.removeListener('update-ready', listener)
  },

  // ── Database CRUD ──
  dbSelect: (params: { table: string; columns?: string; filters?: Record<string, any>; orderBy?: string; ascending?: boolean; limit?: number }) =>
    ipcRenderer.invoke('db-select', params),
  dbSelectOne: (params: { table: string; columns?: string; filters?: Record<string, any> }) =>
    ipcRenderer.invoke('db-select-one', params),
  dbInsert: (params: { table: string; data: Record<string, any> }) =>
    ipcRenderer.invoke('db-insert', params),
  dbUpdate: (params: { table: string; data: Record<string, any>; filters?: Record<string, any> }) =>
    ipcRenderer.invoke('db-update', params),
  dbDelete: (params: { table: string; filters: Record<string, any> }) =>
    ipcRenderer.invoke('db-delete', params),

  // ── Database subscriptions ──
  dbSubscribe: (params: { channel: string; table: string; eventType?: string; filter?: string }) =>
    ipcRenderer.invoke('db-subscribe', params),
  dbUnsubscribe: (params: { subId: string }) =>
    ipcRenderer.invoke('db-unsubscribe', params),
  onDbNotification: (callback: (data: { subId: string; payload: any }) => void) => {
    const listener = (_event: any, data: any) => callback(data)
    ipcRenderer.on('db-notification', listener)
    return () => ipcRenderer.removeListener('db-notification', listener)
  },

  // ── Supabase init ──
  initSupabase: (params: { url: string; key: string; deviceId: string; databaseUrl?: string }) =>
    ipcRenderer.send('init-supabase', params)
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

export type ElectronAPI = typeof electronAPI
