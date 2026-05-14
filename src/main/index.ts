import { app, BrowserWindow, ipcMain, dialog, Tray, Menu, nativeImage, shell, desktopCapturer, screen } from 'electron'
import { autoUpdater } from 'electron-updater'
import { join } from 'path'
import { createClient } from '@supabase/supabase-js'
import WebSocket from 'ws'
import { exec } from 'child_process'
import si from 'systeminformation'
import loudness from 'loudness'

let mainWindow: BrowserWindow | null = null
let supabase: any = null
let pgClient: any = null
let tray: Tray | null = null
let isQuitting = false
let dbMode: 'supabase' | 'pg' = 'supabase'


function createWindow() {
  // Remove default menu bar (File, Edit, View...)
  Menu.setApplicationMenu(null)

  mainWindow = new BrowserWindow({
    width: 900,
    height: 600,
    show: false,
    autoHideMenuBar: true,
    icon: join(__dirname, '../../resources/icon.png'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
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
    { label: 'Відкрити налаштування', click: () => mainWindow?.show() },
    { type: 'separator' },
    { label: 'Вийти', click: () => {
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
  createWindow()
  createTray()
  
  // Start on boot
  app.setLoginItemSettings({
    openAtLogin: true,
    openAsHidden: true
  })

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
    title: isMac ? 'Оберіть програму або файл' : 'Выберите программу або файл'
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

// ══════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════
// Auto-Update Logic (via electron-updater)
// ══════════════════════════════════════════════════════════════

autoUpdater.autoDownload = false // We'll trigger it manually from UI for better UX

ipcMain.handle('check-for-update', async () => {
  try {
    const result = await autoUpdater.checkForUpdates()
    if (result && result.updateInfo) {
      return {
        version: result.updateInfo.version,
        releaseNotes: result.updateInfo.releaseNotes
      }
    }
    return null
  } catch (err) {
    console.error('[Update Check Failed]', err)
    return null
  }
})

ipcMain.on('start-download', () => {
  autoUpdater.downloadUpdate()
})

ipcMain.on('install-update', () => {
  isQuitting = true
  autoUpdater.quitAndInstall()
})

autoUpdater.on('download-progress', (progressObj) => {
  mainWindow?.webContents.send('update-progress', progressObj.percent)
})

autoUpdater.on('update-downloaded', () => {
  mainWindow?.webContents.send('update-ready')
})


// ══════════════════════════════════════════════════════════════
// Database initialization — supports both Supabase and raw PG
// ══════════════════════════════════════════════════════════════
let currentDeviceId: string | null = null
let pollInterval: NodeJS.Timeout | null = null

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
          console.log('[Realtime] Subscription status:', status, err || '')
      })
  }

  // Polling fallback (runs for both Supabase and PG modes)
  // Catches any commands that Realtime might miss
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(() => pollPendingCommands(deviceId), 3000)

  // Mark device as online
  setDeviceOnline(deviceId, true)
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
    // Silently ignore poll errors
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
    console.error('[TeleShift] Failed to update online status:', err)
  }
}

// Mark device offline on quit
app.on('before-quit', async () => {
  if (currentDeviceId) {
    await setDeviceOnline(currentDeviceId, false)
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
        console.error('[PG] Error processing notification:', err)
      }
    })
  } catch (err) {
    console.error('[PG] Connection error:', err)
  }
}

// ══════════════════════════════════════════════════════════════
// IPC CRUD handlers for renderer (used in PostgreSQL mode)
// ══════════════════════════════════════════════════════════════

ipcMain.handle('db-select', async (_event, { table, columns, filters, orderBy, ascending, limit }) => {
  if (dbMode === 'pg' && pgClient) {
    let query = `SELECT ${columns || '*'} FROM ${table}`
    const params: any[] = []
    let idx = 1
    if (filters && Object.keys(filters).length) {
      const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
      query += ' WHERE ' + conds.join(' AND ')
    }
    if (orderBy) query += ` ORDER BY ${orderBy} ${ascending === false ? 'DESC' : 'ASC'}`
    if (limit) query += ` LIMIT ${limit}`
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
  return []
})

ipcMain.handle('db-select-one', async (_event, { table, columns, filters }) => {
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
  return null
})

ipcMain.handle('db-insert', async (_event, { table, data }) => {
  if (dbMode === 'pg' && pgClient) {
    const cols = Object.keys(data).join(', ')
    const placeholders = Object.keys(data).map((_, i) => `$${i + 1}`).join(', ')
    const res = await pgClient.query(`INSERT INTO ${table} (${cols}) VALUES (${placeholders}) RETURNING *`, Object.values(data))
    return res.rows[0] || null
  } else if (supabase) {
    const { data: result } = await supabase.from(table).insert([data]).select().single()
    return result
  }
  return null
})

ipcMain.handle('db-update', async (_event, { table, data, filters }) => {
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
})

ipcMain.handle('db-delete', async (_event, { table, filters }) => {
  if (dbMode === 'pg' && pgClient) {
    const params: any[] = []
    let idx = 1
    let query = `DELETE FROM ${table}`
    if (filters && Object.keys(filters).length) {
      const conds = Object.entries(filters).map(([k, v]) => { params.push(v); return `${k} = $${idx++}` })
      query += ' WHERE ' + conds.join(' AND ')
    }
    await pgClient.query(query, params)
  } else if (supabase) {
    let q = supabase.from(table).delete()
    for (const [k, v] of Object.entries(filters || {})) q = q.eq(k, v)
    await q
  }
})

// ══════════════════════════════════════════════════════════════
// IPC Realtime subscribe (for PG mode, uses LISTEN/NOTIFY)
// ══════════════════════════════════════════════════════════════

const pgListeners = new Map<string, any>()

ipcMain.handle('db-subscribe', async (_event, { channel, table, eventType, filter }) => {
  const subId = `${channel}_${Date.now()}`

  if (dbMode === 'pg' && pgClient) {
    // PG mode — listener is already active from init, 
    // we just need to forward matching notifications to renderer
    const listener = (msg: any) => {
      try {
        const payload = JSON.parse(msg.payload)
        mainWindow?.webContents.send('db-notification', { subId, payload })
      } catch {}
    }
    // Map the NOTIFY channel name from our trigger naming convention
    let pgChannel = 'new_command'
    if (table === 'connections') pgChannel = 'connection_change'
    if (table === 'apps') pgChannel = 'apps_change'
    if (table === 'logs') pgChannel = 'log_insert'

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
})

ipcMain.handle('db-unsubscribe', async (_event, { subId }) => {
  const entry = pgListeners.get(subId)
  if (!entry) return

  if (dbMode === 'pg' && entry.listener) {
    pgClient?.removeListener('notification', entry.listener)
  } else if (entry.sub && supabase) {
    supabase.removeChannel(entry.sub)
  }

  pgListeners.delete(subId)
})


// ══════════════════════════════════════════════════════════════
// Command processing (shared between Supabase and PG modes)
// ══════════════════════════════════════════════════════════════

async function dbUpdate(table: string, data: any, filters: any) {
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
}

async function processCommand(cmd: any) {
    try {
        await dbUpdate('device_commands', { status: 'processing' }, { id: cmd.id })
        let result: any = 'success'

        switch(cmd.command) {
            case 'shutdown':
                if (process.platform === 'darwin') exec('osascript -e "tell application \"System Events\" to shut down"')
                else exec('shutdown /s /t 1')
                break
            case 'reboot':
                if (process.platform === 'darwin') exec('osascript -e "tell application \"System Events\" to restart"')
                else exec('shutdown /r /t 1')
                break
            case 'lock':
                if (process.platform === 'darwin') exec('osascript -e "tell application \"System Events\" to sleep" & pmset displaysleepnow')
                else exec('rundll32.exe user32.dll,LockWorkStation')
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
                        const appName = (appPath.split(/[\\/]/).pop() || '').toLowerCase()
                        
                        // Check by full path or just by process name
                        const isRunning = runningPaths.some(p => p.includes(appPath)) || 
                                          runningNames.some(n => n === appName || n === appName + '.exe')
                        
                        statusMap[app.id] = isRunning
                    }
                    result = JSON.stringify(statusMap)
                } catch (err) {
                    result = 'Error checking processes'
                }
                break
            case 'get_status':
                try {
                    const [bat, disk, cpuLoad, mem, gpu, osInfo] = await Promise.all([
                        si.battery().catch(() => ({ hasBattery: false })),
                        si.fsSize().catch(() => []),
                        si.currentLoad().catch(() => ({ currentLoad: 0 })),
                        si.mem().catch(() => ({ total: 0, used: 0 })),
                        si.graphics().catch(() => ({ controllers: [] })),
                        si.osInfo().catch(() => ({ distro: 'Unknown', release: '', hostname: 'PC' }))
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
                    result = JSON.stringify({ error: e.message })
                }
                break
            case 'get_volume':
                const vol = await loudness.getVolume()
                const muted = await loudness.getMuted()
                result = JSON.stringify({ volume: vol, muted })
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
                
                if (dbMode === 'supabase' && supabase) {
                    // Upload to Supabase Storage and return public URL
                    const fileName = `screenshot_${Date.now()}.png`
                    const { data, error } = await supabase.storage.from('screenshots').upload(fileName, imgBuffer, { contentType: 'image/png' })
                    if (error) throw error
                    const { data: pubData } = supabase.storage.from('screenshots').getPublicUrl(fileName)
                    result = pubData.publicUrl
                } else {
                    // Raw PG mode — encode screenshot as base64
                    result = (imgBuffer as Buffer).toString('base64')
                }
                break
            case 'launch_app':
                if (process.platform === 'darwin') exec(`open "${cmd.payload.path}"`)
                else exec(`start "" "${cmd.payload.path}"`)
                break
            default:
                throw new Error('Unknown command')
        }

        await dbUpdate('device_commands', { status: 'completed', result }, { id: cmd.id })
    } catch (err: any) {
        await dbUpdate('device_commands', { status: 'error', result: err.message }, { id: cmd.id })
    }
}
