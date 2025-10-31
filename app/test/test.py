from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

test = Router()


class TestStates(StatesGroup):
    waiting_for_answer = State()


html_savoli = [
    {
        "q": "HTML5’da <section> va <div> teglari orasidagi farq nimada?",
        "options": [
            "Ikkalasi ham bir xil ishlaydi",
            "<section> semantik teg, <div> esa semantik emas",
            "<div> faqat matn uchun ishlatiladi"
        ],
        "answer": "<section> semantik teg, <div> esa semantik emas"
    },
    {
        "q": "<canvas> tegi nima uchun ishlatiladi?",
        "options": [
            "Video joylash uchun",
            "Matn formatlash uchun",
            "Rasm va grafik chizish uchun"
        ],
        "answer": "Rasm va grafik chizish uchun"
    },
    {
        "q": "HTML’da accessibility (foydalanuvchilar uchun qulaylik) ni yaxshilash uchun qaysi atribut ishlatiladi?",
        "options": ["aria-label", "alt-text", "screen-reader"],
        "answer": "aria-label"
    },
    {
        "q": "<meta charset='UTF-8'> tegi nima qiladi?",
        "options": [
            "Brauzerga sahifa kengligini belgilaydi",
            "Tegishli script faylini ulaydi",
            "Veb sahifa kodlash turini belgilaydi"
        ],
        "answer": "Veb sahifa kodlash turini belgilaydi"
    },
    {
        "q": "<picture> tegi nimaga xizmat qiladi?",
        "options": [
            "Turli ekran o‘lchamlariga mos rasm tanlash uchun",
            "Rasmlarni guruhlash uchun",
            "Rasm ustiga matn yozish uchun"
        ],
        "answer": "Turli ekran o‘lchamlariga mos rasm tanlash uchun"
    },
    {
        "q": "HTML’da <source> tegi qayerda ishlatiladi?",
        "options": [
            "<audio> va <video> ichida",
            "<form> ichida",
            "<img> ichida"
        ],
        "answer": "<audio> va <video> ichida"
    },
    {
        "q": "HTML’da <noscript> tegi nima qiladi?",
        "options": [
            "Skriptni o‘chiradi",
            "JavaScript o‘chirib qo‘yilgan foydalanuvchilarga matn ko‘rsatadi",
            "Serverdagi kodni yashiradi"
        ],
        "answer": "JavaScript o‘chirib qo‘yilgan foydalanuvchilarga matn ko‘rsatadi"
    },
    {
        "q": "<data> tegi nimani bildiradi?",
        "options": [
            "Jadvallarni yaratadi",
            "Script kodini o‘rnatadi",
            "Ma’lumot qiymatini mashina tomonidan o‘qiladigan shaklda saqlaydi"
        ],
        "answer": "Ma’lumot qiymatini mashina tomonidan o‘qiladigan shaklda saqlaydi"
    },
    {
        "q": "<b> va <strong> teglari orasidagi farq nimada?",
        "options": [
            "<b> faqat vizual, <strong> esa semantik urg‘u beradi",
            "Ikkalasi ham bir xil",
            "<strong> matnni kichik qiladi"
        ],
        "answer": "<b> faqat vizual, <strong> esa semantik urg‘u beradi"
    },
    {
        "q": "<link rel='preload'> nima uchun ishlatiladi?",
        "options": [

            "Sahifadagi linklarni optimallashtirish uchun",
            "External CSS ulash uchun",
            "Muayyan resursni oldindan yuklash uchun"
        ],
        "answer": "Muayyan resursni oldindan yuklash uchun"
    },
    {
        "q": "<abbr> tegi nimani bildiradi?",
        "options": [
            "Qisqartma so‘z yoki iborani belgilaydi",
            "Matnga izoh qo‘shadi",
            "Paragraf yaratadi"
        ],
        "answer": "Qisqartma so‘z yoki iborani belgilaydi"
    },
    {
        "q": "HTML’da <template> tegi nima uchun ishlatiladi?",
        "options": [
            "JavaScript yordamida dinamik kiritiladigan tarkibni saqlash uchun",
            "Faylni import qilish uchun",
            "Server bilan aloqani o‘rnatish uchun"
        ],
        "answer": "JavaScript yordamida dinamik kiritiladigan tarkibni saqlash uchun"
    },
    {
        "q": "HTML’da <iframe> tegi xavfsizlik nuqtayi nazaridan qanday xavf tug‘dirishi mumkin?",
        "options": [
            "Uchinchi tomon sahifalari orqali XSS yoki phishing hujumlariga yo‘l ochadi",
            "Brauzerni sekinlashtiradi, xolos",
            "HTML faylini buzadi"
        ],
        "answer": "Uchinchi tomon sahifalari orqali XSS yoki phishing hujumlariga yo‘l ochadi"
    },
    {
        "q": "HTML5’da ‘contenteditable’ atributi nima qiladi?",
        "options": [
            "Elementni foydalanuvchi tomonidan tahrir qilinadigan holga keltiradi",
            "Matnni faqat o‘qish rejimiga o‘tkazadi",
            "HTML kodini avtomatik tuzatadi"
        ],
        "answer": "Elementni foydalanuvchi tomonidan tahrir qilinadigan holga keltiradi"
    },
    {
        "q": "<time datetime='2025-10-14'>14-oktabr 2025</time> tegi nima maqsadda ishlatiladi?",
        "options": [
            "Sana yoki vaqtni semantik tarzda ifodalash uchun",
            "Brauzer vaqt zonasini o‘zgartirish uchun",
            "Taymer yaratish uchun"
        ],
        "answer": "Sana yoki vaqtni semantik tarzda ifodalash uchun"
    },
]


def test_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Testni boshlash")],
        ],
        resize_keyboard=True
    )


@test.message(F.text == "📝 Testni boshlash")
async def start_test(message: Message, state: FSMContext):
    await state.set_state(TestStates.waiting_for_answer)
    await message.answer(
        f"Test boshlandi!\n\n❓ Savol: {html_savoli['question']}\n\n"
        f"Javobingizni yozing:"
    )


@test.message(TestStates.waiting_for_answer)
async def check_answer(message: Message, state: FSMContext):
    user_answer = message.text.lower().strip()
    correct_answer = html_savoli["answer"]

    if user_answer == correct_answer:
        await message.answer("✅ Togri javob", reply_markup=test_start_keyboard())
    else:
        await message.answer(f"❌ Notogri", parse_mode="HTML",
                             reply_markup=test_start_keyboard())

    await state.clear()
