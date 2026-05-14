from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import main_menu_kb

router = Router()

@router.callback_query(F.data == "main_menu")
async def go_main_menu(call: CallbackQuery):
    # Якщо це фотоповідомлення, edit_text не спрацює, тому видаляємо і шлемо нове
    if call.message.photo:
        await call.message.delete()
        await call.message.answer("🏠 Головне меню", reply_markup=main_menu_kb())
    else:
        await call.message.edit_text("🏠 Головне меню", reply_markup=main_menu_kb())
