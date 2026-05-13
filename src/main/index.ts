import { app, BrowserWindow, ipcMain, dialog, Tray, Menu, nativeImage } from 'electron'
import { join } from 'path'
import { createClient } from '@supabase/supabase-js'
import WebSocket from 'ws'
import { exec } from 'child_process'
import si from 'systeminformation'
import loudness from 'loudness'
import screenshot from 'screenshot-desktop'

let mainWindow: BrowserWindow | null = null
let supabase: any = null
let tray: Tray | null = null
let isQuitting = false


function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 600,
    show: false, // Show gracefully
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

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
  // Empty icon if no asset provided. In production, provide an icon.png
  const icon = nativeImage.createEmpty()
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
  tray.setToolTip('PC Controller Host')
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
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [{ name: 'Executables', extensions: ['exe'] }]
  })
  return result.filePaths[0]
})

ipcMain.on('quit-app', () => {
  isQuitting = true
  app.exit(0)
})

ipcMain.on('init-supabase', (event, { url, key, deviceId }) => {
  supabase = createClient(url, key, {
    auth: { persistSession: false },
    global: { WebSocket: WebSocket as any }
  })
  
  supabase
    .channel('device_commands_listener')
    .on('postgres_changes', { 
        event: 'INSERT', 
        schema: 'public', 
        table: 'device_commands', 
        filter: `device_id=eq.${deviceId}` 
    }, async (payload: any) => {
        const cmd = payload.new
        if (cmd.status === 'pending') {
           await processCommand(cmd)
        }
    })
    .subscribe()
})

async function processCommand(cmd: any) {
    if (!supabase) return
    try {
        await supabase.from('device_commands').update({ status: 'processing' }).eq('id', cmd.id)
        let result: any = 'success'

        switch(cmd.command) {
            case 'shutdown':
                if (process.platform === 'darwin') exec('shutdown -h now')
                else exec('shutdown /s /t 1')
                break
            case 'reboot':
                if (process.platform === 'darwin') exec('shutdown -r now')
                else exec('shutdown /r /t 1')
                break
            case 'lock':
                if (process.platform === 'darwin') exec('pmset displaysleepnow')
                else exec('rundll32.exe user32.dll,LockWorkStation')
                break
            case 'get_status':
                const bat = await si.battery()
                const disk = await si.fsSize()
                const cDisk = disk.find(d => d.mount === 'C:') || disk[0]
                result = JSON.stringify({
                    battery: bat.hasBattery ? bat.percent : 'Desktop',
                    disk_free: cDisk ? Math.floor(cDisk.available / (1024*1024*1024)) : 0
                })
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
                const imgBuffer = await screenshot()
                const fileName = `screenshot_${Date.now()}.png`
                const { data, error } = await supabase.storage.from('screenshots').upload(fileName, imgBuffer, { contentType: 'image/png' })
                if (error) throw error
                const { data: pubData } = supabase.storage.from('screenshots').getPublicUrl(fileName)
                result = pubData.publicUrl
                break
            case 'launch_app':
                if (process.platform === 'darwin') exec(`open "${cmd.payload.path}"`)
                else exec(`start "" "${cmd.payload.path}"`)
                break
            default:
                throw new Error('Unknown command')
        }

        await supabase.from('device_commands').update({ status: 'completed', result }).eq('id', cmd.id)
    } catch (err: any) {
        await supabase.from('device_commands').update({ status: 'error', result: err.message }).eq('id', cmd.id)
    }
}
