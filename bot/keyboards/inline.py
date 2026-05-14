from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def not_connected_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Connect PC", callback_data="connect_info")]
    ])

def connect_info_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Enter hash manually", callback_data="enter_hash")]
    ])

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Shutdown", callback_data="power_off"),
         InlineKeyboardButton(text="🔄 Restart", callback_data="power_reboot")],
        [InlineKeyboardButton(text="📊 Status", callback_data="menu_status"),
         InlineKeyboardButton(text="🔒 Lock", callback_data="sys_lock")],
        [InlineKeyboardButton(text="📸 Screenshot", callback_data="menu_screenshot"),
         InlineKeyboardButton(text="🚀 Launch", callback_data="menu_launch")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")]
    ])

def confirm_kb(action_prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes", callback_data=f"{action_prefix}_yes"),
         InlineKeyboardButton(text="❌ No — back", callback_data="main_menu")]
    ])

def back_btn():
    return InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[back_btn()]])

def status_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Get Status", callback_data="stat_all")],
        [InlineKeyboardButton(text="🔇 Sound Control", callback_data="stat_sound")],
        [back_btn()]
    ])

def sound_menu_kb(vol_percent, is_muted):
    mute_text = "🔊 Unmute" if is_muted else "🔇 Mute"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mute_text, callback_data="snd_mute")],
        [InlineKeyboardButton(text="➕ +10%", callback_data="snd_up"),
         InlineKeyboardButton(text="➖ -10%", callback_data="snd_down")],
        [back_btn()]
    ])

def monitors_kb(count):
    if count <= 1: return None
    kb = []
    row = []
    for i in range(1, count + 1):
        row.append(InlineKeyboardButton(text=f"🖥 Monitor {i}", callback_data=f"screen_{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton(text="🖥 All", callback_data="screen_all")])
    kb.append([back_btn()])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def apps_kb(apps, status_map=None):
    kb = []
    row = []
    for app in apps:
        is_running = status_map.get(str(app['id'])) if status_map else False
        name = f"✅ {app['name']}" if is_running else app['name']
        
        row.append(InlineKeyboardButton(text=name, callback_data=f"launch_{app['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([back_btn()])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def settings_kb(settings):
    notif = "On" if settings.get('notify_on_command') else "Off"
    online_notif = "On" if settings.get('notify_online', True) else "Off"
    qual = settings.get('screenshot_quality', 'high')
    lang = settings.get('language', 'en').upper()

    kb = [
        [InlineKeyboardButton(text=f"🔔 Notifications: {notif}", callback_data="set_notif")],
        [InlineKeyboardButton(text=f"🟢 Online Alert: {online_notif}", callback_data="set_online_notif")],
        [InlineKeyboardButton(text=f"📸 Quality: {qual}", callback_data="set_qual"),
         InlineKeyboardButton(text=f"🌐 Language: {lang}", callback_data="set_lang")],
        [InlineKeyboardButton(text="🔌 Disconnect PC", callback_data="disconnect_pc")],
        [InlineKeyboardButton(text="ℹ️ Info", callback_data="sys_info")],
        [back_btn()]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
