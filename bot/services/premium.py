from datetime import datetime, timedelta, timezone
from bot.config import PREMIUM_GROUP_ID, ADULT_PREMIUM_GROUP_ID, INVITE_VALID_HOURS

def group_id(category="movie"):
    return ADULT_PREMIUM_GROUP_ID if category == "adult" else PREMIUM_GROUP_ID

async def make_invite(bot, uid, category="movie"):
    expire = datetime.now(timezone.utc) + timedelta(hours=INVITE_VALID_HOURS)
    invite = await bot.create_chat_invite_link(
        chat_id=group_id(category),
        name=f"Premium-{uid}",
        expire_date=expire,
        member_limit=1,
    )
    return invite.invite_link

async def is_member(bot, uid, category="movie"):
    try:
        member = await bot.get_chat_member(group_id(category), uid)
        return member.status not in ("left","kicked")
    except Exception:
        return False

async def remove_member(bot, uid, category="movie"):
    try:
        await bot.ban_chat_member(group_id(category), uid)
        await bot.unban_chat_member(group_id(category), uid)
        return True
    except Exception as e:
        print(f"Remove user {uid} failed: {e}", flush=True)
        return False
