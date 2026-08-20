import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@")

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("DB_NAME", "premium_bot")

ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID", "0"))

UPI_ID = os.getenv("UPI_ID", "")
UPI_NAME = os.getenv("UPI_NAME", "")
PAYMENT_QR_PATH = os.getenv("PAYMENT_QR_PATH", "assets/payment_qr.png")

REMINDER_HOURS = int(os.getenv("REMINDER_HOURS", "24"))
INVITE_VALID_HOURS = int(os.getenv("INVITE_VALID_HOURS", "24"))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

# Auto Filter Bot premium sync.
# IMPORTANT: both bots use the SAME MONGO_URI and DB_NAME.
# Auto Filter premium records are stored in the `uersz` collection with
# fields: id and expiry_time.
AUTO_FILTER_SYNC_ENABLED = os.getenv("AUTO_FILTER_SYNC_ENABLED", "True").strip().lower() in {
    "true", "1", "yes", "on"
}
AUTO_FILTER_COLLECTION = os.getenv("AUTO_FILTER_COLLECTION", "uersz").strip() or "uersz"

# Special offer shown automatically for 3 days after premium expiry.
EXPIRED_OFFER_DAYS = int(os.getenv("EXPIRED_OFFER_DAYS", "3"))
EXPIRED_DISCOUNT_PERCENT = int(os.getenv("EXPIRED_DISCOUNT_PERCENT", "10"))

# Offers are configured per plan.
# OFFER_TYPE: none | extra_days | discount
# OFFER_VALUE: extra days OR discount percentage.
# Keep OFFER_TYPE=none until you want to activate an offer.
def _plan_offer(index):
    offer_type = os.getenv(f"PLAN_{index}_OFFER_TYPE", "none").strip().lower()
    if offer_type not in {"none", "extra_days", "discount"}:
        offer_type = "none"
    try:
        value = int(os.getenv(f"PLAN_{index}_OFFER_VALUE", "0"))
    except ValueError:
        value = 0
    value = max(0, value)
    return {
        "type": offer_type,
        "value": value,
        "label": os.getenv(f"PLAN_{index}_OFFER_LABEL", "").strip(),
    }

PLANS = [
    {"id":"p1","name":os.getenv("PLAN_1_NAME","1 Month"),"days":int(os.getenv("PLAN_1_DAYS","30")),"price":int(os.getenv("PLAN_1_PRICE","99")),"offer":_plan_offer(1)},
    {"id":"p2","name":os.getenv("PLAN_2_NAME","3 Months"),"days":int(os.getenv("PLAN_2_DAYS","90")),"price":int(os.getenv("PLAN_2_PRICE","249")),"offer":_plan_offer(2)},
    {"id":"p3","name":os.getenv("PLAN_3_NAME","6 Months"),"days":int(os.getenv("PLAN_3_DAYS","180")),"price":int(os.getenv("PLAN_3_PRICE","449")),"offer":_plan_offer(3)},
    {"id":"p4","name":os.getenv("PLAN_4_NAME","1 Year"),"days":int(os.getenv("PLAN_4_DAYS","365")),"price":int(os.getenv("PLAN_4_PRICE","799")),"offer":_plan_offer(4)},
]
PLAN_MAP = {p["id"]: p for p in PLANS}

# Runtime offers are managed by the admin /offer command and persisted in MongoDB.
RUNTIME_OFFERS = {}

def offer_details(plan):
    """Return the effective days/price and offer metadata for a plan."""
    offer = RUNTIME_OFFERS.get(plan["id"], plan.get("offer", {}))
    expires_at = offer.get("expires_at")
    if expires_at:
        try:
            exp = expires_at
            if isinstance(exp, str):
                exp = __import__("datetime").datetime.fromisoformat(exp.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=__import__("datetime").timezone.utc)
            if exp <= __import__("datetime").datetime.now(__import__("datetime").timezone.utc):
                offer = {"type": "none", "value": 0, "label": ""}
        except Exception:
            pass
    kind = offer.get("type", "none")
    value = int(offer.get("value", 0) or 0)
    days = plan["days"]
    price = plan["price"]
    if kind == "extra_days" and value > 0:
        days += value
    elif kind == "discount" and value > 0:
        price = round(price * (100 - min(value, 100)) / 100)
    active = kind in {"extra_days", "discount"} and value > 0
    return {
        "days": days,
        "price": price,
        "active": active,
        "type": kind if active else "none",
        "value": value if active else 0,
        "label": offer.get("label", "") if active else "",
    }
