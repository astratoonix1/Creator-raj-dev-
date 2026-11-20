"""Stream/download web server (original DreamXBotz ka port). Files BIN_CHANNEL se stream hoti hain."""
import time

multi_clients = {}   # {0: main_client, 1: extra bot, ...}
work_loads = {}
StartTime = time.time()


class _Holder:
    client = None    # bot.py start par main client yahan set hota hai


holder = _Holder()
