from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import (
    MONGO_URI, DB_NAME,
    AUTO_FILTER_MONGO_URI, AUTO_FILTER_DB_NAME,
    SECOND_AUTO_FILTER_MONGO_URI, SECOND_AUTO_FILTER_DB_NAME,
)

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]
users = db.users
payments = db.payments
offer_settings = db.offer_settings

# IMPORTANT: Auto Filter databases can be different from the Premium IMAX database.
# Each Auto Filter bot stores premium users in the `uersz` collection as:
# {"id": <telegram_user_id>, "expiry_time": <datetime>}
auto_filter_client = (
    AsyncIOMotorClient(AUTO_FILTER_MONGO_URI, serverSelectionTimeoutMS=10000)
    if AUTO_FILTER_MONGO_URI else None
)
auto_filter_db = auto_filter_client[AUTO_FILTER_DB_NAME] if auto_filter_client else None
auto_filter_premium = auto_filter_db.uersz if auto_filter_db is not None else None

second_auto_filter_client = (
    AsyncIOMotorClient(SECOND_AUTO_FILTER_MONGO_URI, serverSelectionTimeoutMS=10000)
    if SECOND_AUTO_FILTER_MONGO_URI else None
)
second_auto_filter_db = (
    second_auto_filter_client[SECOND_AUTO_FILTER_DB_NAME]
    if second_auto_filter_client else None
)
second_auto_filter_premium = (
    second_auto_filter_db.uersz if second_auto_filter_db is not None else None
)

def _utc(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return None

async def _import_auto_filter_collection(collection, source):
    if collection is None:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    async for af_user in collection.find(
        {"id": {"$type": "number"}, "expiry_time": {"$exists": True, "$ne": None}},
        {"id": 1, "expiry_time": 1},
    ):
        uid = int(af_user["id"])
        expiry = _utc(af_user.get("expiry_time"))
        if not expiry or expiry <= now:
            # Only turn off premiums that were imported from this Auto Filter source.
            await users.update_one(
                {"user_id": uid, "premium_source": source},
                {"$set": {"premium_status": False, "premium_expiry": expiry}},
            )
            continue
        await users.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid,
                "premium_status": True,
                "premium_expiry": expiry,
                "premium_plan": "autofilter",
                "premium_plan_name": "Auto Filter Premium",
                "premium_source": source,
            }, "$setOnInsert": {
                "premium_start": now,
                "joined_group": False,
            }},
            upsert=True,
        )
        count += 1
    return count

async def sync_all_auto_filter_premium():
    """Refresh Premium IMAX from both Auto Filter `uersz` collections."""
    total = 0
    total += await _import_auto_filter_collection(auto_filter_premium, "autofilter_1")
    total += await _import_auto_filter_collection(second_auto_filter_premium, "autofilter_2")
    return total

async def init_db():
    await client.admin.command("ping")
    if second_auto_filter_client is not None:
        await second_auto_filter_client.admin.command("ping")

    # Existing shared MongoDB databases can contain old user documents
    # without a user_id field. A normal unique index treats those missing
    # values as null and fails with E11000. Keep the index unique for real
    # Telegram numeric IDs while ignoring legacy documents without user_id.
    try:
        await users.drop_index("user_id_1")
    except Exception:
        pass
    await users.create_index(
        "user_id",
        unique=True,
        partialFilterExpression={"user_id": {"$type": "number"}},
        name="user_id_1",
    )
    await users.create_index("referral_code", unique=True, sparse=True)
    await users.create_index("premium_expiry")
    await payments.create_index("payment_id", unique=True)
    await payments.create_index("status")
    await payments.create_index([("user_id", 1), ("status", 1)])
    await offer_settings.create_index("plan_id", unique=True)

    # Import existing premiums immediately on startup from both Auto Filter bots.
    imported = await sync_all_auto_filter_premium()
    print(f"Imported {imported} active Auto Filter premium users.", flush=True)

    print("MongoDB connected successfully.", flush=True)

async def get_user(uid):
    return await users.find_one({"user_id": uid})

async def upsert_user(uid, **data):
    await users.update_one({"user_id": uid}, {"$set": data, "$setOnInsert":{"user_id":uid}}, upsert=True)

async def create_payment(data):
    await payments.insert_one(data)

async def get_payment(pid):
    return await payments.find_one({"payment_id":pid})

async def update_payment(pid, **data):
    await payments.update_one({"payment_id":pid},{"$set":data})

def active_users():
    return users.find({"premium_status": True})

def expired_users():
    return users.find({"premium_status": True, "premium_expiry":{"$lte":datetime.now(timezone.utc)}})

async def find_referrer(code):
    return await users.find_one({"referral_code":code})

async def award_referral(uid):
    user = await get_user(uid)
    if not user or not user.get("referred_by") or user.get("referral_credited"):
        return None
    result = await users.update_one(
        {"user_id":uid, "referral_credited":{"$ne":True}},
        {"$set":{"referral_credited":True}}
    )
    if result.modified_count != 1:
        return None
    rid = user["referred_by"]
    await users.update_one(
        {"user_id":rid},
        {"$inc":{"successful_referrals":1,"discount_credits":1}}
    )
    return await get_user(rid)


def get_offer_settings():
    return offer_settings.find({})

async def set_offer_settings(plan_id, data):
    await offer_settings.update_one({"plan_id": plan_id}, {"$set": data}, upsert=True)

async def delete_offer_settings(plan_id):
    await offer_settings.delete_one({"plan_id": plan_id})


def all_users():
    return users.find({})


async def save_premium_invite_message(uid, invite_link, message_id, chat_id=None):
    """Remember a premium invite message so it can be deleted after the user joins."""
    entry = {
        "invite_link": invite_link,
        "message_id": int(message_id),
        "chat_id": int(chat_id or uid),
    }
    await users.update_one(
        {"user_id": int(uid)},
        {
            "$push": {
                "premium_invite_messages": {
                    "$each": [entry],
                    "$slice": -10,
                }
            }
        },
        upsert=True,
    )


async def remove_premium_invite_message(uid, invite_link=None):
    """Remove and return the stored invite-message record matching the used link."""
    user = await get_user(uid)
    entries = list(user.get("premium_invite_messages", [])) if user else []
    if not entries:
        return None

    match = None
    remaining = []
    for entry in entries:
        if invite_link and entry.get("invite_link") == invite_link and match is None:
            match = entry
        else:
            remaining.append(entry)

    # Fallback: if Telegram did not include invite_link, delete the newest stored message.
    if match is None and not invite_link:
        match = entries[-1]
        remaining = entries[:-1]

    if match is not None:
        await users.update_one(
            {"user_id": int(uid)},
            {"$set": {"premium_invite_messages": remaining}},
        )
    return match


async def sync_auto_filter_premium(uid, expiry):
    """Sync Premium IMAX premium data into both Auto Filter `uersz` collections."""
    document = {"id": int(uid), "expiry_time": expiry}

    if auto_filter_premium is not None:
        await auto_filter_premium.update_one(
            {"id": int(uid)}, {"$set": document}, upsert=True
        )

    if second_auto_filter_premium is not None:
        await second_auto_filter_premium.update_one(
            {"id": int(uid)}, {"$set": document}, upsert=True
        )
