from datetime import datetime, timezone
from pyrogram import filters
from pyrogram.types import CallbackQuery, Message
from bot.app import app
from bot.config import ADMIN_IDS, PLAN_MAP
from bot.db import get_payment, update_payment, get_user, upsert_user, users, payments, award_referral_discount
from bot.keyboards import admin_payment_menu
from bot.services.premium import activate_premium, make_invite, remove_from_group

admin_filter = filters.user(list(ADMIN_IDS))

@app.on_callback_query(filters.regex("^approve:"))
async def approve(_, cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("Unauthorized.", show_alert=True)
    payment_id = cq.data.split(":", 1)[1]
    payment = await get_payment(payment_id)
    if not payment or payment.get("status") != "pending":
        return await cq.answer("Payment is no longer pending.", show_alert=True)

    plan = PLAN_MAP[payment["plan_id"]]
    expiry = await activate_premium(payment["user_id"], plan, payment_id)
    await update_payment(payment_id, status="approved", approved_by=cq.from_user.id, approved_at=datetime.now(timezone.utc))

    # Consume one 5% referral discount credit only after admin approves the payment.
    if payment.get("discount_credit_used"):
        await users.update_one(
            {"user_id": payment["user_id"], "discount_credits": {"$gt": 0}},
            {"$inc": {"discount_credits": -1}}
        )

    # A successful referred purchase gives the referrer one 5% discount credit.
    referrer = await award_referral_discount(payment["user_id"])
    link = await make_invite(payment["user_id"])

    try:
        await app.send_message(
            payment["user_id"],
            f"🟢 **Premium Activated!**\n\n📦 {plan['name']}\n⏰ Expiry: {expiry}\n\n"
            "👇 Your personal Premium Group link is ready. It is valid for 24 hours and limited to one member.",
            reply_markup=__import__("bot.keyboards", fromlist=["join_menu"]).join_menu(link)
        )
    except Exception as e:
        print("User activation message error:", e)

    if referrer:
        try:
            await app.send_message(
                referrer["user_id"],
                "🎉 **Successful Referral!**\n\n"
                f"Your referral completed an approved premium purchase.\n"
                f"🎁 You earned **one 5% discount credit** for your next premium purchase.\n"
                f"🎟️ Available credits: {referrer.get('discount_credits', 1)}"
            )
        except Exception:
            pass

    await cq.message.edit_caption((cq.message.caption or "") + "\n\n🟢 APPROVED")
    await cq.answer("Premium activated.")

@app.on_callback_query(filters.regex("^reject:"))
async def reject(_, cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("Unauthorized.", show_alert=True)
    payment_id = cq.data.split(":", 1)[1]
    payment = await get_payment(payment_id)
    if not payment or payment.get("status") != "pending":
        return await cq.answer("Payment is no longer pending.", show_alert=True)

    await update_payment(payment_id, status="rejected", rejected_by=cq.from_user.id, rejected_at=datetime.now(timezone.utc))
    try:
        await app.send_message(payment["user_id"], "🔴 Your payment screenshot was rejected. Please make a valid payment and submit a new screenshot.")
    except Exception:
        pass
    await cq.message.edit_caption((cq.message.caption or "") + "\n\n🔴 REJECTED")
    await cq.answer("Payment rejected.")

@app.on_message(filters.command("admin") & admin_filter)
async def admin_cmd(_, message: Message):
    await message.reply_text(
        "⚙️ ADMIN PANEL\n\n"
        "/pending - pending payments\n"
        "/stats - statistics\n"
        "/premium USER_ID DAYS - manual premium\n"
        "/remove USER_ID - remove premium"
    )

@app.on_message(filters.command("pending") & admin_filter)
async def pending_cmd(_, message: Message):
    cursor = payments.find({"status": "pending"}).sort("created_at", 1)
    count = 0
    async for p in cursor:
        count += 1
        await message.reply_text(
            f"💳 {p['payment_id']}\n👤 {p['user_id']}\n📦 {p['plan_name']}\n💰 ₹{p['amount']}",
            reply_markup=admin_payment_menu(p["payment_id"])
        )
    if count == 0:
        await message.reply_text("No pending payments.")

@app.on_message(filters.command("stats") & admin_filter)
async def stats_cmd(_, message: Message):
    active = await users.count_documents({"premium_status": True})
    pending = await payments.count_documents({"status": "pending"})
    total = await payments.count_documents({"status": "approved"})
    await message.reply_text(f"📊 Statistics\n\n🟢 Active: {active}\n🟡 Pending: {pending}\n💳 Approved payments: {total}")

@app.on_message(filters.command("premium") & admin_filter)
async def manual_premium(_, message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply_text("Usage: /premium USER_ID DAYS")
    uid, days = int(parts[1]), int(parts[2])
    plan = {"id": "manual", "name": f"Manual {days} Days", "days": days, "price": 0}
    expiry = await activate_premium(uid, plan, "MANUAL")
    link = await make_invite(uid)
    await app.send_message(uid, f"🟢 Premium activated manually until {expiry}", reply_markup=__import__("bot.keyboards", fromlist=["join_menu"]).join_menu(link))
    await message.reply_text("Done.")

@app.on_message(filters.command("remove") & admin_filter)
async def remove_cmd(_, message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply_text("Usage: /remove USER_ID")
    uid = int(parts[1])
    await remove_from_group(uid)
    await upsert_user(uid, premium_status=False, joined_group=False)
    await message.reply_text("Removed and premium disabled.")
