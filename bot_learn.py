import asyncio
import sqlite3 as sq
import re
import os

from db_tg import *

from openpyxl import Workbook

from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


TOKEN = "your_token_from_@BotFather"
ADMIN_ID = 'your_telegram_id' #without parentheses
AVAILABLE_TIMES = [
    "09:00",
    "10:00",
    "11:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00"
]


storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=TOKEN)

connection = sq.connect('clients.db')
cursor = connection.cursor()

class ClientForm(StatesGroup):
    wait_name = State()
    wait_phone = State()
    wait_email = State()
    wait_time_m = State()
    wait_master = State()

def get_booked_times(master_id):
    cursor.execute("SELECT time_m FROM clients WHERE master_id = ?", (master_id,))
    records = cursor.fetchall()
    
    booked = [row[0] for row in records]
    return booked

def main_keyboard(message: Message) -> ReplyKeyboardMarkup:
    kb = [
            [KeyboardButton(text="Book an appointment")]
        ]
        
    if message.from_user.id == ADMIN_ID:
        kb.append([KeyboardButton(text="Appointments")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return keyboard


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Hello!", reply_markup=main_keyboard(message))

@dp.message(F.text == "Book an appointment")
async def record_client(message: Message, state: FSMContext):
    init_db()

    await message.answer("Enter the client's name: ")
    await state.set_state(ClientForm.wait_name)

@dp.message(ClientForm.wait_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter the client's phone number: ")
    await state.set_state(ClientForm.wait_phone)

@dp.message(ClientForm.wait_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    phone = message.text.strip()

    pattern_phone = r"^\+?380\d{9}$"
    if not re.match(pattern_phone, phone):
            await message.answer("Invalid format!")
            return

    await state.update_data(phone=phone)
    await message.answer("Enter the client's email address: ")
    await state.set_state(ClientForm.wait_email)

@dp.message(ClientForm.wait_email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    email = message.text.strip()

    pattern = r"^[\w\.-]+@gmail\.com$"

    if not re.match(pattern, email):
        await message.answer("Invalid format!")
        return

    await state.update_data(email=email)

    cursor.execute('''SELECT id, name FROM masters''')
    show_masters = cursor.fetchall()

    masters_text = "Select a master's ID to book an appointment:\n\n"
    for m_id, name in show_masters:
        masters_text += f"{m_id} — {name}\n"

    await message.answer(masters_text)
    await state.set_state(ClientForm.wait_master)

@dp.message(ClientForm.wait_master)
async def process_master(message: Message, state: FSMContext):
    await state.update_data(master_id=message.text)

    try:
        master_id = int(message.text)
    except ValueError:
        await message.answer("Invalid master ID. Please enter a number.")
        return

    cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
    master_exists = cursor.fetchone()

    if not master_exists:
        await message.answer("No master with that ID exists. Please check the list and enter a valid ID:")
        return


    await state.update_data(master_id=master_id)
    booked_times = get_booked_times(master_id)

    free_times = [time for time in AVAILABLE_TIMES if time not in booked_times]

    if not free_times:
        await message.answer("This master has no available time slots. Choose another master (enter the ID):")
        return

    keyboard_buttons = [[InlineKeyboardButton(text=time, callback_data=f"choice_{time}")]
                        for time in free_times]
    inline_kb_times = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer("Select an available time slot:", reply_markup=inline_kb_times)
    await state.set_state(ClientForm.wait_time_m)

# Admin interface

@dp.message(F.text == "Appointments", F.from_user.id == ADMIN_ID)
async def show_records(message: Message, state: State):

    kb_excel = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Export to Excel")],
            [KeyboardButton(text="Back to main menu")]
        ],
        resize_keyboard=True
    )

    cursor.execute('''SELECT id, name, phone, email, master_id, time_m FROM clients''')
    records = cursor.fetchall()

    if not records:
        await message.answer("No appointments found.", reply_markup=kb_excel)
        return

    await message.answer("Admin panel", reply_markup=kb_excel)
    
    for id, name, phone, email, master_id, time_m in records:
        keyboard_inl = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                    text='Delete',
                    callback_data=f"delete_{id}")
                ]
            ]
        )
        response = f"{id}. Name: {name}\n Phone: {phone}\n Email: {email}\n Master: {master_id}\n Time: {time_m} "
        await message.answer(response, reply_markup=keyboard_inl)


@dp.message(F.text == "Export to Excel", F.from_user.id == ADMIN_ID)
async def records_exel(message: Message):

    cursor.execute('''
        SELECT clients.id, clients.name, clients.phone, clients.email, masters.name, clients.time_m 
        FROM clients 
        LEFT JOIN masters ON clients.master_id = masters.id
    ''')
    records = cursor.fetchall()

    if not records:
        await message.answer("There are no appointments in the database to export.")
        return 

    wb = Workbook()
    ws = wb.active
    ws.title = 'Record Clients'  

    headers = ["Appointment ID", "Client name", "Phone", "Email", "Master", "Appointment time"]
    ws.append(headers)

    for record in records:
        ws.append(list(record))

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    file_path = "clients_export.xlsx"
    wb.save(file_path)

    document = FSInputFile(file_path)
    await message.answer_document(document, caption="📊 Full list of client appointments")

    if os.path.exists(file_path):
        os.remove(file_path)

@dp.message(F.text == "Back to main menu", F.from_user.id == ADMIN_ID)
async def exit_admin(message: Message):
    await message.answer("Back to the main menu", reply_markup=main_keyboard(message))

@dp.callback_query(F.data.startswith("delete_"))
async def delete_record(callback: CallbackQuery):

    record_id = int(callback.data.split("_")[1])
    cursor.execute(
        "DELETE FROM clients WHERE id = ?",
        (record_id,)
    )
    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM clients")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='clients'")
        connection.commit()

    await callback.message.answer("Appointment deleted successfully.")
    await callback.answer()

    # The record has now been deleted from the database.

@dp.callback_query(F.data.startswith("choice_"))
async def choice_free_time(callback: CallbackQuery, state: FSMContext):
    chosen_time = callback.data.split("_")[1]

    await state.update_data(time_m=chosen_time)

    data = await state.get_data()
    try:
        master_id = int(data['master_id'])
    except ValueError:
        master_id = data['master_id']

    add_client(
            tg_id=callback.from_user.id,
            name=data['name'],
            phone=data['phone'],
            email=data['email'],
            time_m=data['time_m'],
            master_id=master_id
        )
    
    await callback.message.answer(f"Appointment successfully booked for {chosen_time}!")
    await callback.answer()
    await state.clear()

    
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())