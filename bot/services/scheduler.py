import asyncio
from datetime import datetime, timedelta, timezone

from bot.config import CHECK_INTERVAL_SECONDS, REMINDER_HOURS
from bot.db import expired_users, active_users, upsert_user
from bot.services.premium import is_member, remove_member, make_invite


def utc_datetime(value):
    """
    MongoDB datetime ko timezone-aware UTC datetime mein convert karta hai.
    Naive datetime ko UTC maana jayega.
    """
    if value is None:
        return None

    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


async def process(bot):
    now = datetime.now(timezone.utc)

    # ==========================================
    # EXPIRED PREMIUM USERS
    # ==========================================
    async for user in expired_users():
        uid = user["user_id"]

        try:
            await remove_member(bot, uid)
        except Exception as e:
            print(
                f"Remove member error for {uid}: {e}",
                flush=True
            )

        await upsert_user(
            uid,
            premium_status=False,
            joined_group=False
        )

        try:
            await bot.send_message(
                uid,
                "🔴 Your premium membership has expired "
                "and you have been removed from the Premium Group."
            )
        except Exception:
            pass

    # ==========================================
    # ACTIVE PREMIUM USERS
    # ==========================================
    async for user in active_users():
        uid = user["user_id"]

        # ------------------------------------------
        # Premium expiry datetime normalize
        # ------------------------------------------
        premium_expiry = utc_datetime(
            user.get("premium_expiry")
        )

        # Agar premium expiry already ho chuki hai
        if premium_expiry and premium_expiry <= now:
            continue

        # ------------------------------------------
        # Check Premium Group membership
        # ------------------------------------------
        try:
            inside = await is_member(bot, uid)
        except Exception as e:
            print(
                f"Membership check error for {uid}: {e}",
                flush=True
            )
            continue

        # ------------------------------------------
        # User already inside Premium Group
        # ------------------------------------------
        if inside:
            if not user.get("joined_group"):
                await upsert_user(
                    uid,
                    joined_group=True
                )

            continue

        # ------------------------------------------
        # Last reminder datetime normalize
        # ------------------------------------------
        last = utc_datetime(
            user.get("last_reminder")
        )

        # Reminder already sent recently
        if last and (
            now - last
            < timedelta(hours=REMINDER_HOURS)
        ):
            continue

        # ------------------------------------------
        # Send Premium Group reminder
        # ------------------------------------------
        try:
            link = await make_invite(
                bot,
                uid
            )

            from bot.keyboards import join_menu

            await bot.send_message(
                uid,
                "⏰ Reminder: your premium is active, "
                "but you have not joined the Premium Group yet.",
                reply_markup=join_menu(link)
            )

            # Save reminder time as UTC-aware datetime
            await upsert_user(
                uid,
                last_reminder=now
            )

        except Exception as e:
            print(
                f"Reminder error for {uid}: {e}",
                flush=True
            )


# ==============================================
# SCHEDULER LOOP
# ==============================================
async def scheduler_loop(bot):
    while True:

        try:
            await process(bot)

        except Exception as e:
            print(
                f"Scheduler error: {e}",
                flush=True
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )
