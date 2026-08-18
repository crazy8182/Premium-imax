from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client[DB_NAME]
users = db.users
payments = db.payments
offer_settings = db.offer_settings

async def init_db():
    await client.admin.command("ping")
    await users.create_index("user_id", unique=True)
    await users.create_index("referral_code", unique=True, sparse=True)
    await users.create_index("premium_expiry")
    await payments.create_index("payment_id", unique=True)
    await payments.create_index("status")
    await offer_settings.create_index("plan_id", unique=True)
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
