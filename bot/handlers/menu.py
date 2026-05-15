from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import main_menu_kb
from utils.i18n import t

router = Router()

@router.callback_query(F.data == "main_menu")
async def go_main_menu(call: CallbackQuery, lang: str):
    text = f"🏠 {t('welcome', lang)}"
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text, reply_markup=main_menu_kb(lang), parse_mode="HTML")
    else:
        await call.message.edit_text(text, reply_markup=main_menu_kb(lang), parse_mode="HTML")
