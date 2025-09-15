import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import mention_html
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")
CHANNEL_URL = os.getenv("CHANNEL_URL")
SUPPORT_GROUP_URL = os.getenv("SUPPORT_GROUP_URL")

mongo_client = MongoClient(MONGO_URL)
db = mongo_client["NYCREATION"]
users_col = db["users"]
groups_col = db["groups"]

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        users_col.update_one({"_id": user.id}, {"$set": {"name": user.full_name}}, upsert=True)
    elif chat.type in ["group", "supergroup"]:
        groups_col.update_one({"_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)

    keyboard = [
        [InlineKeyboardButton("📢 𝐂ʜᴀɴɴᴇʟ", url=CHANNEL_URL)],
        [InlineKeyboardButton("💬 𝐒ᴜᴘᴘᴏʀᴛ 𝐆ʀᴏᴜᴘ", url=SUPPORT_GROUP_URL)],
        [InlineKeyboardButton("ℹ️ 𝐇ᴇʟᴘ", callback_data="help")]
    ]

    text = (
        " <b>ʜᴇʏ {0} 🥀,</b>"
        "✨ <b>Wᴇʟᴄᴏᴍᴇ ᴛᴏ ᴇᴅɪᴛ ɢᴜʀᴅɪᴀɴ ʙᴏᴛ </b> ✨\n\n"
        "🔹 <b>ᴛʜɪs ʙᴏᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇs ᴇᴅɪᴛᴇᴅ ᴍᴇssᴀɢᴇs ɪɴ ɢʀᴏᴜᴘs.</b>\n"
        "🔹 <b>ʜᴇʟᴘs ᴍᴀɪɴᴛᴀɪɴ ᴛʀᴀɴsᴘᴀʀᴇɴᴄʏ ɪɴ ᴄᴏɴᴠᴇʀsᴀᴛɪᴏɴ.</b>\n\n"
        "<blockquote> ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ & ɢɪᴠᴇ Dᴇʟᴇᴛᴇ ᴍᴇssᴀɢᴇ ᴘᴇʀᴍɪssɪᴏɴ.</blockquote>\n\n"
        "ᴍᴀᴅᴇ ʙʏ ↣ [𓂃❛ 𝐙 𝛆 ʀ 𝛂 ƚ 𝐡 𝚘 δ](https://t.me/Og_Zerathos) ♡")

    


    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        text = (
            "⚙️ <b>Help Menu</b>\n\n"
            "🔹 <b>Message Guardian:</b> If someone edits a message in group, bot will delete it.\n"
            "🔹 <b>Broadcast:</b> Only Admin can broadcast messages to all users & groups.\n\n"
            "✅ Make sure bot has <b>Delete Message</b> rights in groups."
        )
        await query.edit_message_text(text, parse_mode="HTML")


async def edited_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.edited_message
    if not message:
        return

    chat = message.chat
    user = message.from_user

    try:
        await message.delete()
        warn_text = f"⚠️ {mention_html(user.id, user.first_name)} ʏᴏᴜ ᴇᴅɪᴛᴇᴅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ᴀɴᴅ ɪ ᴅᴇʟᴇᴛᴇᴅ ɪᴛ 🤡."
        await chat.send_message(warn_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to delete edited message: {e}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CURRENT_ADMIN_ID = 7574330905
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and user_id != CURRENT_ADMIN_ID:
        return await update.message.reply_text("❌ You are not authorized to use this command.")

    if not context.args:
        return await update.message.reply_text("Usage: /broadcast <message>")

    text = " ".join(context.args)

    for user in users_col.find():
        try:
            await context.bot.send_message(chat_id=user["_id"], text=text)
        except Exception as e:
            logger.warning(f"Failed to send to user {user['_id']}: {e}")

    for group in groups_col.find():
        try:
            await context.bot.send_message(chat_id=group["_id"], text=text)
        except Exception as e:
            logger.warning(f"Failed to send to group {group['_id']}: {e}")

    await update.message.reply_text("✅ Broadcast sent to all users and groups.")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="help"))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, edited_message_handler))
    application.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Bot started...")
    application.run_polling()


if __name__ == "__main__":
    main()
