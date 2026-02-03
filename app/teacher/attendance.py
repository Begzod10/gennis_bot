import pprint

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.student.utils import safe_get, safe_post
from aiogram.exceptions import TelegramBadRequest
import os

teacher_callbacks = Router()
selected_date = {}


async def format_group_list(groups):
    text = "👥 <b>Sizning guruhlaringiz:</b>\n\n"
    buttons = []
    for i, g in enumerate(groups, start=1):
        text += (
            f"{i}️⃣ <b>{g.get('name')}</b>\n"
            f"📚 {g.get('subject', {}).get('name', '—')}\n"
            f"👨‍🎓 {g.get('students_num', 0)} o‘quvchi\n"
            f"{'─' * 22}\n"
        )
        buttons.append(
            InlineKeyboardButton(
                text=f"{i}️⃣ Guruh",
                callback_data=f"group_open:{g['id']}"
            )
        )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    )
    return text, keyboard


@teacher_callbacks.message(lambda m: m.text and "guruhlar" in m.text.lower())
async def get_teacher_groups(message: Message):
    token = os.getenv("GENNIS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    res = await safe_get(
        "https://classroom.gennis.uz/api/group/get_groups",
        headers=headers
    )
    groups = res.json()
    text, kb = await format_group_list(groups)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@teacher_callbacks.callback_query(F.data.startswith("group_open:"))
async def open_group(callback: CallbackQuery):
    group_id = callback.data.split(":")[1]
    token = os.getenv("GENNIS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    res = await safe_get(
        f"https://classroom.gennis.uz/api/group/attendance_classroom/{group_id}",
        headers=headers
    )
    data = res.json()
    dates = data.get("date", [])
    buttons = []
    for d in dates:
        for day in d.get("days", []):
            date_text = f"{day} {d.get('name')}"
            buttons.append(InlineKeyboardButton(
                text=date_text,
                callback_data=f"set_date:{group_id}:{day}-{d.get('value')}"
            ))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    )
    try:
        await callback.message.edit_text(
            "📅 Iltimos, baho qo‘yiladigan sanani tanlang:",
            reply_markup=keyboard
        )
    except TelegramBadRequest:
        await callback.answer("📅 Sana tanlang")


@teacher_callbacks.callback_query(F.data.startswith("set_date:"))
async def set_date(callback: CallbackQuery):
    _, group_id, date_str = callback.data.split(":")
    day, month = date_str.split("-")
    selected_date[group_id] = f"{day}-{month}"
    token = os.getenv("GENNIS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    res = await safe_get(
        f"https://classroom.gennis.uz/api/group/group_profile2/{group_id}",
        headers=headers
    )
    students = res.json().get("data", {}).get("students", [])
    await callback.message.delete()
    for s in students:
        student_id = s.get("id")
        full_name = f"{s.get('name', '')} {s.get('surname', '')}".strip()
        phone = s.get("phone", "—")
        balance = s.get("balance", 0)
        text = (
            f"👤 <b>{full_name}</b>\n"
            f"📱 +998{phone}\n"
            f"💰 {balance:,} so'm"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Keldi",
                    callback_data=f"att_yes:{group_id}:{student_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Kelmadi",
                    callback_data=f"att_no:{group_id}:{student_id}"
                )
            ]]
        )
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@teacher_callbacks.callback_query(F.data.startswith("att_no:"))
async def attendance_no(callback: CallbackQuery):
    _, group_id, student_id = callback.data.split(":")
    token = os.getenv("GENNIS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "group_id": int(group_id),
        "student": {
            "id": int(student_id),
            "typeChecked": "no",
            "scores": [],
            "date": selected_date.get(group_id)
        }
    }
    await safe_post(
        "https://classroom.gennis.uz/api/group_classroom_attendance/make_attendance_classroom",
        headers=headers,
        json=payload
    )
    await callback.message.delete()


@teacher_callbacks.callback_query(F.data.startswith("att_yes:"))
async def homework_select(callback: CallbackQuery):
    _, group_id, student_id = callback.data.split(":")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text="⭐" * i, callback_data=f"hw:{group_id}:{student_id}:{i}")]
                            for i in range(1, 6)
                        ] + [
                            [InlineKeyboardButton(text="➡️ O‘tkazish", callback_data=f"hw:{group_id}:{student_id}:0")]
                        ]
    )
    await callback.message.edit_text(
        "📘 <b>Uy vazifasi</b>\nNecha yulduz qo‘yiladi?",
        parse_mode="HTML",
        reply_markup=kb
    )


@teacher_callbacks.callback_query(F.data.startswith("hw:"))
async def activity_select(callback: CallbackQuery):
    _, group_id, student_id, hw = callback.data.split(":")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text="⭐" * i, callback_data=f"act:{group_id}:{student_id}:{hw}:{i}")]
                            for i in range(1, 6)
                        ] + [
                            [InlineKeyboardButton(text="➡️ O‘tkazish",
                                                  callback_data=f"act:{group_id}:{student_id}:{hw}:0")]
                        ]
    )
    await callback.message.edit_text(
        "⚡ <b>Darsdagi faollik</b>\nNecha yulduz qo‘yiladi?",
        parse_mode="HTML",
        reply_markup=kb
    )


@teacher_callbacks.callback_query(F.data.startswith("act:"))
async def attendance_finish(callback: CallbackQuery):
    _, group_id, student_id, hw, act = callback.data.split(":")
    hw = int(hw)
    act = int(act)
    date = selected_date.get(group_id)
    if not date:
        await callback.answer("❗ Avval sanani tanlang", show_alert=True)
        return
    day, month = date.split("-")
    dictionary = 0  # Dictionary qoshmadim = 0
    payload = {
        "day": int(day),
        "month": month,
        "group_id": int(group_id),
        "id": int(student_id),
        "type": "yes" if (hw + act + dictionary) > 0 else "no",
        "score": [
            {"name": "homework", "activeBall": hw},
            {"name": "activity", "activeBall": act},
            {"name": "dictionary", "activeBall": dictionary}
        ]
    }
    token = os.getenv("GENNIS_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = await safe_post(
        "https://classroom.gennis.uz/api/group_classroom_attendance/make_attendance_classroom",
        headers=headers,
        json=payload
    )
    try:
        if res.status_code == 200:
            await callback.answer("✅ Davomat saqlandi", show_alert=True)
            await callback.message.delete()
        else:
            try:
                error_text = res.json().get("errors", [{"message": "Unknown error"}])[0]["message"]
            except Exception:
                error_text = res.text
            if len(error_text) > 200:
                error_text = error_text[:200] + "..."
            try:
                await callback.answer(f"❌ Xatolik: {error_text}", show_alert=True)
            except TelegramBadRequest:
                await callback.message.reply(f"❌ Xatolik: {error_text}")
    except TelegramBadRequest:
        await callback.message.reply("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.")
    pprint.pprint(payload)
