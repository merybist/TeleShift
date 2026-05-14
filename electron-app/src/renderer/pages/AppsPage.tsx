import React, { useEffect, useState } from 'react'
import { dbSelect, dbSelectOne, dbInsert, dbDelete, dbSubscribe } from '../db'
import { motion } from 'framer-motion'
import { FolderPlus, Trash2, Box } from 'lucide-react'
const { ipcRenderer } = require('electron')

export default function AppsPage() {
  const [apps, setApps] = useState<any[]>([])
  const deviceId = localStorage.getItem('device_id')
  const [internalId, setInternalId] = useState<string>('')

  useEffect(() => {
    fetchDeviceAndApps()
    const sub = dbSubscribe('apps', 'apps', () => fetchDeviceAndApps())
    return () => sub.unsubscribe()
  }, [])

  async function fetchDeviceAndApps() {
    if (!deviceId) return
    const dev = await dbSelectOne('devices', 'id', { device_id: deviceId })
    if (dev) {
      setInternalId(dev.id)
      const data = await dbSelect('apps', '*', { device_id: dev.id })
      setApps(data)
    }
  }

  async function addApp() {
    const path = await ipcRenderer.invoke('select-file')
    if (path) {
      // Handle both Windows (\) and Mac (/) paths, and remove common extensions
      const name = path.split(/[\\/]/).pop()?.replace(/\.(exe|app|lnk|bat)$/i, '') || 'New App'
      await dbInsert('apps', { device_id: internalId, name, path })
      fetchDeviceAndApps()
    }
  }

  async function removeApp(id: string) {
    await dbDelete('apps', { id })
    fetchDeviceAndApps()
  }

  return (
    <div className="max-w-3xl mx-auto h-full flex flex-col relative z-10">
      <div className="flex justify-between items-center mb-10 bg-gray-900/40 p-8 rounded-3xl border border-gray-800/50 backdrop-blur-xl shadow-2xl">
        <div>
          <h2 className="text-3xl font-black text-white bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">Apps</h2>
          <p className="text-gray-400 mt-2 text-lg">Add applications for quick launch via the bot</p>
        </div>
        <button onClick={addApp} className="px-6 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl transition-all font-bold shadow-lg shadow-blue-500/20 flex items-center gap-2">
          <FolderPlus size={20} />
          Add App
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto pr-2 pb-10">
        <div className="grid gap-4">
          {apps.map((app, i) => (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              key={app.id} 
              className="bg-gray-800/40 p-5 rounded-2xl border border-gray-700/50 flex justify-between items-center hover:bg-gray-800/60 transition-all backdrop-blur-md group hover:border-blue-500/30 hover:shadow-[0_0_20px_rgba(59,130,246,0.1)]"
            >
              <div className="overflow-hidden pr-4 flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-400 group-hover:bg-blue-500 group-hover:text-white transition-colors">
                  <Box size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-xl text-white mb-1 truncate">{app.name}</h3>
                  <p className="text-sm text-gray-500 font-mono truncate">{app.path}</p>
                </div>
              </div>
              <button 
                onClick={() => removeApp(app.id)} 
                className="shrink-0 p-3 bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white rounded-xl transition-all font-medium opacity-0 group-hover:opacity-100 focus:opacity-100"
                title="Delete"
              >
                <Trash2 size={20} />
              </button>
            </motion.div>
          ))}
          {apps.length === 0 && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="text-center py-20 bg-gray-800/20 rounded-3xl border border-gray-700/50 border-dashed backdrop-blur-sm"
            >
              <Box size={48} className="mx-auto text-gray-600 mb-4" />
              <p className="text-gray-400 text-xl font-medium">App list is empty.</p>
              <p className="text-gray-500 mt-2">Click "Add App" to get started.</p>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
