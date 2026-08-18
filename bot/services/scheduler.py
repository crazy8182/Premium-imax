import asyncio
from datetime import datetime, timedelta, timezone
from bot.config import CHECK_INTERVAL_SECONDS, REMINDER_HOURS
from bot.db import expired_users, active_users, upsert_user
from bot.services.premium import is_member, remove_member, make_invite

async def process(bot):
    now = datetime.now(timezone.utc)

    async for user in expired_users():
        uid=user["user_id"]
        await remove_member(bot, uid)
        await upsert_user(uid, premium_status=False, joined_group=False)
        try:
            await bot.send_message(uid, "🔴 Your premium membership has expired and you have been removed from the Premium Group.")
        except Exception:
            pass

    async for user in active_users():
        uid=user["user_id"]
        if user.get("premium_expiry") and user["premium_expiry"] <= now:
            continue
        inside=await is_member(bot, uid)
        if inside:
            if not user.get("joined_group"):
                await upsert_user(uid, joined_group=True)
            continue
        last=user.get("last_reminder")
        if last and now-last < timedelta(hours=REMINDER_HOURS):
            continue
        try:
            link=await make_invite(bot, uid)
            await bot.send_message(uid,
                "⏰ Reminder: your premium is active, but you have not joined the Premium Group yet.",
                reply_markup=__import__("bot.keyboards",fromlist=["join_menu"]).join_menu(link))
            await upsert_user(uid,last_reminder=now)
        except Exception as e:
            print(f"Reminder error for {uid}: {e}", flush=True)

async def scheduler_loop(bot):
    while True:
        try:
            await process(bot)
        except Exception as e:
            print(f"Scheduler error: {e}", flush=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
