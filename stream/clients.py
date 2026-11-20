"""Extra bots (MULTI_TOKEN1, MULTI_TOKEN2 ...) = stream speed/load balance. Original ka port."""
import asyncio
import logging

from pyrogram import Client

from config import API_ID, API_HASH, SLEEP_THRESHOLD
from stream import multi_clients, work_loads
from stream.config_parser import TokenParser


async def initialize_clients(main_client):
    multi_clients[0] = main_client
    work_loads[0] = 0
    tokens = TokenParser().parse_from_env()
    if not tokens:
        logging.info("No additional stream clients, main bot use hoga")
        return

    async def start_client(cid, token):
        try:
            c = await Client(name=f"stream{cid}", api_id=API_ID, api_hash=API_HASH, bot_token=token,
                             sleep_threshold=SLEEP_THRESHOLD, no_updates=True, in_memory=True).start()
            work_loads[cid] = 0
            return cid, c
        except Exception:
            logging.error(f"Failed starting stream client {cid}", exc_info=True)

    res = await asyncio.gather(*[start_client(i, t) for i, t in tokens.items()])
    multi_clients.update(dict(r for r in res if r))
    if len(multi_clients) > 1:
        logging.info("Multi-client stream mode ON")
