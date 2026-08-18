from datetime import datetime, timedelta, timezone
from bot.config import PREMIUM_GROUP_ID, INVITE_VALID_HOURS

async def make_invite(bot, uid):
    expire = datetime.now(timezone.utc) + timedelta(hours=INVITE_VALID_HOURS)
    invite = await bot.create_chat_invite_link(
        chat_id=PREMIUM_GROUP_ID,
        name=f"Premium-{uid}",
        expire_date=expire,
        member_limit=1,
    )
    return invite.invite_link

async def is_member(bot, uid):
    try:
        member = await bot.get_chat_member(PREMIUM_GROUP_ID, uid)
        return member.status not in ("left","kicked")
    except Exception:
        return False

async def remove_member(bot, uid):
    try:
        await bot.ban_chat_member(PREMIUM_GROUP_ID, uid)
        await bot.unban_chat_member(PREMIUM_GROUP_ID, uid)
        return True
    except Exception as e:
        print(f"Remove user {uid} failed: {e}", flush=True)
        return False
