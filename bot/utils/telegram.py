import asyncio
from aiogram.types import CallbackQuery
from locales import t
from keyboards.inline import main_menu_kb

async def handle_offline_device(call: CallbackQuery, lang: str = "en"):
    # Answer callback query to stop loading spinner and show native alert
    try:
        await call.answer(t("device_offline", lang), show_alert=True)
    except Exception:
        pass

    offline_msg = t("device_offline", lang)
    temp_msg = None

    if call.message.photo:
        try:
            await call.message.delete()
        except Exception:
            pass
        temp_msg = await call.message.answer(offline_msg)
        await asyncio.sleep(3)
        try:
            await temp_msg.delete()
        except Exception:
            pass
        await call.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    else:
        # Edit current message text to offline warning, removing keyboard
        try:
            await call.message.edit_text(offline_msg)
        except Exception:
            # Fallback if edit fails
            temp_msg = await call.message.answer(offline_msg)

        await asyncio.sleep(3)

        if temp_msg:
            try:
                await temp_msg.delete()
            except Exception:
                pass
            await call.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
        else:
            try:
                await call.message.edit_text(t("main_menu", lang), reply_markup=main_menu_kb(lang))
            except Exception:
                await call.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
