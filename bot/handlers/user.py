import uuid
from datetime import datetime, timezone
from pathlib import Path
from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from bot.app import app
from bot.config import PLAN_MAP, UPI_ID, UPI_NAME, PAYMENT_QR_PATH, ADMIN_IDS
from bot.db import upsert_user, create_payment, get_user
from bot.keyboards import plans_menu, payment_menu, main_menu, join_menu, admin_payment_menu
from bot.services.premium import make_invite, is_in_group

def discounted_price(price: int, credits: int):
    if credits > 0:
        return max(1, round(price * 0.95))
    return price

@app.on_callback_query(filters.regex("^plans$"))
async def plans_cb(_, cq: CallbackQuery):
    user = await get_user(cq.from_user.id)
    credits = int(user.get("discount_credits", 0)) if user else 0
    if credits:
        text = f"⭐ Choose your Premium Plan:\n\n🎁 You have {credits} × 5% discount credit. One credit will be used on your next purchase."
        # Build a custom keyboard with discounted prices.
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        rows = []
        for p in PLAN_MAP.values():
            price = discounted_price(p["price"], credits)
            rows.append([InlineKeyboardButton(f"🟢 {p['name']} — ₹{price}", callback_data=f"plan:{p['id']}")])
        rows.append([InlineKeyboardButton("🔴 CANCEL", callback_data="home")])
        await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))
    else:
        await cq.message.edit_text("⭐ Choose your Premium Plan:", reply_markup=plans_menu())
    await cq.answer()

@app.on_message(filters.command("plans"))
async def plans_cmd(_, message: Message):
    user = await get_user(message.from_user.id)
    credits = int(user.get("discount_credits", 0)) if user else 0
    if credits:
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        rows = []
        for p in PLAN_MAP.values():
            price = discounted_price(p["price"], credits)
            rows.append([InlineKeyboardButton(f"🟢 {p['name']} — ₹{price}", callback_data=f"plan:{p['id']}")])
        rows.append([InlineKeyboardButton("🔴 CANCEL", callback_data="home")])
        await message.reply_text(
            f"⭐ Choose your Premium Plan:\n\n🎁 5% discount available — one credit will be used.",
            reply_markup=InlineKeyboardMarkup(rows)
        )
    else:
        await message.reply_text("⭐ Choose your Premium Plan:", reply_markup=plans_menu())

@app.on_callback_query(filters.regex("^plan:"))
async def plan_cb(_, cq: CallbackQuery):
    pid = cq.data.split(":", 1)[1]
    plan = PLAN_MAP.get(pid)
    if not plan:
        return await cq.answer("Plan not found.", show_alert=True)

    user = await get_user(cq.from_user.id)
    credits = int(user.get("discount_credits", 0)) if user else 0
    price = discounted_price(plan["price"], credits)

    discount_text = ""
    if credits:
        discount_text = f"\n🎁 Referral discount: 5%\n💰 Original: ₹{plan['price']}\n💵 Pay only: **₹{price}**\n"

    text = (
        f"⭐ **{plan['name']} Premium**\n\n"
        f"⏳ Validity: **{plan['days']} days**\n"
        f"{discount_text}\n"
        f"💳 UPI ID: `{UPI_ID}`\n"
        f"👤 Name: {UPI_NAME}\n\n"
        "1️⃣ Pay the exact amount shown above.\n"
        "2️⃣ Tap **I HAVE PAID**.\n"
        "3️⃣ Send the payment screenshot in this chat."
    )
    path = Path(PAYMENT_QR_PATH)
    if path.exists():
        await cq.message.reply_photo(str(path), caption=text, reply_markup=payment_menu(pid))
    else:
        await cq.message.edit_text(text, reply_markup=payment_menu(pid))
    await cq.answer()

@app.on_callback_query(filters.regex("^paid:"))
async def paid_cb(_, cq: CallbackQuery):
    pid = cq.data.split(":", 1)[1]
    if pid not in PLAN_MAP:
        return await cq.answer("Invalid plan.", show_alert=True)
    await upsert_user(cq.from_user.id, pending_plan=pid)
    await cq.message.reply_text("📸 Now send your **payment screenshot** here.")
    await cq.answer("Waiting for screenshot.")

@app.on_message(filters.photo)
async def payment_screenshot(_, message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    pid = user.get("pending_plan") if user else None
    if not pid or pid not in PLAN_MAP:
        return

    plan = PLAN_MAP[pid]
    credits = int(user.get("discount_credits", 0))
    use_discount = credits > 0
    final_amount = discounted_price(plan["price"], credits)

    payment_id = uuid.uuid4().hex[:12].upper()
    await create_payment({
        "payment_id": payment_id,
        "user_id": uid,
        "username": message.from_user.username,
        "plan_id": pid,
        "plan_name": plan["name"],
        "original_amount": plan["price"],
        "discount_percent": 5 if use_discount else 0,
        "discount_credit_used": use_discount,
        "amount": final_amount,
        "status": "pending",
        "screenshot_file_id": message.photo.file_id,
        "created_at": datetime.now(timezone.utc)
    })
    await upsert_user(uid, pending_plan=None)

    caption = (
        "💳 **NEW PREMIUM PAYMENT**\n\n"
        f"🆔 Payment: `{payment_id}`\n"
        f"👤 User: {message.from_user.mention}\n"
        f"🆔 User ID: `{uid}`\n"
        f"📦 Plan: {plan['name']}\n"
        f"💰 Original: ₹{plan['price']}\n"
        f"🎁 Discount: {5 if use_discount else 0}%\n"
        f"💵 Expected Amount: ₹{final_amount}\n\n"
        "Review the screenshot and choose:"
    )
    for admin in ADMIN_IDS:
        try:
            await app.send_photo(admin, message.photo.file_id, caption=caption,
                                 reply_markup=admin_payment_menu(payment_id))
        except Exception as e:
            print("Admin notification error:", e)

    await message.reply_text("✅ Screenshot received. Your payment is under admin verification. You will be notified after approval.")

@app.on_callback_query(filters.regex("^status$"))
async def status_cb(_, cq: CallbackQuery):
    user = await get_user(cq.from_user.id)
    if not user or not user.get("premium_status"):
        text = "🔴 No active premium membership."
    else:
        expiry = user.get("premium_expiry")
        text = f"🟢 Premium Active\n\n📦 Plan: {user.get('premium_plan_name')}\n⏰ Expiry: {expiry}"
    await cq.message.reply_text(text)
    await cq.answer()

@app.on_message(filters.command("status"))
async def status_cmd(_, message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.get("premium_status"):
        return await message.reply_text("🔴 No active premium membership.")
    await message.reply_text(f"🟢 Premium Active\n📦 {user.get('premium_plan_name')}\n⏰ Expiry: {user.get('premium_expiry')}")

@app.on_callback_query(filters.regex("^check_membership$"))
async def check_membership(_, cq: CallbackQuery):
    inside = await is_in_group(cq.from_user.id)
    if inside:
        await upsert_user(cq.from_user.id, joined_group=True)
        await cq.answer("🟢 Membership verified!", show_alert=True)
        await cq.message.edit_text("🟢 You are a member of the Premium Group.")
    else:
        await cq.answer("🔴 You are not in the Premium Group yet.", show_alert=True)

@app.on_callback_query(filters.regex("^home$"))
async def home_cb(_, cq: CallbackQuery):
    await cq.message.edit_text("🏠 Premium Membership", reply_markup=main_menu())
    await cq.answer()

@app.on_callback_query(filters.regex("^help$"))
async def help_cb(_, cq: CallbackQuery):
    await cq.message.reply_text("Use BUY PREMIUM to purchase. Use /referral to get your referral link.")
    await cq.answer()
