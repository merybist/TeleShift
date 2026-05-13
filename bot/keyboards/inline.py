from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def not_connected_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Підключити ПК", callback_data="connect_info")]
    ])

def connect_info_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ввести хеш вручну", callback_data="enter_hash")]
    ])

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Вимкнути", callback_data="power_off"),
         InlineKeyboardButton(text="🔄 Перезавантажити", callback_data="power_reboot")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="menu_status"),
         InlineKeyboardButton(text="🔒 Заблокувати", callback_data="sys_lock")],
        [InlineKeyboardButton(text="📸 Скріншот", callback_data="menu_screenshot"),
         InlineKeyboardButton(text="🚀 Запуск", callback_data="menu_launch")],
        [InlineKeyboardButton(text="⚙️ Налаштування", callback_data="menu_settings")]
    ])

def confirm_kb(action_prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так", callback_data=f"{action_prefix}_yes"),
         InlineKeyboardButton(text="❌ Ні — назад", callback_data="main_menu")]
    ])

def back_btn():
    return InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[back_btn()]])

def status_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Отримати статус", callback_data="stat_all")],
        [InlineKeyboardButton(text="🔇 Керування звуком", callback_data="stat_sound")],
        [back_btn()]
    ])

def sound_menu_kb(vol_percent, is_muted):
    mute_text = "🔊 Увімк" if is_muted else "🔇 Мʼют"
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
        row.append(InlineKeyboardButton(text=f"🖥 Монітор {i}", callback_data=f"screen_{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton(text="🖥 Всі", callback_data="screen_all")])
    kb.append([back_btn()])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def apps_kb(apps):
    kb = []
    row = []
    for app in apps:
        row.append(InlineKeyboardButton(text=app['name'], callback_data=f"launch_{app['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    kb.append([back_btn()])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def settings_kb(settings):
    notif = "Увімк" if settings.get('notify_on_command') else "Вимк"
    online_notif = "Увімк" if settings.get('notify_online', True) else "Вимк"
    qual = settings.get('screenshot_quality', 'high')
    lang = settings.get('language', 'ua').upper()

    kb = [
        [InlineKeyboardButton(text=f"🔔 Сповіщення: {notif}", callback_data="set_notif")],
        [InlineKeyboardButton(text=f"🟢 Онлайн-нотифікація: {online_notif}", callback_data="set_online_notif")],
        [InlineKeyboardButton(text=f"📸 Якість: {qual}", callback_data="set_qual"),
         InlineKeyboardButton(text=f"🌐 Мова: {lang}", callback_data="set_lang")],
        [InlineKeyboardButton(text="🔌 Відключити ПК", callback_data="disconnect_pc")],
        [InlineKeyboardButton(text="ℹ️ Інфо", callback_data="sys_info")],
        [back_btn()]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
