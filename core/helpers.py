import asyncio
import datetime as dt
import logging
import random
import re
import string

import pytz
from pyrogram import enums
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, FloodWait
from pyrogram.types import InlineKeyboardButton as Btn
from shortzy import Shortzy

import config as C
from core.db import db, now

log = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


class temp:
    BANNED_USERS = set()
    BANNED_CHATS = set()
    U_NAME = ""
    ME = 0
    SEARCH = {}      # short_key -> results list
    PENDING = {}     # admin content add: key -> content-channel msg_id
    BOT_START = 0


def rand(n=6):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def seconds(s: str) -> int:
    m = re.match(r"^(\d+)\s*(s|min|hour|day|month|year)$", s.strip().lower())
    if not m:
        return 0
    v, u = int(m.group(1)), m.group(2)
    return v * {"s": 1, "min": 60, "hour": 3600, "day": 86400, "month": 2592000, "year": 31536000}[u]


def readable(sec):
    sec = int(sec)
    out = []
    for n, d in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if sec >= d:
            v, sec = divmod(sec, d)
            out.append(f"{v}{n}")
    return " ".join(out) or "0s"


def ist(d, fmt="%d-%m-%Y %I:%M %p"):
    return pytz.utc.localize(d).astimezone(IST).strftime(fmt)


def clean_query(text):
    t = re.sub(r"[^\w\s:'\-&.]", " ", text, flags=re.U)
    t = re.sub(r"\b(360p|480p|720p|1080p|2160p|4k|hindi|dubbed|full|movie|download|hd|web ?series|trailer)\b", " ", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


async def settings(gid=None):
    """Global (DB > env) settings; gid ho to us group ke apne settings upar se lagte hain."""
    s = await db.get_settings()
    g = lambda k, d: s.get(k, d)
    out = {
        "is_verify": g("is_verify", C.IS_VERIFY),
        "api": g("api", C.SHORTENER_API), "site": g("site", C.SHORTENER_WEBSITE),
        "api2": g("api2", C.SHORTENER_API2), "site2": g("site2", C.SHORTENER_WEBSITE2),
        "api3": g("api3", C.SHORTENER_API3), "site3": g("site3", C.SHORTENER_WEBSITE3),
        "gap2": g("gap2", C.TWO_VERIFY_GAP), "gap3": g("gap3", C.THREE_VERIFY_GAP),
        "valid": g("valid", C.VERIFY_VALID),
        "tutorial": g("tutorial", C.TUTORIAL),
        "tutorial2": g("tutorial2", C.TUTORIAL_2 or C.TUTORIAL),
        "tutorial3": g("tutorial3", C.TUTORIAL_3 or C.TUTORIAL),
        "pm_search": g("pm_search", C.PM_SEARCH),
        "group_search": g("group_search", C.GROUP_SEARCH),
        "auto_delete": g("auto_delete", C.AUTO_DELETE),
        "delete_time": g("delete_time", C.DELETE_TIME),
        "protect": g("protect", C.PROTECT_CONTENT),
        "welcome": g("welcome", C.MELCOW_NEW_USERS),
        "template": g("template", C.CARD_TEMPLATE),
        "caption": g("caption", C.CONTENT_CAPTION),
        "log": g("log", C.LOG_CHANNEL),
        "fsub": g("fsub", None),
        "movie_update": g("movie_update", C.MOVIE_UPDATE_NOTIFICATION),
    }
    if gid:
        out.update({k: v for k, v in (await db.get_group_settings(gid)).items() if v is not None})
    return out


# ---------------- shortener ----------------
async def shortlink(url, step=1, gid=None):
    s = await settings(gid)
    api, site = {1: (s["api"], s["site"]), 2: (s["api2"], s["site2"]), 3: (s["api3"], s["site3"])}[step]
    if not api or not site:
        return url
    z = Shortzy(api, site)
    try:
        return await z.convert(url)
    except Exception:
        try:
            return await z.get_quick_link(url)
        except Exception:
            return url


async def verify_step(uid, gid=None):
    """0 = verify ki zarurat nahi, 1/2/3 = us shortener se verify karao."""
    s = await settings(gid)
    if not s["is_verify"] or not s["api"] or await db.is_premium(uid):
        return 0
    u = await db.get_user(uid)
    t = now()
    v1, v2, v3 = u.get("v1"), u.get("v2"), u.get("v3")
    if not v1 or (t - v1).total_seconds() > s["valid"]:
        return 1
    if s["api2"] and (t - v1).total_seconds() > s["gap2"] and (not v2 or v2 < v1):
        return 2
    if s["api3"] and v2 and v2 >= v1 and (t - v2).total_seconds() > s["gap3"] and (not v3 or v3 < v2):
        return 3
    return 0


async def mark_verified(uid, step):
    kw = {f"v{step}": now()}
    if step == 1:
        kw.update(v2=None, v3=None)
    await db.set_user(uid, **kw)


# ---------------- force subscribe ----------------
async def fsub_buttons(bot, uid, auth_channels=None):
    btn = []
    for ch in C.AUTH_REQ_CHANNELS:
        if await db.has_joined(uid, ch):
            continue
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status not in (enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT):
                await db.add_join_req(uid, ch)
                continue
        except UserNotParticipant:
            pass
        except Exception as e:
            log.warning(f"fsub-req check {ch}: {e}")
        try:
            chat = await bot.get_chat(ch)
            inv = await bot.create_chat_invite_link(ch, creates_join_request=True)
            btn.append([Btn(f"⛔️ Join {chat.title}", url=inv.invite_link)])
        except Exception as e:
            log.warning(f"fsub-req link {ch}: {e}")
    for ch in (auth_channels if auth_channels else C.AUTH_CHANNELS):
        try:
            await bot.get_chat_member(ch, uid)
        except UserNotParticipant:
            try:
                chat = await bot.get_chat(ch)
                inv = await bot.create_chat_invite_link(ch)
                btn.append([Btn(f"📢 Join {chat.title}", url=inv.invite_link)])
            except Exception as e:
                log.warning(f"fsub link {ch}: {e}")
        except Exception as e:
            log.warning(f"fsub check {ch}: {e}")
    return btn


async def fsub_block(bot, uid, retry_url=None, retry_cb=None, gid=None):
    """Agar join baaki hai to buttons wali list return karta hai, warna None."""
    if uid in C.ADMINS:
        return None
    btn = await fsub_buttons(bot, uid, (await settings(gid))["fsub"] if gid else None)
    if not btn:
        return None
    if retry_url:
        btn.append([Btn("🔄 Try Again", url=retry_url)])
    elif retry_cb:
        btn.append([Btn("🔄 Try Again", callback_data=retry_cb)])
    return btn


# ---------------- misc ----------------
async def delete_later(msgs, delay):
    await asyncio.sleep(delay)
    for m in msgs:
        try:
            await m.delete()
        except Exception:
            pass


async def safe_send(bot, chat_id, *a, **k):
    try:
        return await bot.send_message(chat_id, *a, **k)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await bot.send_message(chat_id, *a, **k)
    except Exception:
        return None


async def is_admin(bot, chat_id, uid):
    try:
        m = await bot.get_chat_member(chat_id, uid)
        return m.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except Exception:
        return False


async def log_msg(bot, text, chat=None):
    try:
        if C.LOG_CHANNEL:
            await bot.send_message(chat or C.LOG_CHANNEL, text, disable_web_page_preview=True)
    except Exception as e:
        log.warning(f"log_msg: {e}")
