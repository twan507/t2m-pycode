from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ID các nhóm nguồn và đích
source_group_1 = -1002081959670  # Nhóm nguồn 1
target_group_1 = -1002139140364  # Nhóm đích 1
reply_to_message_id_1 = 4

source_group_2 = -1002002317791  # Nhóm nguồn 2
target_group_2 = -1002139140364  # Nhóm đích 2
reply_to_message_id_2 = 3

try:

    async def handle_messages(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        # Kiểm tra nguồn và xử lý tương ứng
        if update.message.chat_id == source_group_1:
            text_to_send = update.message.text or "Tin nhắn không chứa văn bản."
            await context.bot.send_message(
                chat_id=target_group_1,
                text=text_to_send,
                reply_to_message_id=reply_to_message_id_1,
            )
        elif update.message.chat_id == source_group_2:
            text_to_send = update.message.text or "Tin nhắn không chứa văn bản."
            await context.bot.send_message(
                chat_id=target_group_2,
                text=text_to_send,
                reply_to_message_id=reply_to_message_id_2,
            )

    app = (
        ApplicationBuilder()
        .token("5893169055:AAEBvlKkeARb8MybRMZRBueVh9ukY8Ab_no")
        .build()
    )

    # Thêm một MessageHandler duy nhất
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("Running Telegram Bot...")
    app.run_polling()

except Exception as e:
    print(f"Error: {type(e).__name__}")
