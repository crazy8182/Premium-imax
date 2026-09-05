from bot.services.formatting import bold_small_caps
import asyncio
from datetime import datetime, timedelta, timezone

from bot.config import (
    CHECK_INTERVAL_SECONDS,
    REMINDER_HOURS,
    EXPIRED_OFFER_DAYS,
    EXPIRED_DISCOUNT_PERCENT
)

from bot.db import (
    expired_users,
    active_users,
    expired_adult_users,
    active_adult_users,
    upsert_user,
    sync_auto_filter_premium
)

from bot.services.premium import is_member, remove_member


def utc_datetime(value):
    if value is None:
        return None

    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


async def process(bot):
    now = datetime.now(timezone.utc)

    # =========================
    # EXPIRED NORMAL PREMIUM
    # =========================

    async for user in expired_users():
        uid = user["user_id"]

        try:
            await remove_member(bot, uid)
        except Exception as e:
            print(f"Remove member error for {uid}: {e}", flush=True)

        offer_until = now + timedelta(days=EXPIRED_OFFER_DAYS)

        await sync_auto_filter_premium(uid, None)

        await upsert_user(
            uid,
            premium_status=False,
            joined_group=False,
            expired_offer_until=offer_until,
            expired_offer_reminders_sent=1,
            expired_offer_last_reminder=now
        )

        plan_name = user.get("premium_plan_name") or "Premium"

        try:
            from bot.keyboards import expired_offer_menu

            await bot.send_message(
                uid,
                bold_small_caps(
                    f"🔴 Your {plan_name} premium membership has expired.\n\n"
                    f"🎁 Special Offer: {EXPIRED_DISCOUNT_PERCENT}% OFF\n"
                    f"⏳ Valid only for the next {EXPIRED_OFFER_DAYS} days.\n\n"
                    "Renew now and get your premium at a special price.\n"
                    "After these 3 days, normal plan prices will apply."
                ),
                reply_markup=expired_offer_menu(),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Expired offer message error for {uid}: {e}", flush=True)


    # =========================
    # ACTIVE NORMAL PREMIUM
    # =========================

    async for user in active_users():
        uid = user["user_id"]

        premium_expiry = utc_datetime(user.get("premium_expiry"))

        if premium_expiry and premium_expiry <= now:
            continue

        try:
            inside = await is_member(bot, uid)

        except Exception as e:
            print(f"Membership check error for {uid}: {e}", flush=True)
            continue

        if inside:
            if not user.get("joined_group"):
                await upsert_user(uid, joined_group=True)

            continue

        last = utc_datetime(user.get("last_reminder"))

        if last and now - last < timedelta(hours=REMINDER_HOURS):
            continue

        try:
            from bot.keyboards import join_menue

            await bot.send_message(
                uid,
                bold_small_caps(
                    "⏰ Reminder: your premium is active, but you have not joined "
                    "the Premium Group yet.\n\n"
                    "Use the button below to join the Premium Group."
                ),
                reply_markup=join_menue(),
                parse_mode="HTML"
            )

            # IMPORTANT: Save reminder time immediately
            await upsert_user(uid, last_reminder=now)

            print(
                f"Premium reminder sent to {uid}. "
                f"Next reminder after {REMINDER_HOURS} hours.",
                flush=True
            )

        except Exception as e:
            print(f"Reminder error for {uid}: {e}", flush=True)


    # =========================
    # EXPIRED 18+ PREMIUM
    # =========================

    async for user in expired_adult_users():
        uid = user["user_id"]

        try:
            await remove_member(bot, uid, "adult")

        except Exception as e:
            print(f"18+ remove member error for {uid}: {e}", flush=True)

        await upsert_user(
            uid,
            adult_premium_status=False,
            adult_joined_group=False
        )


    # =========================
    # ACTIVE 18+ PREMIUM
    # =========================

    async for user in active_adult_users():
        uid = user["user_id"]

        expiry = utc_datetime(user.get("adult_premium_expiry"))

        if expiry and expiry <= now:
            continue

        try:
            inside = await is_member(bot, uid, "adult")

        except Exception as e:
            print(f"18+ membership check error for {uid}: {e}", flush=True)
            continue

        if inside:
            if not user.get("adult_joined_group"):
                await upsert_user(uid, adult_joined_group=True)

            continue

        last = utc_datetime(user.get("adult_last_reminder"))

        if last and now - last < timedelta(hours=REMINDER_HOURS):
            continue

        try:
            from bot.keyboards import join_menue

            await bot.send_message(
                uid,
                bold_small_caps(
                    "⏰ Reminder: your 18+ Premium is active, but you have not "
                    "joined the 18+ Premium Group yet.\n\n"
                    "Use the button below to join the 18+ Premium Group."
                ),
                reply_markup=join_menue(),
                parse_mode="HTML"
            )

            # IMPORTANT: Save reminder time
            await upsert_user(uid, adult_last_reminder=now)

            print(
                f"18+ Premium reminder sent to {uid}. "
                f"Next reminder after {REMINDER_HOURS} hours.",
                flush=True
            )

        except Exception as e:
            print(f"18+ reminder error for {uid}: {e}", flush=True)


    # =========================
    # EXPIRED OFFER REMINDERS
    # =========================

    async for user in __import__(
        "bot.db",
        fromlist=["users"]
    ).users.find({
        "premium_status": False,
        "expired_offer_until": {"$gt": now}
    }):

        uid = user["user_id"]

        until = utc_datetime(user.get("expired_offer_until"))

        if not until or until <= now:
            continue

        last = utc_datetime(
            user.get("expired_offer_last_reminder")
        )

        sent = int(
            user.get("expired_offer_reminders_sent", 0) or 0
        )

        if sent >= EXPIRED_OFFER_DAYS:
            continue

        if last and now - last < timedelta(hours=24):
            continue

        remaining = until - now

        remaining_hours = max(
            1,
            int(remaining.total_seconds() // 3600)
        )

        remaining_days = max(
            1,
            (remaining_hours + 23) // 24
        )

        try:
            from bot.keyboards import expired_offer_menu

            await bot.send_message(
                uid,
                bold_small_caps(
                    f"🔥 Don't miss your expired-user offer!\n\n"
                    f"🎁 {EXPIRED_DISCOUNT_PERCENT}% OFF Premium\n"
                    f"⏳ About {remaining_days} day(s) / "
                    f"{remaining_hours} hour(s) remaining.\n\n"
                    "After the offer expires, normal plan prices will apply."
                ),
                reply_markup=expired_offer_menu(),
                parse_mode="HTML"
            )

            await upsert_user(
                uid,
                expired_offer_last_reminder=now,
                expired_offer_reminders_sent=sent + 1
            )

        except Exception as e:
            print(
                f"Expired offer reminder error for {uid}: {e}",
                flush=True
            )


async def scheduler_loop(bot):

    while True:

        try:
            await process(bot)

        except Exception as e:
            print(f"Scheduler error: {e}", flush=True)

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
