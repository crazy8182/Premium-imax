from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import BOT_USERNAME, ADMIN_IDS
from bot.db import get_user, upsert_user, find_referrer
from bot.keyboards import main_menu, offers_menu
from bot.config import PLANS, offer_details

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    user=await get_user(u.id)
    data={"username":u.username,"first_name":u.first_name}
    if not user:
        data.update({"referral_code":str(u.id),"successful_referrals":0,"discount_credits":0,"referral_credited":False})
        if context.args and context.args[0].startswith("ref_"):
            code=context.args[0][4:]
            ref=await find_referrer(code)
            if ref and ref["user_id"] != u.id:
                data["referred_by"]=ref["user_id"]
        await upsert_user(u.id,**data)
    else:
        await upsert_user(u.id,**data)
    tutorial_video = "https://t.me/c/4413195479/3"
    await update.message.reply_video(
        video=tutorial_video,
        caption=(
            "👋 <b>Welcome, {u.first_name or 'User'}!</b>\n\n"
            "Help k liye uper ki video dekhein.\n\n"
            "Premium lene ke liye pehle <b>Check Plans</b> pe tap karein.\n\n"
            "Agar payment already ho gaya hai, toh "
            "<b>Buy Premium</b> me category select karke "
            "<b>Paid</b> button pe tap karke apna payment proof submit karein."
        ),
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "💼 Contact Support",
                url=f'https://t.me/akImaxSupport_Bot',
                style="primary"
            )
        ]
    ]

    await update.message.reply_text(
        "🆘 <b>Support</b>\n\n"
        "Contact our team using the button below.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def referral(update, context):
    u=update.effective_user
    user=await get_user(u.id)
    if not user:
        await upsert_user(u.id, referral_code=str(u.id), username=u.username, first_name=u.first_name)
        user=await get_user(u.id)
    me=await context.bot.get_me()
    code=user.get("referral_code",str(u.id))
    link=f"https://t.me/{me.username}?start=ref_{code}"
    await update.message.reply_text(
        f"🎁 Referral Program\n\n🔗 {link}\n\n"
        f"👥 Successful referrals: {user.get('successful_referrals',0)}\n"
        f"🎟️ 5% discount credits: {user.get('discount_credits',0)}\n\n"
        "Each successful referred premium purchase gives you one 5% discount on your next purchase."
    )


async def offers(update, context):
    active = []
    for p in PLANS:
        offer = offer_details(p)
        if offer["active"]:
            if offer["type"] == "extra_days":
                detail = f"➕ +{offer["value"]} Extra Days"
            else:
                detail = f"💸 {offer["value"]}% OFF"
            label = f" — {offer["label"]}" if offer["label"] else ""
            active.append(
                f"🔥 <b>{p["name"]}</b>{label}\n"
                f"{detail}\n"
                f"⏳ Validity: {offer["days"]} days\n"
                f"💰 Price: ₹{offer["price"]}"
            )

    if not active:
        text = (
            "🔥 <b>Current Offers</b>\n\n"
            "😔 Koi active offers nahi hai abhi filhaal!\n\n"
            "New offer aane pe aapko notification mil jayega."
        )
    else:
        text = "🔥 <b>Current Offers</b>\n\n" + "\n\n".join(active)

    await update.message.reply_text(text, reply_markup=offers_menu(), parse_mode="HTML")
\n\nasync def get_video_id(update, context):\n    """TEMPORARY: Send a video to the bot to get its Telegram file_id.\n    Remove this function and its MessageHandler from bot/bot.py after copying the ID.\n    """\n    if update.effective_user.id not in ADMIN_IDS:\n        return\n    if update.message and update.message.video:\n        file_id = update.message.video.file_id\n        await update.message.reply_text(\n            f"🎥 <b>Video File ID:</b>\\n\\n<code>{file_id}</code>",\n            parse_mode="HTML"\n        )\n