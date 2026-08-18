from datetime import datetime, timezone
from bot.config import PLAN_MAP, RUNTIME_OFFERS
from bot.db import get_offer_settings, set_offer_settings, delete_offer_settings

async def init_offers():
    RUNTIME_OFFERS.clear()
    async for doc in get_offer_settings():
        pid = doc.get("plan_id")
        if pid in PLAN_MAP:
            RUNTIME_OFFERS[pid] = {
                "type": doc.get("type", "none"),
                "value": int(doc.get("value", 0) or 0),
                "label": doc.get("label", "") or "",
                "expires_at": doc.get("expires_at"),
            }

async def save_offer(plan_id, offer_type, value, label="", expires_at=None):
    data = {
        "plan_id": plan_id,
        "type": offer_type,
        "value": int(value),
        "label": label or "",
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc),
    }
    await set_offer_settings(plan_id, data)
    RUNTIME_OFFERS[plan_id] = data

async def clear_offer(plan_id):
    await delete_offer_settings(plan_id)
    RUNTIME_OFFERS.pop(plan_id, None)

async def active_offer(plan):
    from bot.config import offer_details
    return offer_details(plan)
