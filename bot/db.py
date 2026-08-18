from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
users = db.users
payments = db.payments

async def init_db():
    await users.create_index("user_id", unique=True)
    await users.create_index("premium_expiry")
    await users.create_index("referral_code", unique=True, sparse=True)
    await payments.create_index("payment_id", unique=True)
    await payments.create_index("status")
    await payments.create_index("user_id")

async def get_user(user_id):
    return await users.find_one({"user_id": user_id})

async def upsert_user(user_id, **data):
    await users.update_one(
        {"user_id": user_id},
        {"$set": data, "$setOnInsert": {"user_id": user_id}},
        upsert=True
    )

async def create_payment(data):
    await payments.insert_one(data)

async def get_payment(payment_id):
    return await payments.find_one({"payment_id": payment_id})

async def update_payment(payment_id, **data):
    await payments.update_one({"payment_id": payment_id}, {"$set": data})

def active_users():
    return users.find({"premium_status": True})

def expired_users():
    from datetime import datetime, timezone
    return users.find({
        "premium_status": True,
        "premium_expiry": {"$lte": datetime.now(timezone.utc)}
    })

async def find_by_referral_code(code):
    return await users.find_one({"referral_code": code})

async def award_referral_discount(referred_user_id):
    """
    Gives the referrer one 5% discount credit only once for this referred user.
    Returns the referrer user document if a new credit was awarded, otherwise None.
    """
    user = await get_user(referred_user_id)
    if not user:
        return None
    referrer_id = user.get("referred_by")
    if not referrer_id or user.get("referral_credited"):
        return None

    result = await users.update_one(
        {"user_id": referred_user_id, "referred_by": referrer_id, "referral_credited": {"$ne": True}},
        {"$set": {"referral_credited": True}}
    )
    if result.modified_count != 1:
        return None

    await users.update_one(
        {"user_id": referrer_id},
        {
            "$inc": {
                "successful_referrals": 1,
                "discount_credits": 1
            }
        },
        upsert=True
    )
    return await get_user(referrer_id)
