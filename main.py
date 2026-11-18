
import os
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import AsyncOpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DAILY_LIMIT = 10
MODEL = "gpt-4o-mini"

histories = {}
usage = {}


def today():
    return datetime.now(timezone.utc).date().isoformat()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я GPT.AI 🤖\n\n"
        "Я ИИ-ассистент, который поможет с вопросами, "
        "идеями, объяснениями и многим другим.\n\n"
        "У тебя 10 бесплатных запросов в сутки.\n"
        "Просто напиши мне сообщение!"
    )


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    histories[user_id] = []
    await update.message.reply_text("Новый диалог начат! 🆕")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — запустить бота\n"
        "/new — начать новый диалог\n"
        "/help — помощь"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if usage.get(user_id, {}).get("date") != today():
        usage[user_id] = {"date": today(), "count": 0}

    if usage[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text(
            "На сегодня бесплатные запросы закончились 😔\n"
            "Лимит обновится завтра."
        )
        return

    if user_id not in histories:
        histories[user_id] = []

    histories[user_id].append({"role": "user", "content": text})

    # Сохраняем только последние сообщения
    histories[user_id] = histories[user_id][-12:]

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты GPT.AI — полезный, дружелюбный "
                        "и умный ИИ-ассистент. Отвечай понятно "
                        "на языке пользователя."
                    )
                },
                *histories[user_id]
            ]
        )

        answer = response.choices[0].message.content

        histories[user_id].append(
            {"role": "assistant", "content": answer}
        )
        usage[user_id]["count"] += 1

        await update.message.reply_text(answer)

    except Exception:
        if histories[user_id] and histories[user_id][-1]["role"] == "user":
            histories[user_id].pop()

        await update.message.reply_text(
            "Не удалось получить ответ 😔 Попробуй ещё раз позже."
        )


def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        raise RuntimeError("Не заданы токены в переменных окружения!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_chat))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("GPT.AI запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
  
