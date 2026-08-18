from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS, PLAN_MAP
from bot.db import get_payment, update_payment, get_user, upsert_user, users, payments, award_referral
from bot.services.premium import make_invite, remove_member

def admin_only(uid): return uid in ADMIN_IDS

async def approve(update, context):
    q=update.callback_query
    if not admin_only(q.from_user.id): return await q.answer("Unauthorized.",show_alert=True)
    await q.answer()
    pid=q.data.split(":",1)[1]
    pmt=await get_payment(pid)
    if not pmt or pmt.get("status")!="pending": return await q.answer("Already processed.",show_alert=True)
    plan=PLAN_MAP[pmt["plan_id"]]
    now=datetime.now(timezone.utc)
    user=await get_user(pmt["user_id"])
    old=user.get("premium_expiry") if user else None
    expiry=(old+timedelta(days=plan["days"])) if old and old>now else now+timedelta(days=plan["days"])
    await upsert_user(pmt["user_id"],premium_status=True,premium_plan=pmt["plan_id"],premium_plan_name=plan["name"],premium_start=now,premium_expiry=expiry,joined_group=False,last_reminder=None,approved_payment_id=pid)
    if pmt.get("discount_credit_used"):
        await users.update_one({"user_id":pmt["user_id"],"discount_credits":{"$gt":0}},{"$inc":{"discount_credits":-1}})
    referrer=await award_referral(pmt["user_id"])
    await update_payment(pid,status="approved",approved_by=q.from_user.id,approved_at=now)
    try:
        link=await make_invite(context.bot,pmt["user_id"])
        await context.bot.send_message(pmt["user_id"],f"🟢 Premium Activated!\n\n📦 {plan['name']}\n⏰ Expiry: {expiry}\n\nYour personal group link is valid for 24 hours and limited to one member.",reply_markup=__import__("bot.keyboards",fromlist=["join_menu"]).join_menu(link))
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
    await update.message.reply_text("⚙️ ADMIN\n/pending\n/stats\n/premium USER_ID DAYS\n/remove USER_ID")

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
    old=user.get("premium_expiry") if user else None
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
