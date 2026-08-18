import logging
from pyrogram import Client, filters
from bot.config import API_ID, API_HASH, BOT_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.INFO)

app = Client(
    "premium_management_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=20
)

# Import handlers after app exists so decorators register on this Client.
from bot.handlers import start, user, admin  # noqa: E402,F401

# Catch-all logger: confirms that Telegram updates are reaching the bot.
@app.on_message(filters.all, group=99)
async def update_logger(_, message):
    try:
        user = message.from_user
        uid = user.id if user else "unknown"
        text = (message.text or message.caption or "")[:80]
        print(f"UPDATE RECEIVED | user={uid} | text={text!r}", flush=True)
    except Exception as e:
        print(f"UPDATE LOGGER ERROR: {e}", flush=True)
