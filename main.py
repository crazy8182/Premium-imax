import asyncio
import os
import aiohttp
from aiohttp import web

from bot.app import app
from bot.services.scheduler import start_scheduler
from bot.db import init_db
from bot.config import BOT_TOKEN


async def delete_webhook():
    """Remove any old Bot API webhook so polling can receive updates."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"drop_pending_updates": "false"}, timeout=20) as resp:
                data = await resp.json()
                print(f"Telegram webhook cleanup: {data}", flush=True)
    except Exception as e:
        print(f"Webhook cleanup warning: {e}", flush=True)


async def health(request):
    return web.Response(text="OK")


async def start_web_server():
    port = int(os.getenv("PORT", "8080"))
    web_app = web.Application()
    web_app.router.add_get("/", health)
    web_app.router.add_get("/health", health)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health server running on 0.0.0.0:{port}", flush=True)


async def main():
    # Database indexes are created before Telegram starts.
    await init_db()

    # Important for bots that were previously run with a webhook.
    await delete_webhook()

    await app.start()

    me = await app.get_me()
    print(
        f"Premium Management Bot started | @{me.username} | id={me.id}",
        flush=True
    )

    await start_scheduler()
    await start_web_server()

    # Keep the worker alive.
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
