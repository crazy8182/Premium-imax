from datetime import datetime, timedelta, timezone
from bot.config import PREMIUM_GROUP_ID, INVITE_VALID_HOURS
from bot.db import upsert_user, get_user
from bot.app import app

async def activate_premium(user_id, plan, payment_id=None):
    now = datetime.now(timezone.utc)
    user = await get_user(user_id)
    old_expiry = user.get("premium_expiry") if user else None

    if old_expiry and old_expiry > now:
        expiry = old_expiry + timedelta(days=plan["days"])
    else:
        expiry = now + timedelta(days=plan["days"])

    await upsert_user(
        user_id,
        premium_status=True,
        premium_plan=plan["id"],
        premium_plan_name=plan["name"],
        premium_start=now,
        premium_expiry=expiry,
        last_reminder=None,
        joined_group=False,
        approved_payment_id=payment_id
    )
    return expiry

async def make_invite(user_id):
    expire = datetime.now(timezone.utc) + timedelta(hours=INVITE_VALID_HOURS)
    invite = await app.create_chat_invite_link(
        PREMIUM_GROUP_ID,
        name=f"Premium-{user_id}",
        expire_date=expire,
        member_limit=1
    )
    return invite.invite_link

async def is_in_group(user_id):
    try:
        member = await app.get_chat_member(PREMIUM_GROUP_ID, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False

async def remove_from_group(user_id):
    try:
        await app.ban_chat_member(PREMIUM_GROUP_ID, user_id)
        try:
            await app.unban_chat_member(PREMIUM_GROUP_ID, user_id)
        except Exception:
            pass
        return True
    except Exception:
        return False
