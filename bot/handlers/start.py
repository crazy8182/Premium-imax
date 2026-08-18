from telegram import Update
from telegram.ext import ContextTypes
from bot.config import BOT_USERNAME
from bot.db import get_user, upsert_user, find_referrer
from bot.keyboards import main_menu

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
    await update.message.reply_text(
        f"👋 Welcome {u.first_name or 'User'}!\n\n⭐ Premium Membership\nChoose an option below:",
        reply_markup=main_menu()
    )

async def help_cmd(update, context):
    await update.message.reply_text("Use /plans to buy Premium.\nUse /status to check membership.\nUse /referral to get your referral link.")

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
