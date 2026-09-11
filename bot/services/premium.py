from datetime import datetime, timedelta, timezone

from bot.config import PREMIUM_GROUP_ID, ADULT_PREMIUM_GROUP_ID, INVITE_VALID_HOURS
from bot.db import premium_invites


def group_id(category="movie"):
    return ADULT_PREMIUM_GROUP_ID if category == "adult" else PREMIUM_GROUP_ID


def category_label(category):
    return "18+ Premium" if category == "adult" else "Movie Premium"


async def make_invite(bot, uid, category="movie"):
    """Create a one-user invite and keep a DB record so admins can revoke it later."""
    uid = int(uid)
    chat_id = group_id(category)
    if not chat_id:
        raise ValueError(f"{category_label(category)} group ID is not configured")

    expire = datetime.now(timezone.utc) + timedelta(hours=INVITE_VALID_HOURS)

    invite = await bot.create_chat_invite_link(
        chat_id=chat_id,
        name=f"Premium-{uid}-{category}",
        expire_date=expire,
        member_limit=1,
    )

    link = invite.invite_link
    await premium_invites.update_one(
        {"invite_link": link},
        {"$set": {
            "invite_link": link,
            "user_id": uid,
            "category": category,
            "chat_id": chat_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expire,
            "revoked": False,
        }},
        upsert=True,
    )
    return link


async def revoke_invite(bot, invite_link):
    """Revoke one bot-created invite link."""
    record = await premium_invites.find_one({"invite_link": invite_link})
    if not record:
        return False, "Link not found in bot database."

    try:
        await bot.revoke_chat_invite_link(record["chat_id"], invite_link)
    except Exception as e:
        # Telegram returns an error if it was already revoked/expired.
        msg = str(e).lower()
        if "not found" not in msg and "invite" not in msg and "revoked" not in msg:
            return False, str(e)

    await premium_invites.update_one(
        {"invite_link": invite_link},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}},
    )
    return True, "revoked"


async def revoke_user_invites(bot, uid, category=None):
    """Revoke all currently stored links belonging to one premium user."""
    query = {"user_id": int(uid), "revoked": {"$ne": True}}
    if category in {"movie", "adult"}:
        query["category"] = category

    count = 0
    async for record in premium_invites.find(query):
        ok, _ = await revoke_invite(bot, record["invite_link"])
        if ok:
            count += 1
    return count


async def revoke_all_invites(bot, category):
    """Revoke every bot-created invite for the selected premium group."""
    if category not in {"movie", "adult"}:
        raise ValueError("Category must be movie or adult")

    count = 0
    query = {"category": category, "revoked": {"$ne": True}}
    async for record in premium_invites.find(query):
        ok, _ = await revoke_invite(bot, record["invite_link"])
        if ok:
            count += 1
    return count


async def is_member(bot, uid, category="movie"):
    """Check whether a user is currently a member of the correct premium group."""
    chat_id = group_id(category)

    if not chat_id:
        print(f"Membership check failed for {uid}: group ID is not configured", flush=True)
        return False

    try:
        member = await bot.get_chat_member(chat_id, uid)
        status = str(member.status).lower()

        print(
            f"Membership check | user={uid} | category={category} | "
            f"group={chat_id} | status={status}",
            flush=True,
        )

        return status not in {"left", "kicked", "banned"}

    except Exception as e:
        print(
            f"Membership check ERROR | user={uid} | category={category} | "
            f"group={chat_id} | {type(e).__name__}: {e}",
            flush=True,
        )
        return False


async def remove_member(bot, uid, category="movie"):
    try:
        await bot.ban_chat_member(group_id(category), uid)
        await bot.unban_chat_member(group_id(category), uid)
        return True
    except Exception as e:
        print(f"Remove user {uid} failed: {e}", flush=True)
        return False
