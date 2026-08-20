from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]
users = db.users
payments = db.payments
offer_settings = db.offer_settings

# Same premium collection used by the Auto Filter Bot.
# IMPORTANT: This bot only writes to it; the Auto Filter Bot code is unchanged.
auto_filter_premium = db.uersz

async def init_db():
    await client.admin.command("ping")

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

    # Import existing Premium users from the Auto Filter Bot.
    # The Auto Filter Bot already stores premium users in the shared `uersz`
    # collection as: {id: user_id, expiry_time: datetime}.  This is a
    # one-way compatibility import so old Auto Filter premium memberships
    # also appear in Premium IMAX without changing the Auto Filter Bot.
    now = datetime.now(timezone.utc)
    async for af_user in auto_filter_premium.find({
        "id": {"$type": "number"},
        "expiry_time": {"$exists": True, "$ne": None, "$gt": now},
    }, {"id": 1, "expiry_time": 1}):
        uid = int(af_user["id"])
        expiry = af_user["expiry_time"]
        if isinstance(expiry, datetime) and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        await users.update_one(
            {"user_id": uid},
            {
                "$set": {
                    "user_id": uid,
                    "premium_status": True,
                    "premium_expiry": expiry,
                    "premium_plan": "autofilter",
                    "premium_plan_name": "Auto Filter Premium",
                },
                "$setOnInsert": {
                    "premium_start": now,
                    "joined_group": False,
                },
            },
            upsert=True,
        )

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


async def sync_auto_filter_premium(uid, expiry):
    """Sync Premium IMAX premium data into the Auto Filter Bot's existing uersz collection.

    The Auto Filter Bot expects exactly these fields for premium access:
      {"id": user_id, "expiry_time": datetime}
    """
    await auto_filter_premium.update_one(
        {"id": int(uid)},
        {"$set": {"id": int(uid), "expiry_time": expiry}},
        upsert=True,
    )
