<div align="center">
  <h1>🚀 TeleShift</h1>
  <p><strong>Premium Remote PC Controller Desktop Agent & Telegram Bot</strong></p>
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey?style=for-the-badge" alt="Platforms" />
  <br><br>
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=electron,react,ts,tailwind,py,supabase,postgres" alt="Tech Stack" />
  </a>
</div>

---

## 🌟 Overview

**TeleShift** is a high-end, secure, and distributed remote PC control system. It empowers you to manage your desktop computers remotely using a centralized Telegram Bot acting as the command center, and a lightweight, background Electron-based agent installed on your machines.

With real-time commands bridged through **Supabase**, TeleShift offers instant execution with high security and minimal latency.

## ✨ Features

- 📱 **Telegram Bot Interface:** Control your PC from anywhere right from your Telegram app.
- ⚡ **Real-Time Execution:** Powered by Supabase WebSockets for instant command delivery.
- 🖥️ **Agent:** Built with Electron & React for Windows.
- 🔒 **Secure Connection:** Devices are linked securely via per-user unique database hashes.
- 👻 **Stealth Mode:** The desktop agent starts automatically on boot and runs hidden in the system tray.

### 🎮 Supported Commands
- 🛑 **Shutdown / Reboot** - Manage system power state.
- 🔒 **Lock Screen** - Secure your workstation instantly.
- 📸 **Take Screenshots** - View your PC's current screen remotely.
- 🔊 **Volume Control** - Mute, increase, or decrease system volume.
- 📊 **System Status** - Monitor battery level and disk space.
- 🚀 **Launch Apps** - Start specific executables or files remotely.

---

## 🛠️ Tech Stack

### Desktop Agent (Host)
- ![Electron](https://img.shields.io/badge/Electron-191970?style=flat-square&logo=Electron&logoColor=white)
- ![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
- ![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat-square&logo=typescript&logoColor=white)
- ![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)

### Control Center (Bot)
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
- ![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blue?style=flat-square)

### Backend Bridge
- ![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white)

---

## 🚀 Getting Started

### 1. Database Setup (Supabase / PostgreSQL)
1. Create a new Supabase project or use your own PostgreSQL database with Realtime enabled.
2. Setup the `device_commands` table for realtime listening.
3. Keep your Database URL (or `SUPABASE_URL`) and Keys handy.

### 2. Telegram Bot Setup
1. Clone the repository and navigate to the `bot` directory.
2. Copy `.env.example` to `.env` and fill in your Supabase and Telegram Bot tokens.
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

### 3. Desktop Agent Setup
1. Navigate to the `electron-app` directory.
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. To test in development:
   ```bash
   npm run dev
   ```
4. To build the production executable (NSIS Installer for Windows):
   ```bash
   npm run build:exe
   ```

---

## 🛡️ Security & Privacy
TeleShift does not expose your local PC to the public internet via port forwarding. It securely listens for authorized commands pushed to the Supabase real-time channel, preventing external attacks.

---

<div align="center">
  <i>Built with ❤️ for seamless remote management.</i>
</div>
