import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
const { ipcRenderer } = require('electron')
import { QrCode, LayoutGrid, Terminal, ShieldCheck, Github } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import fluttershyImg from '../../resources/avatar.jpg'
import ConnectionPage from './pages/ConnectionPage'
import AppsPage from './pages/AppsPage'
import LogsPage from './pages/LogsPage'

function Sidebar() {
  const location = useLocation()
  const links = [
    { path: '/', icon: <QrCode size={20} />, label: 'Підключення' },
    { path: '/apps', icon: <LayoutGrid size={20} />, label: 'Програми' },
    { path: '/logs', icon: <Terminal size={20} />, label: 'Журнал' }
  ]

  return (
    <div className="w-72 bg-gray-900/60 backdrop-blur-xl p-6 flex flex-col justify-between border-r border-gray-800/50 shadow-2xl relative z-10">
      <div>
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-gradient-to-tr from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
             <QrCode size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-300">PC Controller</h1>
        </div>
        
        <div className="flex flex-col gap-3">
          {links.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`relative flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-300 font-medium ${
                  isActive 
                  ? 'text-white bg-blue-600/20 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border border-transparent'
                }`}
              >
                {isActive && (
                  <motion.div 
                    layoutId="active-sidebar" 
                    className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-600/20 to-transparent opacity-50" 
                  />
                )}
                <span className="relative z-10">{link.icon}</span>
                <span className="relative z-10">{link.label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="min-h-full">
             <ConnectionPage />
          </motion.div>
        } />
        <Route path="/apps" element={
           <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="min-h-full">
             <AppsPage />
          </motion.div>
        } />
        <Route path="/logs" element={
           <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="min-h-full">
             <LogsPage />
          </motion.div>
        } />
      </Routes>
    </AnimatePresence>
  )
}

function WarningModal() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (localStorage.getItem('warning_accepted') !== 'true') {
      setShow(true)
    }
  }, [])

  if (!show) return null

  const handleAccept = () => {
    localStorage.setItem('warning_accepted', 'true')
    setShow(false)
  }

  const handleQuit = () => {
    ipcRenderer.send('quit-app')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="max-w-lg w-full bg-gray-900 border border-gray-700 p-8 rounded-3xl shadow-2xl relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500" />
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-blue-500/20 rounded-2xl flex items-center justify-center shrink-0 border border-blue-500/30">
            <span className="text-2xl">✨</span>
          </div>
          <h2 className="text-2xl font-bold text-white">Увага!</h2>
        </div>
        
        <p className="text-gray-300 text-base leading-relaxed mb-6">
          Ця програма — інструмент для віддаленого керування вашим ПК, а <strong className="text-white">не RAT чи вірус</strong>.<br/>
          Якщо ви завантажили її <strong>не з</strong> офіційних сторінок:
        </p>

        <div className="flex gap-4 mb-8">
          <a href="https://github.com/merybist" target="_blank" rel="noreferrer" className="relative flex-1 bg-gray-800/40 hover:bg-gray-800 border border-gray-700 rounded-2xl p-5 overflow-hidden group transition-all text-left">
            <Github size={120} className="absolute -bottom-8 -right-8 text-white opacity-10 group-hover:opacity-20 transition-all duration-500 group-hover:scale-110" />
            <div className="relative z-10 flex flex-col">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-1">Офіційний GitHub</span>
              <span className="text-white font-bold text-sm">github.com/merybist</span>
            </div>
          </a>

          <a href="https://merybist.com" target="_blank" rel="noreferrer" className="relative flex-1 bg-indigo-900/20 hover:bg-indigo-900/40 border border-indigo-500/20 rounded-2xl p-5 overflow-hidden group transition-all text-left">
            <img src={fluttershyImg} alt="Fluttershy" className="absolute right-0 top-1/2 -translate-y-1/2 w-32 h-32 object-contain opacity-[0.35] mix-blend-screen group-hover:opacity-[0.5] transition-all duration-500 group-hover:scale-110" style={{ maskImage: 'radial-gradient(circle at center, black 45%, transparent 75%)', WebkitMaskImage: 'radial-gradient(circle at center, black 45%, transparent 75%)' }} />
            <div className="relative z-10 flex flex-col">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-widest mb-1">Сайт Автора</span>
              <span className="text-white font-bold text-sm">merybist.com</span>
            </div>
          </a>
        </div>

        <p className="text-center mb-8">
          <strong className="text-red-400 uppercase tracking-widest font-black text-xl">То вас наєбали!</strong>
        </p>

        <div className="flex gap-4">
          <button 
            onClick={handleAccept}
            className="flex-1 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold transition-all shadow-lg hover:shadow-blue-500/20"
          >
            Так, поняв
          </button>
          <button 
            onClick={handleQuit}
            className="flex-1 py-4 bg-red-500/10 hover:bg-red-500 hover:text-white text-red-400 border border-red-500/30 rounded-xl font-bold transition-all"
          >
            Вийти
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default function App() {
  return (
    <div className="relative flex h-screen w-full bg-[#0a0c10] text-gray-100 overflow-hidden font-sans selection:bg-blue-500/30">
      <WarningModal />
      {/* Background gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-600/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" />
      
      <Sidebar />
      <main className="flex-1 overflow-hidden p-8 relative z-10 flex flex-col">
        <AnimatedRoutes />
      </main>
    </div>
  )
}
