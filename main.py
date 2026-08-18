import asyncio
import logging
import os
from aiohttp import web
from telegram.ext import Application
from bot.config import BOT_TOKEN
from bot.db import init_db
from bot.bot import register_handlers
from bot.services.scheduler import scheduler_loop

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def health(request):
    return web.Response(text="OK")

async def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health server listening on 0.0.0.0:{port}", flush=True)
    return runner

async def main():
    await init_db()

    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    register_handlers(application)

    await application.initialize()
    await application.start()

    me = await application.bot.get_me()
    print(f"Premium Management Bot started | @{me.username} | id={me.id}", flush=True)

    await application.updater.start_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=False,
    )
    print("Telegram polling started successfully.", flush=True)

    health_runner = await start_health_server()
    scheduler_task = asyncio.create_task(scheduler_loop(application.bot))

    try:
        await asyncio.Event().wait()
    finally:
        scheduler_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await health_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
