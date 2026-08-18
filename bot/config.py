import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("DB_NAME", "premium_bot")

ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID", "0"))

UPI_ID = os.getenv("UPI_ID", "")
UPI_NAME = os.getenv("UPI_NAME", "")
PAYMENT_QR_PATH = os.getenv("PAYMENT_QR_PATH", "assets/payment_qr.png")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

CURRENCY = os.getenv("CURRENCY", "INR")
REMINDER_HOURS = int(os.getenv("REMINDER_HOURS", "24"))
INVITE_VALID_HOURS = int(os.getenv("INVITE_VALID_HOURS", "24"))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

PLANS = [
    {"id": "p1", "name": os.getenv("PLAN_1_NAME", "1 Month"), "days": int(os.getenv("PLAN_1_DAYS", "30")), "price": int(os.getenv("PLAN_1_PRICE", "99"))},
    {"id": "p2", "name": os.getenv("PLAN_2_NAME", "3 Months"), "days": int(os.getenv("PLAN_2_DAYS", "90")), "price": int(os.getenv("PLAN_2_PRICE", "249"))},
    {"id": "p3", "name": os.getenv("PLAN_3_NAME", "6 Months"), "days": int(os.getenv("PLAN_3_DAYS", "180")), "price": int(os.getenv("PLAN_3_PRICE", "449"))},
    {"id": "p4", "name": os.getenv("PLAN_4_NAME", "1 Year"), "days": int(os.getenv("PLAN_4_DAYS", "365")), "price": int(os.getenv("PLAN_4_PRICE", "799"))},
]

PLAN_MAP = {p["id"]: p for p in PLANS}
