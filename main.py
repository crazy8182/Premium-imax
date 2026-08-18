import asyncio
import os
from aiohttp import web

from bot.app import app
from bot.services.scheduler import start_scheduler


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

    print(f"Health server running on port {port}")


async def main():
    await app.start()
    print("Premium Management Bot started.")

    await start_scheduler()
    await start_web_server()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
