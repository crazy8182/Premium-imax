"""Auto Filter premium synchronization using the SAME MongoDB database as Premium Handler.

Auto Filter premium documents live in the ``uersz`` collection and use:
    {"id": <telegram_user_id>, "expiry_time": <UTC-naive datetime>}

No second MongoDB connection is used. Both bots must point to the same
MongoDB database via MONGO_URI + DB_NAME.
"""
from datetime import datetime, timezone
import logging

from bot.db import db
from bot.config import AUTO_FILTER_SYNC_ENABLED, AUTO_FILTER_COLLECTION

logger = logging.getLogger(__name__)
_collection = db[AUTO_FILTER_COLLECTION]


def _auto_filter_expiry(expiry):
    """Convert aware/naive datetime to Auto Filter's UTC-naive datetime."""
    if expiry is None:
        return None
    if expiry.tzinfo is None:
        return expiry
    return expiry.astimezone(timezone.utc).replace(tzinfo=None)


async def sync_premium(user_id: int, expiry) -> bool:
    """Create/update the Auto Filter premium record with the same expiry."""
    if not AUTO_FILTER_SYNC_ENABLED:
        logger.warning("Auto Filter premium sync is disabled.")
        return False
    try:
        expiry = _auto_filter_expiry(expiry)
        await _collection.update_one(
            {"id": int(user_id)},
            {"$set": {"id": int(user_id), "expiry_time": expiry}},
            upsert=True,
        )
        logger.info("Auto Filter premium synced: user=%s expiry=%s", user_id, expiry)
        return True
    except Exception as e:
        logger.exception("Auto Filter premium sync failed for user %s: %s", user_id, e)
        return False


async def remove_premium(user_id: int) -> bool:
    """Disable Auto Filter premium without deleting the user's Auto Filter record."""
    if not AUTO_FILTER_SYNC_ENABLED:
        logger.warning("Auto Filter premium sync is disabled.")
        return False
    try:
        result = await _collection.update_one(
            {"id": int(user_id)},
            {"$set": {"expiry_time": None}},
        )
        logger.info("Auto Filter premium removed: user=%s matched=%s", user_id, result.matched_count)
        return result.matched_count > 0
    except Exception as e:
        logger.exception("Auto Filter premium removal failed for user %s: %s", user_id, e)
        return False
