from pyrogram import Client
from bot.config import API_ID, API_HASH, BOT_TOKEN
from bot.db import init_db

app = Client(
    "premium_management_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=20
)

# Import handlers after app exists
from bot.handlers import start, user, admin  # noqa: E402

# Initialize indexes once the app starts.
_original_start = app.start
async def _start():
    await init_db()
    return await _original_start()
app.start = _start
