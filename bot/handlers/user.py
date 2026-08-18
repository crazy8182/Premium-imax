import uuid
from datetime import datetime, timezone
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import PLAN_MAP, UPI_ID, UPI_NAME, PAYMENT_QR_PATH, ADMIN_IDS, offer_details
from bot.db import get_user, upsert_user, create_payment
from bot.keyboards import plans_menu, payment_menu, main_menu, join_menu, offers_menu
from bot.services.premium import is_member, make_invite

def pricing(plan, credits):
    offer = offer_details(plan)
    base_price = offer["price"]
    final_price = round(base_price * 0.95) if credits else base_price
    return offer, final_price

def price(plan, credits):
    return pricing(plan, credits)[1]

async def plans(update, context):
    q=update.callback_query
    await q.answer()
    user=await get_user(q.from_user.id)
    credits=int(user.get("discount_credits",0)) if user else 0
    await q.edit_message_text("⭐ Choose your Premium Plan:\n\n🎁 5% discount available." if credits else "⭐ Choose your Premium Plan:", reply_markup=plans_menu(credits))

async def plans_cmd(update, context):
    user=await get_user(update.effective_user.id)
    credits=int(user.get("discount_credits",0)) if user else 0
    await update.message.reply_text("⭐ Choose your Premium Plan:", reply_markup=plans_menu(credits))

async def plan(update, context):
    q=update.callback_query
    await q.answer()
    pid=q.data.split(":",1)[1]
    p=PLAN_MAP.get(pid)
    if not p: return
    user=await get_user(q.from_user.id)
    credits=int(user.get("discount_credits",0)) if user else 0
    offer, final = pricing(p, credits)
    offer_line = ""
    if offer["active"]:
        if offer["type"] == "extra_days":
            offer_line = f"🔥 OFFER: +{offer['value']} extra days" + (f" — {offer['label']}" if offer['label'] else "") + "\n"
        elif offer["type"] == "discount":
            offer_line = f"🔥 OFFER: {offer['value']}% OFF" + (f" — {offer['label']}" if offer['label'] else "") + "\n"
    discount=f"🎁 Referral discount: 5%\n💰 Original: ₹{offer['price']}\n💵 Pay: ₹{final}\n\n" if credits else f"💰 Pay: ₹{final}\n\n"
    text=f"⭐ {p['name']} Premium\n\n⏳ Validity: {offer['days']} days\n{offer_line}{discount}💳 UPI ID: `{UPI_ID}`\n👤 Name: {UPI_NAME}\n\n1️⃣ Pay exact amount.\n2️⃣ Tap I HAVE PAID.\n3️⃣ Send screenshot here."
    path=Path(PAYMENT_QR_PATH)
    if path.exists():
        await q.message.reply_photo(photo=str(path),caption=text,reply_markup=payment_menu(pid))
    else:
        await q.edit_message_text(text,reply_markup=payment_menu(pid))

async def paid(update, context):
    q=update.callback_query
    await q.answer("Send your payment screenshot.")
    await upsert_user(q.from_user.id, pending_plan=q.data.split(":", 1)[1])

    keyboard = [
        [
            InlineKeyboardButton(
                "❌ Cancel Upload",
                callback_data="cancel_upload",
                style="danger"
            )
        ]
    ]

    await q.message.reply_text(
        "📸 Now send your payment screenshot here.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel_upload(update, context):
    q = update.callback_query
    await q.answer("Upload cancelled.")

    await upsert_user(q.from_user.id, pending_plan=None)

    await q.message.edit_text(
        f"👋 Welcome {q.from_user.first_name or 'User'}!\n\n"
        "⭐ Premium Membership\n"
        "Choose an option below:",
        reply_markup=main_menu()
    )

async def screenshot(update, context):
    if not update.message.photo: return
    uid=update.effective_user.id
    user=await get_user(uid)
    pid=user.get("pending_plan") if user else None
    if pid not in PLAN_MAP: return
    p=PLAN_MAP[pid]
    credits=int(user.get("discount_credits",0))
    use=credits>0
    offer, final=pricing(p,credits)
    payment_id=uuid.uuid4().hex[:12].upper()
    await create_payment({
        "payment_id":payment_id,"user_id":uid,"username":update.effective_user.username,
        "plan_id":pid,"plan_name":p["name"],"original_amount":p["price"],
        "offer_type":offer["type"],"offer_value":offer["value"],"offer_label":offer["label"],
        "offer_days":offer["days"],"offer_price":offer["price"],
        "discount_percent":5 if use else 0,"discount_credit_used":use,"amount":final,
        "status":"pending","screenshot_file_id":update.message.photo[-1].file_id,
        "created_at":datetime.now(timezone.utc)
    })
    await upsert_user(uid,pending_plan=None)
    caption=(f"💳 NEW PREMIUM PAYMENT\n\n🆔 `{payment_id}`\n👤 {update.effective_user.mention_html()}\n"
             f"🆔 User ID: `{uid}`\n📦 {p['name']}\n💰 Original: ₹{p['price']}\n"
             f"🔥 Offer: {offer['label'] or offer['type']} {offer['value'] if offer['active'] else ''}"
             f"\n⏳ Days: {offer['days']}\n🎁 Referral Discount: {5 if use else 0}%\n💵 Expected: ₹{final}\n\nApprove or cancel:")
    from bot.keyboards import admin_menu
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_photo(aid,update.message.photo[-1].file_id,caption=caption,parse_mode="HTML",reply_markup=admin_menu(payment_id))
        except Exception as e: print(f"Admin notify error: {e}",flush=True)
    await update.message.reply_text("✅ Screenshot received. Admin verification is pending.")

async def status(update, context):
    uid=update.effective_user.id
    user=await get_user(uid)
    if not user or not user.get("premium_status"):
        await update.message.reply_text("🔴 No active premium membership.")
        return
    await update.message.reply_text(f"🟢 Premium Active\n📦 {user.get('premium_plan_name')}\n⏰ Expiry: {user.get('premium_expiry')}")

async def status_cb(update, context):
    q=update.callback_query
    await q.answer()
    uid=q.from_user.id
    user=await get_user(uid)
    if not user or not user.get("premium_status"):
        await q.message.reply_text("🔴 No active premium membership.")
    else:
        await q.message.reply_text(f"🟢 Premium Active\n📦 {user.get('premium_plan_name')}\n⏰ Expiry: {user.get('premium_expiry')}")

async def check(update, context):
    q=update.callback_query
    await q.answer()
    if await is_member(context.bot,q.from_user.id):
        await upsert_user(q.from_user.id,joined_group=True)
        await q.message.edit_text("🟢 You are a member of the Premium Group.")
    else:
        await q.answer("🔴 You are not in the Premium Group.",show_alert=True)

async def home(update, context):
    q=update.callback_query
    await q.answer()
    await q.message.edit_text("🏠 Premium Membership",reply_markup=main_menu())

async def help_cb(update, context):
    q=update.callback_query
    await q.answer()
    await q.message.reply_text("Use BUY PREMIUM to purchase. Use /referral for your personal referral link.")

async def referral_cb(update, context):
    q=update.callback_query
    await q.answer()
    u=q.from_user
    user=await get_user(u.id)
    if not user:
        await upsert_user(u.id,referral_code=str(u.id),username=u.username,first_name=u.first_name)
        user=await get_user(u.id)
    me=await context.bot.get_me()
    link=f"https://t.me/{me.username}?start=ref_{user.get('referral_code',u.id)}"
    await q.message.reply_text(f"🎁 Referral Program\n\n🔗 {link}\n\n👥 Successful: {user.get('successful_referrals',0)}\n🎟️ 5% credits: {user.get('discount_credits',0)}")

async def text_log(update, context):
    if update.effective_message:
        print(f"UPDATE RECEIVED | user={update.effective_user.id if update.effective_user else 'unknown'} | text={(update.effective_message.text or '')[:100]}",flush=True)


async def offers_cb(update, context):
    q = update.callback_query
    await q.answer()
    from bot.config import PLANS, offer_details

    active = []
    for p in PLANS:
        offer = offer_details(p)
        if offer["active"]:
            detail = (f"➕ +{offer["value"]} Extra Days" if offer["type"] == "extra_days"
                      else f"💸 {offer["value"]}% OFF")
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

    await q.message.edit_text(text, reply_markup=offers_menu(), parse_mode="HTML")
