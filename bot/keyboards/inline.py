from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.i18n import t

def not_connected_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔗 {t('connect_info', lang)}", callback_data="connect_info")]
    ])

def connect_info_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✏️ {t('enter_hash', lang)}", callback_data="enter_hash")]
    ])

def main_menu_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('power_title', lang), callback_data="menu_power")],
        [InlineKeyboardButton(text=t('status_fetching', lang).split(' ')[0] + " Status", callback_data="menu_status"),
         InlineKeyboardButton(text="🔒 Lock", callback_data="sys_lock")],
        [InlineKeyboardButton(text="📸 Screenshot", callback_data="menu_screenshot"),
         InlineKeyboardButton(text="🚀 Launch", callback_data="menu_launch")],
        [InlineKeyboardButton(text=t('settings', lang), callback_data="menu_settings")]
    ])

def power_control_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('shutdown_now', lang), callback_data="power_off"),
         InlineKeyboardButton(text=t('reboot_now', lang), callback_data="power_reboot")],
        [InlineKeyboardButton(text=t('schedule_shutdown', lang), callback_data="sched_shutdown"),
         InlineKeyboardButton(text=t('schedule_reboot', lang), callback_data="sched_reboot")],
        [InlineKeyboardButton(text=t('my_schedules', lang), callback_data="sched_list")],
        [back_btn(lang)]
    ])

def confirm_kb(action_prefix, lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {t('yes', lang)}", callback_data=f"{action_prefix}_yes"),
         InlineKeyboardButton(text=f"❌ {t('no', lang)}", callback_data="main_menu")]
    ])

def schedule_type_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('one_time', lang), callback_data="stype_once"),
         InlineKeyboardButton(text=t('daily', lang), callback_data="stype_daily")],
        [back_btn(lang)]
    ])

def schedules_list_kb(schedules, lang='ua'):
    kb = []
    for s in schedules:
        cmd_type = "OFF" if s['command'] == 'shutdown' else "REB"
        time_str = s['scheduled_at']
        if hasattr(time_str, 'strftime'): time_str = time_str.strftime('%H:%M')
        else: time_str = str(time_str)[:5]
        type_str = "D" if s['is_daily'] else "1"
        kb.append([InlineKeyboardButton(text=f"❌ {cmd_type} {time_str} ({type_str})", callback_data=f"sched_del_{s['id']}")])
    kb.append([back_btn(lang)])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_btn(lang='ua'):
    return InlineKeyboardButton(text=t('back', lang), callback_data="main_menu")

def back_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[[back_btn(lang)]])

def status_menu_kb(lang='ua'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Get Status", callback_data="stat_all")],
        [InlineKeyboardButton(text="🔇 Sound Control", callback_data="stat_sound")],
        [back_btn(lang)]
    ])

def sound_menu_kb(vol_percent, is_muted, lang='ua'):
    mute_text = "🔊 Unmute" if is_muted else "🔇 Mute"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mute_text, callback_data="snd_mute")],
        [InlineKeyboardButton(text="➕ +10%", callback_data="snd_up"),
         InlineKeyboardButton(text="➖ -10%", callback_data="snd_down")],
        [back_btn(lang)]
    ])

def settings_kb(settings, lang='ua'):
    notif = "On" if settings.get('notify_on_command') else "Off"
    online_notif = "On" if settings.get('notify_online', True) else "Off"
    qual = settings.get('screenshot_quality', 'high')
    current_lang = settings.get('language', 'en').upper()
    kb = [
        [InlineKeyboardButton(text=f"🔔 Notifications: {notif}", callback_data="set_notif")],
        [InlineKeyboardButton(text=f"🟢 Online Alert: {online_notif}", callback_data="set_online_notif")],
        [InlineKeyboardButton(text=f"📸 Quality: {qual}", callback_data="set_qual"),
         InlineKeyboardButton(text=f"🌐 Language: {current_lang}", callback_data="set_lang")],
        [InlineKeyboardButton(text="🔌 Disconnect PC", callback_data="disconnect_pc")],
        [back_btn(lang)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def monitors_kb(count, lang='ua'):
    if count <= 1: return None
    kb = []
    row = []
    for i in range(1, count + 1):
        row.append(InlineKeyboardButton(text=f"🖥 {t('monitor_select', lang, current=i)}", callback_data=f"screen_{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton(text="🖥 All", callback_data="screen_all")])
    kb.append([back_btn(lang)])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def apps_kb(apps, status_map=None, lang='ua'):
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
    kb.append([back_btn(lang)])
    return InlineKeyboardMarkup(inline_keyboard=kb)
