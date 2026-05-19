from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales import t


def not_connected_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_connect", lang), callback_data="connect_info")]
    ])


def connect_info_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_enter_hash", lang), callback_data="enter_hash")]
    ])


def main_menu_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_power", lang), callback_data="menu_power"),
         InlineKeyboardButton(text=t("btn_status", lang), callback_data="menu_status")],
        [InlineKeyboardButton(text=t("btn_screenshot", lang), callback_data="menu_screenshot"),
         InlineKeyboardButton(text=t("btn_launch", lang), callback_data="menu_launch")],
        [InlineKeyboardButton(text=t("btn_controls", lang), callback_data="menu_controls"),
         InlineKeyboardButton(text=t("btn_settings", lang), callback_data="menu_settings")]
    ])


def confirm_kb(action_prefix, lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_yes", lang), callback_data=f"{action_prefix}_yes"),
         InlineKeyboardButton(text=t("btn_no_back", lang), callback_data="main_menu")]
    ])


def back_btn(lang="en"):
    return InlineKeyboardButton(text=t("btn_back", lang), callback_data="main_menu")


def back_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[[back_btn(lang)]])


# ── Power ──────────────────────────────────────────────────────

def power_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_shutdown", lang), callback_data="power_off"),
         InlineKeyboardButton(text=t("btn_restart", lang), callback_data="power_reboot")],
        [back_btn(lang)]
    ])


# ── Controls ───────────────────────────────────────────────────

def controls_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_sound", lang), callback_data="ctrl_sound")],
        [InlineKeyboardButton(text=t("btn_lock", lang), callback_data="ctrl_lock")],
        [back_btn(lang)]
    ])


def sound_menu_kb(vol_percent, is_muted, lang="en"):
    mute_text = t("btn_unmute", lang) if is_muted else t("btn_mute", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mute_text, callback_data="snd_mute")],
        [InlineKeyboardButton(text=t("btn_vol_up", lang), callback_data="snd_up"),
         InlineKeyboardButton(text=t("btn_vol_down", lang), callback_data="snd_down")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu_controls")]
    ])


# ── Status ─────────────────────────────────────────────────────

def status_menu_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 " + t("btn_status", lang), callback_data="stat_all")],
        [back_btn(lang)]
    ])


# ── Screenshot ─────────────────────────────────────────────────

def monitors_kb(count, lang="en"):
    if count <= 1:
        return None
    kb = []
    row = []
    for i in range(1, count + 1):
        row.append(InlineKeyboardButton(text=f"🖥 Monitor {i}", callback_data=f"screen_{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="🖥 All", callback_data="screen_all")])
    kb.append([back_btn(lang)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ── Launcher ───────────────────────────────────────────────────

def apps_kb(apps, status_map=None, lang="en"):
    kb = []
    row = []
    for app in apps:
        is_running = status_map.get(str(app['id'])) if status_map else False
        name = f"✅ {app['name']}" if is_running else app['name']
        row.append(InlineKeyboardButton(text=name, callback_data=f"launch_{app['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([back_btn(lang)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def launch_result_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_refresh", lang), callback_data="menu_launch")],
        [back_btn(lang)]
    ])


# ── Settings ───────────────────────────────────────────────────

def settings_kb(lang="en"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_notifications", lang), callback_data="settings_notif")],
        [InlineKeyboardButton(text=t("btn_preferences", lang), callback_data="settings_prefs")],
        [InlineKeyboardButton(text=t("btn_device_info", lang), callback_data="sys_info")],
        [InlineKeyboardButton(text=t("btn_disconnect", lang), callback_data="disconnect_pc")],
        [back_btn(lang)]
    ])


def settings_notif_kb(settings, lang="en"):
    notif_val = t("val_on", lang) if settings.get('notify_on_command') else t("val_off", lang)
    online_val = t("val_on", lang) if settings.get('notify_online', True) else t("val_off", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cmd_notif", lang, val=notif_val), callback_data="set_notif")],
        [InlineKeyboardButton(text=t("btn_online_notif", lang, val=online_val), callback_data="set_online_notif")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu_settings")]
    ])


def settings_prefs_kb(settings, lang="en"):
    qual = settings.get('screenshot_quality', 'high')
    current_lang = settings.get('language', 'en').upper()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_quality", lang, val=qual), callback_data="set_qual")],
        [InlineKeyboardButton(text=t("btn_language", lang, val=current_lang), callback_data="set_lang")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu_settings")]
    ])
