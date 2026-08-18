import asyncio
from datetime import datetime, timedelta, timezone
from bot.config import CHECK_INTERVAL_SECONDS, REMINDER_HOURS
from bot.db import expired_users, active_users, upsert_user
from bot.services.premium import is_in_group, remove_from_group
from bot.app import app
from bot.keyboards import join_menu

async def process_memberships():
    now = datetime.now(timezone.utc)

    # Expiry
    # Expiry
    cursor = expired_users()
    async for user in cursor:
        uid = user["user_id"]
        await remove_from_group(uid)
        await upsert_user(uid, premium_status=False, joined_group=False)
        try:
            await app.send_message(uid, "🔴 Your premium membership has expired. You have been removed from the Premium Group.")
        except Exception:
            pass

    # Reminders
    # Reminders
    cursor = active_users()
    async for user in cursor:
        uid = user["user_id"]
        if user.get("premium_expiry") and user["premium_expiry"] <= now:
            continue

        inside = await is_in_group(uid)
        if inside:
            if not user.get("joined_group"):
                await upsert_user(uid, joined_group=True)
            continue

        last = user.get("last_reminder")
        if last and (now - last) < timedelta(hours=REMINDER_HOURS):
            continue

        try:
            # A fresh one-user link is generated only when a reminder is actually sent.
            from bot.services.premium import make_invite
            link = await make_invite(uid)
            await app.send_message(
                uid,
                "⏰ Reminder: your premium is active, but you have not joined the Premium Group yet.",
                reply_markup=join_menu(link)
            )
            await upsert_user(uid, last_reminder=now)
        except Exception:
            pass

async def loop():
    while True:
        try:
            await process_memberships()
        except Exception as e:
            print("Scheduler error:", e)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

async def start_scheduler():
    asyncio.create_task(loop())
    
