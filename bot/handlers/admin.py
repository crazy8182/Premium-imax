from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS, PLAN_MAP, offer_details
from bot.db import get_payment, update_payment, get_user, upsert_user, users, payments, award_referral
from bot.services.premium import make_invite, remove_member

def admin_only(uid): return uid in ADMIN_IDS

def utc_aware(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return dt

async def approve(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.",show_alert=True)
    await q.answer()
    pid=q.data.split(":",1)[1]
    pmt=await get_payment(pid)
    if not pmt or pmt.get("status")!="pending": return await q.answer("Already processed.",show_alert=True)
    plan=PLAN_MAP[pmt["plan_id"]]
    # Use the offer snapshot saved when the user submitted payment.
    offer_days=int(pmt.get("offer_days") or offer_details(plan)["days"])
    now=datetime.now(timezone.utc)
    user=await get_user(pmt["user_id"])
    old=utc_aware(user.get("premium_expiry")) if user else None
    expiry=(old+timedelta(days=offer_days)) if old and old>now else now+timedelta(days=offer_days)
    await upsert_user(
        pmt["user_id"],
        premium_status=True,
        premium_plan=pmt["plan_id"],
        premium_plan_name=plan["name"],
        premium_start=now,
        premium_expiry=expiry,
        joined_group=False,
        last_reminder=None,
        approved_payment_id=pid,
        expired_offer_until=None,
        expired_offer_last_reminder=None,
        expired_offer_reminders_sent=0,
    )
    if pmt.get("discount_credit_used"):
        await users.update_one({"user_id":pmt["user_id"],"discount_credits":{"$gt":0}},{"$inc":{"discount_credits":-1}})
    referrer=await award_referral(pmt["user_id"])
    await update_payment(pid,status="approved",approved_by=q.from_user.id,approved_at=now)
    try:
        link=await make_invite(context.bot,pmt["user_id"])
        await context.bot.send_message(pmt["user_id"],f"🟢 Premium Activated!\n\n📦 {plan['name']}\n⏳ Validity: {offer_days} days\n⏰ Expiry: {expiry}\n\nYour personal group link is valid for 24 hours and limited to one member.",reply_markup=__import__("bot.keyboards",fromlist=["join_menu"]).join_menu(link))
    except Exception as e: print(f"Activation message error: {e}",flush=True)
    if referrer:
        try: await context.bot.send_message(referrer["user_id"],f"🎉 Successful Referral!\n\n🎁 You earned one 5% discount credit.\n🎟️ Available: {referrer.get('discount_credits',1)}")
        except Exception: pass
    try: await q.message.edit_caption((q.message.caption or "")+"\n\n🟢 APPROVED")
    except Exception: pass

async def reject(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.",show_alert=True)
    await q.answer()
    pid=q.data.split(":",1)[1]
    pmt=await get_payment(pid)
    if not pmt or pmt.get("status")!="pending": return await q.answer("Already processed.",show_alert=True)
    await update_payment(pid,status="rejected",rejected_by=q.from_user.id,rejected_at=datetime.now(timezone.utc))
    try: await context.bot.send_message(pmt["user_id"],"🔴 Your payment screenshot was rejected. Please submit a valid payment screenshot.")
    except Exception: pass
    try: await q.message.edit_caption((q.message.caption or "")+"\n\n🔴 REJECTED")
    except Exception: pass

async def admin_cmd(update, context):
    if not admin_only(update.effective_user.id): return
    await update.message.reply_text("⚙️ ADMIN\n/pending\n/stats\n/premium USER_ID DAYS\n/remove USER_ID\n/offer — Manage Premium Offers")

async def pending(update, context):
    if not admin_only(update.effective_user.id): return
    from bot.keyboards import admin_menu
    count=0
    async for p in payments.find({"status":"pending"}).sort("created_at",1):
        count+=1
        await update.message.reply_text(f"💳 {p['payment_id']}\n👤 {p['user_id']}\n📦 {p['plan_name']}\n💰 ₹{p['amount']}",reply_markup=admin_menu(p["payment_id"]))
    if not count: await update.message.reply_text("No pending payments.")

async def stats(update, context):
    if not admin_only(update.effective_user.id): return
    active=await users.count_documents({"premium_status":True})
    pending_n=await payments.count_documents({"status":"pending"})
    approved=await payments.count_documents({"status":"approved"})
    await update.message.reply_text(f"📊 Statistics\n\n🟢 Active: {active}\n🟡 Pending: {pending_n}\n💳 Approved: {approved}")

async def manual_premium(update, context):
    if not admin_only(update.effective_user.id): return
    if len(context.args)!=2: return await update.message.reply_text("/premium USER_ID DAYS")
    uid,days=int(context.args[0]),int(context.args[1])
    now=datetime.now(timezone.utc)
    user=await get_user(uid)
    old=utc_aware(user.get("premium_expiry")) if user else None
    expiry=(old+timedelta(days=days)) if old and old>now else now+timedelta(days=days)
    await upsert_user(uid,premium_status=True,premium_plan="manual",premium_plan_name=f"Manual {days} Days",premium_start=now,premium_expiry=expiry)
    link=await make_invite(context.bot,uid)
    await context.bot.send_message(uid,f"🟢 Premium activated until {expiry}",reply_markup=__import__("bot.keyboards",fromlist=["join_menu"]).join_menu(link))
    await update.message.reply_text("Done.")

async def remove_cmd(update, context):
    if not admin_only(update.effective_user.id): return
    if len(context.args)!=1: return await update.message.reply_text("/remove USER_ID")
    uid=int(context.args[0])
    await remove_member(context.bot,uid)
    await upsert_user(uid,premium_status=False,joined_group=False)
    await update.message.reply_text("Removed and premium disabled.")

# ---------------- ADMIN OFFER MANAGER ----------------
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from bot.config import PLANS, offer_details
from bot.services.offers import save_offer, clear_offer


def _offer_manager_keyboard():
    rows = []
    for p in PLANS:
        rows.append([InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"offer_plan:{p['id']}", style="primary")])
    rows.append([InlineKeyboardButton("📋 Current Offers", callback_data="offer_list", style="success")])
    return InlineKeyboardMarkup(rows)


def _offer_plan_keyboard(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Extra Days", callback_data=f"offer_type:{pid}:extra_days", style="success")],
        [InlineKeyboardButton("💸 Discount %", callback_data=f"offer_type:{pid}:discount", style="success")],
        [InlineKeyboardButton("❌ Disable Offer", callback_data=f"offer_disable:{pid}", style="danger")],
        [InlineKeyboardButton("🔙 Back", callback_data="offer_manager", style="primary")],
    ])

async def offer_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    await update.message.reply_text(
        "🔥 <b>Offer Manager</b>\n\nSelect a plan:",
        reply_markup=_offer_manager_keyboard(), parse_mode="HTML"
    )

async def offer_manager_cb(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.", show_alert=True)
    await q.answer()
    await q.message.edit_text("🔥 <b>Offer Manager</b>\n\nSelect a plan:", reply_markup=_offer_manager_keyboard(), parse_mode="HTML")

async def offer_plan_cb(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.", show_alert=True)
    await q.answer()
    pid=q.data.split(":",1)[1]
    p=PLAN_MAP.get(pid)
    if not p: return
    o=offer_details(p)
    status = "❌ No active offer"
    if o["active"]:
        status = f"🔥 {o['type']} | {o['value']} | {o['label'] or 'No label'}"
    await q.message.edit_text(f"📦 <b>{p['name']}</b>\n\nCurrent: {status}\n\nChoose offer type:", reply_markup=_offer_plan_keyboard(pid), parse_mode="HTML")

async def offer_type_cb(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.", show_alert=True)
    await q.answer()
    _,pid,kind=q.data.split(":")
    p=PLAN_MAP.get(pid)
    if not p: return
    context.user_data["offer_setup"]={"plan_id":pid,"type":kind,"step":"value"}
    unit="days" if kind=="extra_days" else "%"
    await q.message.edit_text(f"🔥 <b>{p['name']}</b>\n\nSend the offer value now.\nExample: <code>{7 if kind=='extra_days' else 20}</code> ({unit})\n\nSend 0 to cancel.", parse_mode="HTML")

async def offer_input(update, context):
    uid=update.effective_user.id
    if not admin_only(uid): return
    state=context.user_data.get("offer_setup")
    if not state: return
    text=(update.message.text or "").strip()
    if state["step"]=="value":
        try: value=int(text)
        except ValueError: return await update.message.reply_text("❌ Please send a number only.")
        if value<=0:
            context.user_data.pop("offer_setup",None)
            return await update.message.reply_text("❌ Offer setup cancelled.")
        if state["type"]=="discount" and value>100:
            return await update.message.reply_text("❌ Discount must be between 1 and 100%.")
        state["value"]=value
        state["step"]="label"
        return await update.message.reply_text("📝 Send offer name/label.\nExample: Independence Day Offer\nOr send <code>-</code> for no label.", parse_mode="HTML")
    if state["step"]=="label":
        state["label"]="" if text=="-" else text[:100]
        state["step"]="expiry"
        return await update.message.reply_text("⏰ Send validity in days.\nExample: <code>7</code>\nSend <code>0</code> for no expiry.", parse_mode="HTML")
    if state["step"]=="expiry":
        try: days=int(text)
        except ValueError: return await update.message.reply_text("❌ Please send a number only.")
        if days<0: return await update.message.reply_text("❌ Expiry days cannot be negative.")
        from datetime import datetime, timedelta, timezone
        expires_at=None if days==0 else datetime.now(timezone.utc)+timedelta(days=days)
        pid=state["plan_id"]
        await save_offer(pid,state["type"],state["value"],state["label"],expires_at)
        context.user_data.pop("offer_setup",None)
        p=PLAN_MAP[pid]
        o=offer_details(p)
        expiry_text="No expiry" if not expires_at else expires_at.strftime("%d-%m-%Y %H:%M UTC")
        await update.message.reply_text(f"✅ <b>Offer Activated</b>\n\n📦 {p['name']}\n🔥 {state['type']}\n💎 Value: {state['value']}\n📝 {state['label'] or 'No label'}\n⏰ Expiry: {expiry_text}", parse_mode="HTML")
        # Notify users with the new offer.
        text=(f"🔥 <b>New Premium Offer!</b>\n\n📦 {p['name']}\n"
              f"{'➕ +' + str(state['value']) + ' Extra Days' if state['type']=='extra_days' else '💸 ' + str(state['value']) + '% OFF'}\n"
              f"📝 {state['label'] or 'Special Offer'}\n\nUse /offers to view current offers.")
        async for u in users.find({"user_id":{"$exists":True}}, {"user_id":1}):
            try: await context.bot.send_message(u["user_id"], text, parse_mode="HTML")
            except Exception: pass

async def offer_disable_cb(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.", show_alert=True)
    await q.answer("Offer disabled.")
    pid=q.data.split(":",1)[1]
    p=PLAN_MAP.get(pid)
    if not p: return
    await clear_offer(pid)
    await q.message.edit_text(f"❌ Offer disabled for <b>{p['name']}</b>.", parse_mode="HTML", reply_markup=_offer_manager_keyboard())

async def offer_list_cb(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.", show_alert=True)
    await q.answer()
    lines=[]
    for p in PLANS:
        o=offer_details(p)
        if o["active"]:
            exp=""
            raw=o.get("expires_at")
            if raw: exp=f"\n⏰ Expiry: {raw}"
            lines.append(f"🔥 <b>{p['name']}</b> — {o['type']} {o['value']}\n📝 {o['label'] or 'No label'}{exp}")
    text="📋 <b>Current Offers</b>\n\n"+"\n\n".join(lines) if lines else "📋 <b>Current Offers</b>\n\n😔 No active offers."
    await q.message.edit_text(text, parse_mode="HTML", reply_markup=_offer_manager_keyboard())
    
