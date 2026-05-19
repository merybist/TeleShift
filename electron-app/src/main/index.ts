import { app, BrowserWindow, ipcMain, dialog, Tray, Menu, nativeImage, shell, desktopCapturer, screen, session } from 'electron'
import { autoUpdater } from 'electron-updater'
import { join } from 'path'
import { createClient } from '@supabase/supabase-js'
import WebSocket from 'ws'
import { execFile, spawn } from 'child_process'
import { existsSync, statSync, writeFileSync, mkdirSync } from 'fs'
import { randomBytes, createCipheriv } from 'crypto'
import { homedir } from 'os'
import si from 'systeminformation'
import loudness from 'loudness'

let mainWindow: BrowserWindow | null = null
let supabase: any = null
let pgClient: any = null
let tray: Tray | null = null
let isQuitting = false
let dbMode: 'supabase' | 'pg' = 'supabase'

// ══════════════════════════════════════════════════════════════
// Security: Whitelists for SQL injection prevention
// ══════════════════════════════════════════════════════════════

const ALLOWED_TABLES = new Set([
  'devices', 'device_commands', 'connections', 'apps', 'logs', 'users', 'settings'
])

const IDENTIFIER_REGEX = /^[a-zA-Z_][a-zA-Z0-9_]*$/

function validateIdentifier(name: string): boolean {
  return IDENTIFIER_REGEX.test(name) && name.length <= 64
}

function validateTableName(table: string): boolean {
  return ALLOWED_TABLES.has(table)
}

function validateColumns(columns: string): boolean {
  if (columns === '*') return true
  return columns.split(',').every(col => validateIdentifier(col.trim()))
}

// Security: Whitelist for LISTEN channels
const ALLOWED_PG_CHANNELS = new Set([
  'new_command', 'connection_change', 'apps_change', 'log_insert'
])

// Security: Validate file path for launch_app
function validateAppPath(filePath: string): boolean {
  // Reject shell metacharacters
  const dangerousChars = /[;&|`$(){}[\]!#~<>*?\n\r]/
  if (dangerousChars.test(filePath)) return false

  // Must be an absolute path
  if (process.platform === 'win32') {
    if (!/^[a-zA-Z]:\\/.test(filePath) && !filePath.startsWith('\\\\')) return false
  } else {
    if (!filePath.startsWith('/')) return false
  }

  // Path must exist and be a file or .app bundle
  try {
    const stat = statSync(filePath)
    return stat.isFile() || stat.isDirectory() // .app bundles are directories on macOS
  } catch {
    return false
  }
}


// ══════════════════════════════════════════════════════════════
// macOS LaunchAgent — auto-start without code signing
// ══════════════════════════════════════════════════════════════

const PLIST_LABEL = 'com.teleshift.agent'

function getLaunchAgentPath(): string {
  return join(homedir(), 'Library', 'LaunchAgents', `${PLIST_LABEL}.plist`)
}

function setupAutoLaunch(): void {
  if (process.platform !== 'darwin') {
    app.setLoginItemSettings({ openAtLogin: true, openAsHidden: true })
    return
  }

  const plistPath = getLaunchAgentPath()
  if (existsSync(plistPath)) return

  const appPath = app.getPath('exe')
  const plistContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${appPath}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
`

  const dir = join(homedir(), 'Library', 'LaunchAgents')
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
  writeFileSync(plistPath, plistContent, 'utf-8')
  console.log('[TeleShift] LaunchAgent created:', plistPath)
}

function removeAutoLaunch(): void {
  if (process.platform !== 'darwin') {
    app.setLoginItemSettings({ openAtLogin: false })
    return
  }

  const plistPath = getLaunchAgentPath()
  if (existsSync(plistPath)) {
    require('fs').unlinkSync(plistPath)
    console.log('[TeleShift] LaunchAgent removed:', plistPath)
  }
}

function createWindow() {
  // Remove default menu bar (File, Edit, View...)
  Menu.setApplicationMenu(null)

  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width,
    height,
    show: false,
    autoHideMenuBar: true,
    icon: join(__dirname, '../../resources/icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, '../preload/index.js')
    }
  })

  // Start hidden — the app lives in the system tray
  // Window only shows via tray menu or update notification

  // Prevent closing, hide instead
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow?.hide()
    }
  })

  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function createTray() {
  const iconPath = join(__dirname, '../../resources/icon.png')
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  tray = new Tray(icon)
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Settings', click: () => mainWindow?.show() },
    { type: 'separator' },
    { label: 'Quit', click: () => {
        isQuitting = true
        app.quit()
      }
    }
  ])
  tray.setToolTip('TeleShift')
  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => mainWindow?.show())
}

app.whenReady().then(() => {
  // Content Security Policy
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://*.supabase.co wss://*.supabase.co"
        ]
      }
    })
  })

  createWindow()
  createTray()

  // Show window on first launch (no device configured yet)
  // After connection is established, it will hide to tray
  mainWindow?.show()

  // Start on boot via LaunchAgent (works without code signing on macOS)
  setupAutoLaunch()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else mainWindow?.show()
  })
})

app.on('window-all-closed', () => {
  // Do nothing to keep it running in background via Tray
})


ipcMain.handle('select-file', async () => {
  const isMac = process.platform === 'darwin'
  const result = await dialog.showOpenDialog({
    properties: isMac ? ['openFile', 'openDirectory'] : ['openFile'],
    filters: [
      { name: 'Applications/Executables', extensions: isMac ? ['app', 'exe', 'sh', 'command'] : ['exe', 'lnk', 'bat', 'cmd'] },
      { name: 'All Files', extensions: ['*'] }
    ],
    title: isMac ? 'Select an application or file' : 'Select an application or file'
  })
  
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.on('show-window', () => {
  mainWindow?.show()
  mainWindow?.focus()
})

ipcMain.on('quit-app', () => {
  isQuitting = true
  app.exit(0)
})

ipcMain.handle('get-launch-at-startup', () => {
  if (process.platform === 'darwin') {
    return existsSync(getLaunchAgentPath())
  }
  return app.getLoginItemSettings().openAtLogin
})

ipcMain.handle('set-launch-at-startup', (_event, openAtLogin: boolean) => {
  if (openAtLogin) {
    setupAutoLaunch()
  } else {
    removeAutoLaunch()
  }
  console.log(`[TeleShift] Launch at startup set to: ${openAtLogin}`)
  return true
})

// ══════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════
// Auto-Update Logic (via electron-updater)
// ══════════════════════════════════════════════════════════════

autoUpdater.autoDownload = true
autoUpdater.autoInstallOnAppQuit = true

autoUpdater.on('update-available', (info) => {
  console.log(`[TeleShift] Update available: v${info.version}`)
  mainWindow?.webContents.send('update-available', { version: info.version })
})

autoUpdater.on('download-progress', (progressObj) => {
  mainWindow?.webContents.send('update-progress', progressObj.percent)
})

autoUpdater.on('update-downloaded', (info) => {
  console.log(`[TeleShift] Update downloaded: v${info.version}`)
  mainWindow?.webContents.send('update-ready', { version: info.version })
})

autoUpdater.on('error', (err) => {
  console.error('[TeleShift][auto-update]', err.message)
})

// Check on launch + every 4 hours
app.whenReady().then(() => {
  setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 10_000)
  setInterval(() => autoUpdater.checkForUpdates().catch(() => {}), 4 * 60 * 60 * 1000)
})

ipcMain.handle('check-for-update', async () => {
  try {
    const result = await autoUpdater.checkForUpdates()
    if (result?.updateInfo) {
      return { version: result.updateInfo.version }
    }
    return null
  } catch (err) {
    return null
  }
})

ipcMain.on('install-update', () => {
  isQuitting = true
  autoUpdater.quitAndInstall(false, true)
  setTimeout(() => app.exit(0), 1000)
})


// ══════════════════════════════════════════════════════════════
// Database initialization — supports both Supabase and raw PG
// ══════════════════════════════════════════════════════════════
let currentDeviceId: string | null = null
let pollInterval: NodeJS.Timeout | null = null
let heartbeatInterval: NodeJS.Timeout | null = null

ipcMain.on('init-supabase', (event, { url, key, deviceId, databaseUrl }) => {
  currentDeviceId = deviceId
  console.log('[TeleShift] init-supabase called, deviceId:', deviceId, 'pgMode:', !!databaseUrl)

  if (databaseUrl) {
    // ── Raw PostgreSQL mode ──
    dbMode = 'pg'
    initPostgres(databaseUrl, deviceId)
  } else {
    // ── Supabase mode ──
    dbMode = 'supabase'
    supabase = createClient(url, key, {
      auth: { persistSession: false },
      realtime: { transport: WebSocket as any }
    })
    
    // Realtime subscription (primary)
    supabase
      .channel('device_commands_listener')
      .on('postgres_changes', { 
          event: 'INSERT', 
          schema: 'public', 
          table: 'device_commands', 
          filter: `device_id=eq.${deviceId}` 
      }, async (payload: any) => {
          console.log('[Realtime] Got command event:', payload.new?.command)
          const cmd = payload.new
          if (cmd.status === 'pending') {
             await processCommand(cmd)
          }
      })
      .subscribe((status: string, err: any) => {
          if (err) console.error('[TeleShift][realtime-subscribe]', err)
          console.log('[Realtime] Subscription status:', status, err || '')
      })
  }

  // Polling fallback (runs for both Supabase and PG modes)
  // Catches any commands that Realtime might miss
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(() => pollPendingCommands(deviceId), 3000)

  // Mark device as online
  setDeviceOnline(deviceId, true)

  // Heartbeat mechanism: update last_seen_at every 30 seconds
  if (heartbeatInterval) clearInterval(heartbeatInterval)
  heartbeatInterval = setInterval(async () => {
    try {
      const data = { last_seen_at: new Date().toISOString() }
      if (dbMode === 'supabase' && supabase) {
        await supabase.from('devices').update(data).eq('id', deviceId)
      } else if (dbMode === 'pg' && pgClient) {
        await pgClient.query('UPDATE devices SET last_seen_at = $1 WHERE id = $2', [data.last_seen_at, deviceId])
      }
      console.log('[TeleShift][heartbeat] Status updated')
    } catch (e) {
      console.error('[TeleShift][heartbeat] Failed:', e)
    }
  }, 30000)
})

async function pollPendingCommands(deviceId: string) {
  try {
    let rows: any[] = []
    if (dbMode === 'supabase' && supabase) {
      const { data } = await supabase
        .from('device_commands')
        .select('*')
        .eq('device_id', deviceId)
        .eq('status', 'pending')
      rows = data || []
    } else if (dbMode === 'pg' && pgClient) {
      const res = await pgClient.query(
        'SELECT * FROM device_commands WHERE device_id = $1 AND status = $2',
        [deviceId, 'pending']
      )
      rows = res.rows
    }
    for (const cmd of rows) {
      console.log('[Poll] Found pending command:', cmd.command)
      await processCommand(cmd)
    }
  } catch (err) {
    console.error('[TeleShift][polling]', err)
  }
}

async function setDeviceOnline(deviceId: string, online: boolean) {
  try {
    const data = { is_online: online, last_seen_at: new Date().toISOString() }
    if (dbMode === 'supabase' && supabase) {
      await supabase.from('devices').update(data).eq('id', deviceId)
    } else if (dbMode === 'pg' && pgClient) {
      await pgClient.query(
        'UPDATE devices SET is_online = $1, last_seen_at = $2 WHERE id = $3',
        [online, data.last_seen_at, deviceId]
      )
    }
    console.log(`[TeleShift] Device marked ${online ? 'ONLINE' : 'OFFLINE'}`)
  } catch (err) {
    console.error('[TeleShift][online-status]', err)
  }
}

// Mark device offline on quit
app.on('before-quit', (event) => {
  isQuitting = true
  if (currentDeviceId) {
    setDeviceOnline(currentDeviceId, false)
  }
})

async function initPostgres(connectionString: string, deviceId: string) {
  try {
    const pg = require('pg')
    pgClient = new pg.Client({ connectionString })
    await pgClient.connect()
    console.log('[PG] Connected to PostgreSQL')

    await pgClient.query('LISTEN new_command')
    console.log('[PG] Listening for new_command notifications')

    pgClient.on('notification', async (msg: any) => {
      try {
        const cmd = JSON.parse(msg.payload)
        if (cmd.device_id === deviceId && cmd.status === 'pending') {
          // Re-fetch full command data
          const res = await pgClient.query('SELECT * FROM device_commands WHERE id = $1', [cmd.id])
          if (res.rows.length > 0) {
            await processCommand(res.rows[0])
          }
        }
      } catch (err) {
        console.error('[TeleShift][pg-notification]', err)
      }
    })
  } catch (err) {
    console.error('[TeleShift][pg-connection]', err)
  }
}

// ══════════════════════════════════════════════════════════════
// IPC CRUD handlers for renderer (used in PostgreSQL mode)
// ══════════════════════════════════════════════════════════════

ipcMain.handle('db-select', async (_event, { table, columns, filters, orderBy, ascending, limit }) => {
  try {
    if (!validateTableName(table)) throw new Error('Invalid table name')
    if (columns && !validateColumns(columns)) throw new Error('Invalid column names')
    if (orderBy && !validateIdentifier(orderBy)) throw new Error('Invalid orderBy column')
    if (filters) {
      for (const k of Object.keys(filters)) {
        if (!validateIdentifier(k)) throw new Error('Invalid filter column name')
      }
    }

    if (dbMode === 'pg' && pgClient) {
      let query = `SELECT ${columns || '*'} FROM ${table}`
      const params: any[] = []
      let idx = 1
      if (filters && Object.keys(filters).length) {
        const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
        query += ' WHERE ' + conds.join(' AND ')
      }
      if (orderBy) query += ` ORDER BY ${orderBy} ${ascending === false ? 'DESC' : 'ASC'}`
      if (limit) {
        params.push(limit)
        query += ` LIMIT $${idx++}`
      }
      const res = await pgClient.query(query, params)
      return res.rows
    } else if (supabase) {
      let q = supabase.from(table).select(columns || '*')
      for (const [k, v] of Object.entries(filters || {})) q = q.eq(k, v)
      if (orderBy) q = q.order(orderBy, { ascending: ascending !== false })
      if (limit) q = q.limit(limit)
      const { data } = await q
      return data || []
    }
  } catch (e) {
    console.error('[TeleShift][db-select]', e)
  }
  return []
})

ipcMain.handle('db-select-one', async (_event, { table, columns, filters }) => {
  try {
    if (!validateTableName(table)) throw new Error('Invalid table name')
    if (columns && !validateColumns(columns)) throw new Error('Invalid column names')
    if (filters) {
      for (const k of Object.keys(filters)) {
        if (!validateIdentifier(k)) throw new Error('Invalid filter column name')
      }
    }

    if (dbMode === 'pg' && pgClient) {
      let query = `SELECT ${columns || '*'} FROM ${table}`
      const params: any[] = []
      let idx = 1
      if (filters && Object.keys(filters).length) {
        const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
        query += ' WHERE ' + conds.join(' AND ')
      }
      query += ' LIMIT 1'
      const res = await pgClient.query(query, params)
      return res.rows[0] || null
    } else if (supabase) {
      let q = supabase.from(table).select(columns || '*')
      for (const [k, v] of Object.entries(filters || {})) q = q.eq(k, v)
      const { data } = await q.single()
      return data
    }
  } catch (e) {
    console.error('[TeleShift][db-select-one]', e)
  }
  return null
})

ipcMain.handle('db-insert', async (_event, { table, data }) => {
  try {
    if (!validateTableName(table)) throw new Error('Invalid table name')
    for (const k of Object.keys(data)) {
      if (!validateIdentifier(k)) throw new Error('Invalid column name in data')
    }

    if (dbMode === 'pg' && pgClient) {
      const cols = Object.keys(data).join(', ')
      const placeholders = Object.keys(data).map((_, i) => `$${i + 1}`).join(', ')
      const res = await pgClient.query(`INSERT INTO ${table} (${cols}) VALUES (${placeholders}) RETURNING *`, Object.values(data))
      return res.rows[0] || null
    } else if (supabase) {
      const { data: result } = await supabase.from(table).insert([data]).select().single()
      return result
    }
  } catch (e) {
    console.error('[TeleShift][db-insert]', e)
  }
  return null
})

ipcMain.handle('db-update', async (_event, { table, data, filters }) => {
  try {
    if (!validateTableName(table)) throw new Error('Invalid table name')
    for (const k of Object.keys(data)) {
      if (!validateIdentifier(k)) throw new Error('Invalid column name in data')
    }
    if (filters) {
      for (const k of Object.keys(filters)) {
        if (!validateIdentifier(k)) throw new Error('Invalid filter column name')
      }
    }

    if (dbMode === 'pg' && pgClient) {
      const params: any[] = []
      let idx = 1
      const setParts = Object.entries(data).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
      let query = `UPDATE ${table} SET ${setParts.join(', ')}`
      if (filters && Object.keys(filters).length) {
        const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
        query += ' WHERE ' + conds.join(' AND ')
      }
      await pgClient.query(query, params)
    } else if (supabase) {
      let q = supabase.from(table).update(data)
      for (const [k, v] of Object.entries(filters || {})) q = q.eq(k, v)
      await q
    }
  } catch (e) {
    console.error('[TeleShift][db-update]', e)
  }
})

ipcMain.handle('db-delete', async (_event, { table, filters }) => {
  try {
    if (!validateTableName(table)) throw new Error('Invalid table name')
    if (!filters || Object.keys(filters).length === 0) {
      throw new Error('DELETE without filters is not allowed')
    }
    for (const k of Object.keys(filters)) {
      if (!validateIdentifier(k)) throw new Error('Invalid filter column name')
    }

    if (dbMode === 'pg' && pgClient) {
      const params: any[] = []
      let idx = 1
      let query = `DELETE FROM ${table}`
      const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
      query += ' WHERE ' + conds.join(' AND ')
      await pgClient.query(query, params)
    } else if (supabase) {
      let q = supabase.from(table).delete()
      for (const [k, v] of Object.entries(filters)) q = q.eq(k, v)
      await q
    }
  } catch (e) {
    console.error('[TeleShift][db-delete]', e)
  }
})

// ══════════════════════════════════════════════════════════════
// IPC Realtime subscribe (for PG mode, uses LISTEN/NOTIFY)
// ══════════════════════════════════════════════════════════════

const pgListeners = new Map<string, any>()

ipcMain.handle('db-subscribe', async (_event, { channel, table, eventType, filter }) => {
  try {
    const subId = `${channel}_${Date.now()}`

    if (dbMode === 'pg' && pgClient) {
      // PG mode — listener is already active from init,
      // we just need to forward matching notifications to renderer
      const listener = (msg: any) => {
        try {
          const payload = JSON.parse(msg.payload)
          mainWindow?.webContents.send('db-notification', { subId, payload })
        } catch (e) {
          console.error('[TeleShift][pg-notification-parse]', e)
        }
      }
      // Map the NOTIFY channel name from our trigger naming convention
      let pgChannel = 'new_command'
      if (table === 'connections') pgChannel = 'connection_change'
      if (table === 'apps') pgChannel = 'apps_change'
      if (table === 'logs') pgChannel = 'log_insert'

      // Validate channel against whitelist
      if (!ALLOWED_PG_CHANNELS.has(pgChannel)) {
        throw new Error(`Invalid PG channel: ${pgChannel}`)
      }

      await pgClient.query(`LISTEN ${pgChannel}`)
      pgClient.on('notification', listener)
      pgListeners.set(subId, { listener, pgChannel })
    } else if (supabase) {
      const sub = supabase
        .channel(channel)
        .on('postgres_changes', { event: eventType || '*', schema: 'public', table, filter }, (payload: any) => {
          mainWindow?.webContents.send('db-notification', { subId, payload: payload.new })
        })
        .subscribe()
      pgListeners.set(subId, { sub })
    }

    return subId
  } catch (e) {
    console.error('[TeleShift][db-subscribe]', e)
    return null
  }
})

ipcMain.handle('db-unsubscribe', async (_event, { subId }) => {
  try {
    const entry = pgListeners.get(subId)
    if (!entry) return

    if (dbMode === 'pg' && entry.listener) {
      pgClient?.removeListener('notification', entry.listener)
    } else if (entry.sub && supabase) {
      supabase.removeChannel(entry.sub)
    }

    pgListeners.delete(subId)
  } catch (e) {
    console.error('[TeleShift][db-unsubscribe]', e)
  }
})


// ══════════════════════════════════════════════════════════════
// Command processing (shared between Supabase and PG modes)
// ══════════════════════════════════════════════════════════════

async function dbUpdate(table: string, data: any, filters: any) {
  try {
    if (dbMode === 'pg' && pgClient) {
      const params: any[] = []
      let idx = 1
      const setParts = Object.entries(data).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
      let query = `UPDATE ${table} SET ${setParts.join(', ')}`
      if (filters) {
        const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
        query += ' WHERE ' + conds.join(' AND ')
      }
      await pgClient.query(query, params)
    } else if (supabase) {
      let q = supabase.from(table).update(data)
      for (const [k, v] of Object.entries(filters || {})) q = q.eq(k, v)
      await q
    }
  } catch (e) {
    console.error('[TeleShift][command-update-db]', e)
  }
}

async function processCommand(cmd: any) {
    try {
        await dbUpdate('device_commands', { status: 'processing' }, { id: cmd.id })
        let result: any = 'success'

        switch(cmd.command) {
            case 'shutdown':
                await new Promise<void>((resolve, reject) => {
                    if (process.platform === 'darwin') {
                        execFile('osascript', ['-e', 'tell application "System Events" to shut down'], (err) => {
                            if (err) { console.error('[TeleShift][shutdown]', err); reject(err) }
                            else resolve()
                        })
                    } else {
                        execFile('shutdown', ['/s', '/t', '1'], (err) => {
                            if (err) { console.error('[TeleShift][shutdown]', err); reject(err) }
                            else resolve()
                        })
                    }
                })
                break
            case 'reboot':
                await new Promise<void>((resolve, reject) => {
                    if (process.platform === 'darwin') {
                        execFile('osascript', ['-e', 'tell application "System Events" to restart'], (err) => {
                            if (err) { console.error('[TeleShift][reboot]', err); reject(err) }
                            else resolve()
                        })
                    } else {
                        execFile('shutdown', ['/r', '/t', '1'], (err) => {
                            if (err) { console.error('[TeleShift][reboot]', err); reject(err) }
                            else resolve()
                        })
                    }
                })
                break
            case 'lock':
                await new Promise<void>((resolve, reject) => {
                    if (process.platform === 'darwin') {
                        execFile('pmset', ['displaysleepnow'], (err) => {
                            if (err) { console.error('[TeleShift][lock]', err); reject(err) }
                            else resolve()
                        })
                    } else {
                        execFile('rundll32.exe', ['user32.dll,LockWorkStation'], (err) => {
                            if (err) { console.error('[TeleShift][lock]', err); reject(err) }
                            else resolve()
                        })
                    }
                })
                break
            case 'check_apps':
                try {
                    const apps = cmd.payload?.apps || []
                    const processes = await si.processes()
                    const runningPaths = processes.list.map(p => p.path.toLowerCase())
                    const runningNames = processes.list.map(p => p.name.toLowerCase())

                    const statusMap: any = {}
                    for (const app of apps) {
                        const appPath = app.path.toLowerCase()
                        const fileName = (appPath.split(/[\\/]/).pop() || '').toLowerCase()
                        const fileNameNoExt = fileName.replace(/\.[^/.]+$/, "")

                        const isRunning = runningPaths.some(p => p.includes(appPath)) ||
                                          runningNames.some(n =>
                                            n === fileName ||
                                            n === fileNameNoExt ||
                                            n.includes(fileNameNoExt)
                                          )

                        statusMap[app.id] = isRunning
                    }
                    result = JSON.stringify(statusMap)
                } catch (err) {
                    console.error('[TeleShift][check_apps]', err)
                    result = 'Error checking processes: ' + (err as any).message
                }
                break
            case 'get_status':
                try {
                    const [bat, disk, cpuLoad, mem, gpu, osInfo] = await Promise.all([
                        si.battery().catch((e) => { console.error('[TeleShift][status-battery]', e); return { hasBattery: false } }),
                        si.fsSize().catch((e) => { console.error('[TeleShift][status-disk]', e); return [] }),
                        si.currentLoad().catch((e) => { console.error('[TeleShift][status-cpu]', e); return { currentLoad: 0 } }),
                        si.mem().catch((e) => { console.error('[TeleShift][status-ram]', e); return { total: 0, used: 0 } }),
                        si.graphics().catch((e) => { console.error('[TeleShift][status-gpu]', e); return { controllers: [] } }),
                        si.osInfo().catch((e) => { console.error('[TeleShift][status-os]', e); return { distro: 'Unknown', release: '', hostname: 'PC' } })
                    ])
                    const cDisk = (disk as any[]).find(d => d.mount === 'C:') || disk[0]
                    const gpuInfo = (gpu as any).controllers?.[0]
                    const statusData: any = {
                        cpu_load: Math.round((cpuLoad as any).currentLoad || 0),
                        ram_total: Math.round(((mem as any).total || 0) / (1024*1024*1024)),
                        ram_used: Math.round(((mem as any).used || 0) / (1024*1024*1024)),
                        ram_percent: Math.round(((mem as any).used / (mem as any).total * 100) || 0),
                        disk_total: cDisk ? Math.round(cDisk.size / (1024*1024*1024)) : 0,
                        disk_used: cDisk ? Math.round(cDisk.used / (1024*1024*1024)) : 0,
                        disk_free: cDisk ? Math.round(cDisk.available / (1024*1024*1024)) : 0,
                        gpu_name: gpuInfo?.model || 'N/A',
                        gpu_temp: gpuInfo?.temperatureGpu || null,
                        gpu_usage: gpuInfo?.utilizationGpu || null,
                        os: `${(osInfo as any).distro} ${(osInfo as any).release}`,
                        hostname: (osInfo as any).hostname,
                        uptime_seconds: Math.round(require('os').uptime())
                    }
                    if ((bat as any).hasBattery) {
                        statusData.battery = (bat as any).percent
                        statusData.battery_charging = (bat as any).isCharging
                    }
                    result = JSON.stringify(statusData)
                } catch (e: any) {
                    console.error('[TeleShift][get_status]', e)
                    result = JSON.stringify({ error: e.message })
                }
                break
            case 'get_volume':
                const vol = await loudness.getVolume()
                const muted = await loudness.getMuted()
                result = JSON.stringify({ volume: vol, muted })
                break
            case 'show_message':
                const msg = cmd.payload?.text || 'Message from TeleShift'
                dialog.showMessageBox(mainWindow!, {
                    type: 'info',
                    title: 'TeleShift Message',
                    message: msg,
                    buttons: ['OK']
                })
                result = 'success'
                break
            case 'set_volume':
                const action = cmd.payload.action
                let currentVol = await loudness.getVolume()
                if (action === 'up') await loudness.setVolume(Math.min(100, currentVol + 10))
                else if (action === 'down') await loudness.setVolume(Math.max(0, currentVol - 10))
                else if (action === 'mute') {
                    const isMuted = await loudness.getMuted()
                    await loudness.setMuted(!isMuted)
                }
                const newVol = await loudness.getVolume()
                const newMute = await loudness.getMuted()
                result = JSON.stringify({ volume: newVol, muted: newMute })
                break
            case 'take_screenshot':
                const primaryDisplay = screen.getPrimaryDisplay()
                const { width, height } = primaryDisplay.size

                const sources = await desktopCapturer.getSources({
                    types: ['screen'],
                    thumbnailSize: { width, height }
                })

                const source = sources[0] // Primary screen
                if (!source) throw new Error('No screen source found')

                const imgBuffer = source.thumbnail.toPNG()

                // Encrypt screenshot with AES-256-GCM
                const encKey = randomBytes(32)
                const iv = randomBytes(12)
                const cipher = createCipheriv('aes-256-gcm', encKey, iv)
                const encrypted = Buffer.concat([cipher.update(imgBuffer), cipher.final()])
                const authTag = cipher.getAuthTag()

                // Store encrypted data as base64 in the result field (no Supabase Storage)
                const encryptedPayload = JSON.stringify({
                    encrypted: encrypted.toString('base64'),
                    iv: iv.toString('base64'),
                    authTag: authTag.toString('base64'),
                    key: encKey.toString('base64')
                })
                result = encryptedPayload

                // Auto-delete the result after 3 seconds
                const screenshotCmdId = cmd.id
                setTimeout(async () => {
                    try {
                        await dbUpdate('device_commands', { result: null }, { id: screenshotCmdId })
                        console.log('[TeleShift][screenshot] Auto-deleted encrypted screenshot data')
                    } catch (e) {
                        console.error('[TeleShift][screenshot-cleanup]', e)
                    }
                }, 3000)
                break
            case 'launch_app':
                const appPath = cmd.payload?.path
                if (!appPath || !validateAppPath(appPath)) {
                    throw new Error('Invalid or non-existent application path')
                }
                await new Promise<void>((resolve, reject) => {
                    if (process.platform === 'darwin') {
                        execFile('open', [appPath], (err) => {
                            if (err) { console.error('[TeleShift][launch_app]', err); reject(err) }
                            else resolve()
                        })
                    } else {
                        // On Windows, use spawn with shell:false to avoid injection
                        const child = spawn(appPath, [], { detached: true, stdio: 'ignore' })
                        child.unref()
                        child.on('error', (err) => {
                            console.error('[TeleShift][launch_app]', err)
                            reject(err)
                        })
                        resolve()
                    }
                })
                break
            default:
                throw new Error('Unknown command: ' + cmd.command)
        }

        await dbUpdate('device_commands', { status: 'completed', result }, { id: cmd.id })
    } catch (err: any) {
        console.error('[TeleShift][command-handler]', err)
        await dbUpdate('device_commands', { status: 'error', result: err.message }, { id: cmd.id })
    }
}
