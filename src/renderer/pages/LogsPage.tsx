import React, { useEffect, useState } from 'react'
import { dbSelect, dbSelectOne, dbDelete, dbSubscribe } from '../db'

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const deviceId = localStorage.getItem('device_id')
  const [internalId, setInternalId] = useState<string>('')

  useEffect(() => {
    fetchLogs()
    const sub = dbSubscribe('logs', 'logs', (payload) => {
      setLogs(prev => [payload, ...prev].slice(0, 100))
    }, { eventType: 'INSERT' })
    return () => sub.unsubscribe()
  }, [])

  async function fetchLogs() {
    if (!deviceId) return
    const dev = await dbSelectOne('devices', 'id', { device_id: deviceId })
    if (dev) {
      setInternalId(dev.id)
      const data = await dbSelect('logs', '*', { device_id: dev.id }, { orderBy: 'created_at', ascending: false, limit: 100 })
      setLogs(data)
    }
  }

  async function clearLogs() {
    if (!internalId) return
    await dbDelete('logs', { device_id: internalId })
    setLogs([])
  }

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6 bg-gray-800/30 p-6 rounded-2xl border border-gray-700 backdrop-blur-sm">
        <div>
          <h2 className="text-2xl font-bold text-white">Журнал дій</h2>
          <p className="text-gray-400 mt-1">Останні команди відправлені з Telegram бота</p>
        </div>
        <button onClick={clearLogs} className="px-6 py-3 bg-red-600/80 hover:bg-red-600 text-white rounded-xl transition-all font-medium shadow-lg hover:shadow-red-500/20">
          Очистити
        </button>
      </div>
      <div className="flex-1 bg-gray-900 border border-gray-700 rounded-2xl p-6 overflow-y-auto font-mono text-sm shadow-inner">
        {logs.length === 0 ? (
          <p className="text-gray-500 text-center mt-10">Журнал порожній</p>
        ) : (
          logs.map(log => (
            <div key={log.id} className="mb-3 border-b border-gray-800 pb-2 last:border-0">
              <span className="text-gray-500 mr-3">[{new Date(log.created_at).toLocaleTimeString()}]</span>
              <span className="text-blue-400 font-bold">@{log.username}</span>
              <span className="text-gray-300 ml-2">→ {log.action}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
