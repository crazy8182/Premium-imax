import asyncio
from bot.app import app
from bot.services.scheduler import start_scheduler

async def main():
    await app.start()
    await start_scheduler()
    print("Premium Management Bot started.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
