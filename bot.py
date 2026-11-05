import random
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiohttp import web

# Токен берётся из переменной окружения BOT_TOKEN (не храните его в коде!)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

# Папка с картинками рядом с этим файлом
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

bot = Bot(token=TOKEN)
dp = Dispatcher()

CS_PLAYERS = [
    "s1mple", "electronic", "perfecto", "strogo", "FalleN",
    "yuurih", "YEKINDAR", "KSCERATO", "molodoy", "apEX",
    "ropz", "ZywOo", "flameZ", "mezii", "NiKo", "TeSeS",
    "m0NESY", "kyxsan", "kyousuke", "Brollan", "torzsi",
    "Spinx", "Jimpphat", "xertioN", "bLitz", "Techno",
    "mzinho", "910", "chopper", "sh1ro", "tN1R", "donk",
    "zweih", "Aleksib", "iM", "b1t", "w0nderful", "makazze",
    "MAJ3R", "XANTARES", "woxic", "Wicadia", "jottAAA", "huNter-",
    "malbsMd", "SunPayus", "HeavyGod", "MATYS", "dgt", "biguzera",
    "dav1deuS", "nqz", "snow", "device", "Magisk", "HooXi", "jabbi",
    "Staehr", "karrigan", "frozen", "Twistzz", "broky", "jcobbb"
]

# user_id : game-data
games = {}


# ===== /start =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="3 игрока", callback_data="players_3")
    kb.button(text="4 игрока", callback_data="players_4")
    kb.button(text="5 игроков", callback_data="players_5")
    kb.adjust(1)
    await message.answer("Выберите количество игроков:", reply_markup=kb.as_markup())


# ===== Выбор количества игроков =====
@dp.callback_query(F.data.startswith("players_"))
async def choose_players(callback: types.CallbackQuery):
    n = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    spy_chance = {3: 0.33, 4: 0.25, 5: 0.20}[n]
    common_card = random.choice(CS_PLAYERS)

    roles = []
    for i in range(n):
        if random.random() < spy_chance and "Шпион" not in roles:
            roles.append("Шпион")
        else:
            roles.append(common_card)

    if "Шпион" not in roles:
        roles[random.randint(0, n - 1)] = "Шпион"

    random.shuffle(roles)

    games[user_id] = {
        "players": n,
        "current": 1,
        "roles": roles,
        "last_photo": None
    }

    kb = InlineKeyboardBuilder()
    kb.button(text="Начать", callback_data="start_game")
    kb.adjust(1)

    await callback.message.edit_text(
        f"Вы выбрали {n} игроков. Готовы начать?",
        reply_markup=kb.as_markup()
    )


# ===== Начало игры =====
@dp.callback_query(F.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = games.get(user_id)
    if not game:
        await callback.message.edit_text("Ошибка: игра не найдена.")
        return

    # --- удаляем сообщение "Готовы начать?" ---
    try:
        await callback.message.delete()
    except:
        pass

    # --- создаём новое сообщение для первого игрока с кнопкой "Показать карту" ---
    kb = InlineKeyboardBuilder()
    kb.button(text="Показать карту", callback_data="show_card")
    kb.adjust(1)

    msg = await callback.message.answer(
        f"Передайте телефон игроку 1.",
        reply_markup=kb.as_markup()
    )

    # сохраняем ID сообщения для удаления в hide_card
    game["last_msg"] = {"chat_id": msg.chat.id, "message_id": msg.message_id}

# ===== Показ карты =====
@dp.callback_query(F.data == "show_card")
async def show_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = games.get(user_id)

    if not game:
        await callback.message.edit_text("Ошибка: игра не найдена.")
        return

    idx = game["current"] - 1
    role = game["roles"][idx]

    cards_dir = os.path.join(BASE_DIR, "cards")

    if role == "Шпион":
        photo_path = os.path.join(cards_dir, "spy.png")
        if not os.path.exists(photo_path):
            photo_path = os.path.join(cards_dir, "spy.PNG")
    else:
        safe_name = "".join(c if c.isalnum() else "_" for c in role)
        photo_path = os.path.join(cards_dir, f"{safe_name}.png")
        if not os.path.exists(photo_path):
            photo_path = os.path.join(cards_dir, "common.png")

    kb = InlineKeyboardBuilder()
    kb.button(text="Скрыть", callback_data="hide_card")
    kb.adjust(1)

    photo_msg = await callback.message.answer_photo(
        photo=types.FSInputFile(photo_path),
        caption=f"Твоя карта:\n👉 {role}",
        reply_markup=kb.as_markup()
    )

    game["last_photo"] = {
        "chat_id": photo_msg.chat.id,
        "message_id": photo_msg.message_id
    }


# ===== Скрыть карту =====
@dp.callback_query(F.data == "hide_card")
async def hide_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = games.get(user_id)

    if not game:
        await callback.message.answer("Ошибка: игра не найдена.")
        return

    # --- 1. Удаляем фото ---
    last_photo = game.get("last_photo")
    if last_photo:
        try:
            await bot.delete_message(last_photo["chat_id"], last_photo["message_id"])
        except:
            pass
        game["last_photo"] = None

    # --- 2. Удаляем сообщение с кнопкой "Скрыть" ---
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

    # --- 3. Удаляем прошлое сообщение “Передайте телефон” ---
    last_msg = game.get("last_msg")
    if last_msg:
        try:
            await bot.delete_message(last_msg["chat_id"], last_msg["message_id"])
        except:
            pass
        game["last_msg"] = None

    # --- 4. Переход к следующему игроку ---
    game["current"] += 1

    # --- 5. Если игроки закончились ---
    if game["current"] > game["players"]:
        kb = InlineKeyboardBuilder()
        kb.button(text="Заново", callback_data="restart")
        kb.adjust(1)

        msg = await callback.message.answer(
            "Все игроки посмотрели карты.\nИгра окончена!",
            reply_markup=kb.as_markup()
        )
        # очищаем игру
        del games[user_id]
        return

    # --- 6. Отправляем новое сообщение “Передайте телефон” ---
    kb = InlineKeyboardBuilder()
    kb.button(text="Показать карту", callback_data="show_card")
    kb.adjust(1)

    msg = await callback.message.answer(
        f"Передайте телефон игроку {game['current']}.",
        reply_markup=kb.as_markup()
    )

    # сохраняем ID сообщения, чтобы удалить в следующем шаге
    game["last_msg"] = {"chat_id": msg.chat.id, "message_id": msg.message_id}



# ===== Перезапуск =====
@dp.callback_query(F.data == "restart")
async def restart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in games:
        del games[user_id]

    kb = InlineKeyboardBuilder()
    kb.button(text="3 игрока", callback_data="players_3")
    kb.button(text="4 игрока", callback_data="players_4")
    kb.button(text="5 игроков", callback_data="players_5")
    kb.adjust(1)

    await callback.message.edit_text(
        "Выберите количество игроков:",
        reply_markup=kb.as_markup()
    )


# ===== Запуск =====
async def health(request):
    return web.Response(text="OK")


async def start_web_server():
    # Маленький веб-сервер нужен бесплатным хостингам (Render, Koyeb),
    # чтобы сервис считался "живым" и его можно было пинговать.
    port = os.getenv("PORT")
    if not port:
        return
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(port)).start()
    print(f"Health-сервер на порту {port}")


async def main():
    await start_web_server()
    print("Бот запущен…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
