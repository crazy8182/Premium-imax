from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS
from bot.db import users


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        return

    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text(
            "📢 <b>Broadcast</b>\n\n"
            "Jis message ko broadcast karna hai, us message par "
            "<b>Reply</b> karke /broadcast bhejiye.",
            parse_mode="HTML",
        )
        return

    status = await update.message.reply_text("📤 Broadcast start ho raha hai...")

    total = 0
    sent = 0
    failed = 0

    async for user in users.find({}, {"user_id": 1}):
        total += 1
        uid = user.get("user_id")

        if not uid:
            failed += 1
            continue

        try:
            await update.message.reply_to_message.copy(chat_id=int(uid))
            sent += 1
        except Exception:
            failed += 1

    await status.edit_text(
        "✅ <b>Broadcast Complete</b>\n\n"
        f"👥 Total users: <b>{total}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>",
        parse_mode="HTML",
    )
