import React, { useEffect, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { nanoid } from 'nanoid'
import { QRCodeSVG } from 'qrcode.react'
import { dbSelect, dbSelectOne, dbInsert, dbUpdate, dbDelete, dbSubscribe, usePg } from '../db'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, RefreshCw } from 'lucide-react'
const { ipcRenderer } = require('electron')

export default function ConnectionPage() {
  const [deviceId, setDeviceId] = useState(localStorage.getItem('device_id'))
  const [internalId, setInternalId] = useState<string | null>(null)
  const [hash, setHash] = useState('')
  const [connection, setConnection] = useState<any>(null)
  const [timeLeft, setTimeLeft] = useState(120)
  const [error, setError] = useState<string | null>(null)
  const [launchAtStartup, setLaunchAtStartup] = useState(false)
  const botName = 'merycontrolbot'

  useEffect(() => {
    initDevice()
    checkLaunchSettings()
  }, [])

  async function checkLaunchSettings() {
    try {
      const state = await ipcRenderer.invoke('get-launch-at-startup')
      setLaunchAtStartup(state)
    } catch (err) {
      console.error('[TeleShift][startup-check]', err)
    }
  }

  async function toggleLaunchAtStartup() {
    try {
      const newState = !launchAtStartup
      await ipcRenderer.invoke('set-launch-at-startup', newState)
      setLaunchAtStartup(newState)
    } catch (err) {
      console.error('[TeleShift][startup-toggle]', err)
    }
  }

  useEffect(() => {
    if (!internalId) return
    ipcRenderer.send('init-supabase', {
      url: import.meta.env.VITE_SUPABASE_URL,
      key: import.meta.env.VITE_SUPABASE_ANON_KEY,
      deviceId: internalId,
      databaseUrl: import.meta.env.VITE_DATABASE_URL || ''
    })
  }, [internalId])

  useEffect(() => {
    if (!internalId) return
    fetchConnection()
    const sub = dbSubscribe(
      'connections_changes',
      'connections',
      (payload) => setConnection(payload),
      { filter: `device_id=eq.${internalId}` }
    )
    return () => sub.unsubscribe()
  }, [internalId])

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (internalId && !connection?.is_active) {
      interval = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            generateNewHash()
            return 120
          }
          return prev - 1
        })
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [internalId, connection?.is_active])

  async function initDevice() {
    try {
      let currentId = localStorage.getItem('device_id')
      if (!currentId) {
        currentId = uuidv4()
        localStorage.setItem('device_id', currentId)
      }
      setDeviceId(currentId)

      let dev = await dbSelectOne('devices', 'id', { device_id: currentId })
      if (!dev) {
        console.log('[Connection] Registering new device...')
        const newDev = await dbInsert('devices', {
          device_id: currentId,
          name: 'PC'
        })
        dev = newDev
        if (dev) {
          await dbInsert('settings', { device_id: dev.id })
        }
      }
      
      if (dev) {
        setInternalId(dev.id)
        setError(null)
      } else {
        throw new Error('Could not initialize device in database.')
      }
    } catch (err: any) {
      console.error('[Connection] Init error:', err)
      setError(err.message || 'Database connection error')
    }
  }

  async function hardReset() {
    localStorage.clear()
    window.location.reload()
  }

  async function fetchConnection() {
    if (!internalId) return
    const rows = await dbSelect('connections', '*', { device_id: internalId })
    const data = rows[0] || null
    if (data) {
      setConnection(data)
      setHash(data.hash_token)
      setTimeLeft(120)
    } else {
      generateNewHash()
    }
  }

  async function generateNewHash() {
    if (!internalId) return
    const newHash = nanoid(12)
    await dbDelete('connections', { device_id: internalId })
    await dbDelete('device_commands', { device_id: internalId })
    await dbInsert('connections', {
      device_id: internalId,
      hash_token: newHash
    })
    setHash(newHash)
    setConnection(null)
    setTimeLeft(120)
  }

  async function resetConnection() {
    if (!connection) return
    await dbUpdate('connections', { is_active: false }, { id: connection.id })
    generateNewHash()
  }

  const deepLink = `https://t.me/${botName}?start=${hash}`
  const progressPercent = (timeLeft / 120) * 100

  return (
    <div className="max-w-2xl mx-auto h-full flex flex-col justify-center pb-2">
      <AnimatePresence mode="wait">
      {connection?.is_active ? (
        <motion.div 
          key="connected"
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: -20 }}
          className="bg-green-500/10 p-10 rounded-3xl border border-green-500/30 text-center w-full shadow-2xl shadow-green-500/10"
        >
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
            className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"
          >
            <CheckCircle2 size={48} className="text-green-400" />
          </motion.div>
          <h3 className="text-3xl font-bold text-green-400 mb-2">Підключено</h3>
          <p className="text-xl text-gray-300">Користувач: <span className="font-bold text-white">@{connection.username}</span></p>
          <button 
            onClick={resetConnection} 
            className="mt-10 px-8 py-4 bg-red-500/20 hover:bg-red-500/40 text-red-400 border border-red-500/30 rounded-2xl transition-all w-full font-bold shadow-lg flex items-center justify-center gap-2"
          >
            <RefreshCw size={20} />
            Скинути підключення
          </button>
        </motion.div>
      ) : (
        <motion.div 
          key="disconnected"
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: -20 }}
          className="flex flex-col items-center bg-gray-800/40 p-6 rounded-3xl shadow-2xl border border-gray-700/50 w-full flex-1 justify-center min-h-0"
        >
          <div className="text-center mb-4 shrink-0">
            <h2 className="text-2xl font-black mb-1 text-white">Зв'язок з ботом</h2>
            <p className="text-gray-400 text-sm">Відскануйте QR-код або введіть код</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-2xl w-full text-center">
              <p className="text-red-400 text-sm mb-2">{error}</p>
              <button 
                onClick={hardReset}
                className="text-xs font-bold text-white bg-red-500/40 hover:bg-red-500/60 px-3 py-1 rounded-lg transition-all"
              >
                Скинути все та почати заново
              </button>
            </div>
          )}

          {!error && !hash && (
             <div className="mb-6 flex flex-col items-center gap-4">
               <RefreshCw className="animate-spin text-blue-500" size={32} />
               <p className="text-gray-500 text-sm italic">Ініціалізація бази даних...</p>
             </div>
          )}

          {hash && !error && (
            <motion.div 
              animate={{ boxShadow: ['0px 0px 0px 0px rgba(59,130,246,0)', '0px 0px 30px 10px rgba(59,130,246,0.2)', '0px 0px 0px 0px rgba(59,130,246,0)'] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="bg-white p-4 rounded-3xl shadow-inner mb-6 shrink-0"
            >
              <QRCodeSVG value={deepLink} size={160} level="H" />
            </motion.div>
          )}
          
          <div className="flex flex-col items-center w-full max-w-sm mx-auto shrink-0">
            <div className="flex justify-between items-end w-full px-2 mb-2">
              <span className="text-xs text-gray-400 uppercase tracking-widest font-bold">Унікальний код</span>
              <span className="text-[10px] font-mono text-blue-400 bg-blue-500/10 px-2 py-1 rounded-md">{Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}</span>
            </div>
            
            <div className="relative w-full mb-4">
               <div 
                 className="bg-gray-900/80 px-6 py-4 rounded-2xl border border-gray-700 w-full text-center cursor-pointer hover:bg-gray-900 transition-colors group overflow-hidden" 
                 onClick={() => navigator.clipboard.writeText(hash)}
               >
                 <code className="relative z-10 text-blue-400 font-mono text-2xl tracking-[0.2em] group-hover:text-blue-300 transition-colors">{hash || '...'}</code>
                 <div className="absolute bottom-0 left-0 h-1 bg-blue-500/50 transition-all duration-1000 ease-linear" style={{ width: `${progressPercent}%` }} />
               </div>
            </div>
            
            <button 
              onClick={generateNewHash} 
              className="px-6 py-3 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/30 rounded-2xl transition-all w-full font-bold flex items-center justify-center gap-2"
            >
              <RefreshCw size={18} />
              Оновити хеш вручну
            </button>
          </div>
        </motion.div>
      )}
      </AnimatePresence>
      
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 pt-6 border-t border-gray-800/50 flex items-center justify-between px-2"
      >
        <div className="flex flex-col">
          <span className="text-sm font-bold text-gray-200">Автозапуск</span>
          <span className="text-xs text-gray-500">Запускати програму при старті системи</span>
        </div>
        
        <button 
          onClick={toggleLaunchAtStartup}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${launchAtStartup ? 'bg-blue-600' : 'bg-gray-700'}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${launchAtStartup ? 'translate-x-6' : 'translate-x-1'}`}
          />
        </button>
      </motion.div>
    </div>
  )
}
