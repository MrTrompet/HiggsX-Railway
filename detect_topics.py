from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = "7339866415:AAG8DOd7OCkY6DZg9CKiDMP5BYtyK7VqD8I"  # <-- Reemplaza con tu token real

async def show_topic_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user.full_name
    message = update.message.text
    message_thread_id = update.message.message_thread_id  # Este es el ID del topic

    print(f"📥 Mensaje recibido de {user}")
    print(f"💬 Contenido: {message}")
    print(f"📌 chat_id: {chat_id}")
    print(f"🧵 message_thread_id: {message_thread_id}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Detectado:\n"
            f"chat_id: `{chat_id}`\n"
            f"message_thread_id: `{message_thread_id}`\n\n"
            f"Este es el ID del topic actual. Úsalo para segmentar mensajes."
        ),
        message_thread_id=message_thread_id
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    handler = MessageHandler(filters.TEXT & filters.ChatType.GROUPS, show_topic_info)
    app.add_handler(handler)

    print("🤖 Bot escuchando... Escribe en tus topics para detectar sus IDs.")
    app.run_polling()
