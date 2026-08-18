from pyrogram import filters
from pyrogram.types import Message
from bot.app import app
from bot.keyboards import main_menu
from bot.db import upsert_user, get_user, find_by_referral_code

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    u = message.from_user
    existing = await get_user(u.id)

    # Telegram deep-link: /start ref_XXXX
    referral_code = None
    if len(message.command) > 1:
        payload = message.command[1].strip()
        if payload.startswith("ref_"):
            referral_code = payload[4:]

    data = {
        "username": u.username,
        "first_name": u.first_name,
    }

    # Referral is locked on first attribution only.
    if not existing:
        data["referral_code"] = str(u.id)
        data["successful_referrals"] = 0
        data["discount_credits"] = 0
        data["referral_credited"] = False

        if referral_code:
            referrer = await find_by_referral_code(referral_code)
            if referrer and referrer["user_id"] != u.id:
                data["referred_by"] = referrer["user_id"]

        await upsert_user(u.id, **data)
    else:
        await upsert_user(u.id, **data)

    text = (
        f"👋 Welcome {u.first_name or 'User'}!\n\n"
        "⭐ Premium Membership\n"
        "Fast activation after admin approval.\n\n"
        "Choose an option below:"
    )
    if referral_code and existing is None and data.get("referred_by"):
        text += "\n\n🎁 Referral tracked! Your friend will earn a 5% discount credit after your first successful premium purchase."

    await message.reply_text(text, reply_markup=main_menu())

@app.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    await message.reply_text(
        "Use /plans to view premium plans.\n"
        "Use /status to check membership.\n"
        "Use /referral to get your personal referral link."
    )

@app.on_message(filters.command("referral"))
async def referral_cmd(_, message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await upsert_user(message.from_user.id, referral_code=str(message.from_user.id), username=message.from_user.username, first_name=message.from_user.first_name)
        user = await get_user(message.from_user.id)

    me = await app.get_me()
    code = user.get("referral_code") or str(message.from_user.id)
    link = f"https://t.me/{me.username}?start=ref_{code}"
    credits = int(user.get("discount_credits", 0))
    successful = int(user.get("successful_referrals", 0))

    await message.reply_text(
        "🎁 **Referral Program**\n\n"
        f"🔗 Your referral link:\n{link}\n\n"
        f"👥 Successful referrals: {successful}\n"
        f"🎟️ Available 5% discount credits: {credits}\n\n"
        "Every friend who completes an approved premium purchase gives you **one 5% discount on your next premium purchase**."
    )
