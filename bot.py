import asyncio
import logging
import time

from aiohttp import web
from pyrogram import Client, idle

import config as C
from core.db import db
from core.helpers import temp, log_msg
from plugins.premium import expiry_loop
from plugins.tools import set_menu
from core import files as F
import stream
from stream.clients import initialize_clients
from stream.route import routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("logs.txt")])
logging.getLogger("pyrogram").setLevel(logging.ERROR)

app = Client(C.SESSION, api_id=C.API_ID, api_hash=C.API_HASH, bot_token=C.BOT_TOKEN,
             plugins={"root": "plugins"}, workers=16, sleep_threshold=30, in_memory=True)


async def web_server():
    """Stream/download routes (/watch/<id>, /<id>) + health check."""
    a = web.Application(client_max_size=30000000)
    a.add_routes(routes)
    runner = web.AppRunner(a)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", C.PORT).start()


async def keep_alive():
    import aiohttp
    while C.URL:
        await asyncio.sleep(280)
        try:
            async with aiohttp.ClientSession() as s:
                await s.get(C.URL, timeout=aiohttp.ClientTimeout(total=10))
        except Exception:
            pass


async def main():
    if not (C.API_ID and C.API_HASH and C.BOT_TOKEN and C.DATABASE_URI and C.TMDB_API_KEY):
        raise SystemExit("API_ID, API_HASH, BOT_TOKEN, DATABASE_URI, TMDB_API_KEY zaruri hain (README dekho).")
    await app.start()
    me = await app.get_me()
    temp.ME, temp.U_NAME, temp.BOT_START = me.id, me.username, time.time()
    stream.holder.client = app
    await initialize_clients(app)
    await F.ensure_indexes()
    u, c = await db.banned()
    temp.BANNED_USERS, temp.BANNED_CHATS = set(u), set(c)
    await web_server()
    try:
        await set_menu(app)
    except Exception:
        pass
    asyncio.create_task(expiry_loop(app))
    asyncio.create_task(keep_alive())
    await log_msg(app, f"✅ <b>@{me.username}</b> started.")
    logging.info("Bot started as @%s", me.username)
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
