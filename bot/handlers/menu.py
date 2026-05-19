from aiogram import Router, F
from aiogram.types import CallbackQuery
from locales import t
from keyboards.inline import main_menu_kb

router = Router()


@router.callback_query(F.data == "main_menu")
async def go_main_menu(call: CallbackQuery, lang: str = "en"):
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    else:
        await call.message.edit_text(t("main_menu", lang), reply_markup=main_menu_kb(lang))
