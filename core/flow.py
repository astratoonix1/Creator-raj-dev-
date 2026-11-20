"""Search results, movie card, verify/ads flow aur content delivery - sab yahin."""
import asyncio
import html
import time

from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core import tmdb, files as F
from core.db import db, now
from core.helpers import (temp, rand, settings, shortlink, verify_step, mark_verified,
                          fsub_block, delete_later, log_msg, readable, get_size, valid_text)

PER_PAGE = 8


async def reply_pic(message, pic, text, kb=None, quote=True):
    """Photo ke saath reply; photo fail ho to text."""
    if pic:
        try:
            return await message.reply_photo(pic, caption=text[:1024], reply_markup=kb, quote=quote)
        except Exception:
            pass
    return await message.reply_text(text, reply_markup=kb, quote=quote)


async def send_pic(client, chat_id, pic, text, kb=None):
    if pic:
        try:
            return await client.send_photo(chat_id, pic, caption=text[:1024], reply_markup=kb)
        except Exception:
            pass
    return await client.send_message(chat_id, text, reply_markup=kb)


def fsub_pic():
    import random
    return random.choice(C.FSUB_PICS) if C.FSUB_PICS else None


def gid_of(x):
    """deep-link me group id abs form me aati hai ('0' = koi group nahi)."""
    return -int(x) if x and str(x).isdigit() and int(x) else None


def gtag(gid):
    return f"_{abs(gid)}" if gid else ""


def cache(data):
    k = rand(6)
    temp.SEARCH[k] = data
    while len(temp.SEARCH) > 600:
        temp.SEARCH.pop(next(iter(temp.SEARCH)))
    return k


# ---------------------------------------------------------------- results
async def results_markup(skey, page, group=False, gid=None):
    res = temp.SEARCH.get(skey)
    if not isinstance(res, list):
        return None
    has = await db.has_content([r["key"] for r in res])
    res = sorted(res, key=lambda r: r["key"] not in has)   # content wale upar
    pages = max(1, (len(res) + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    rows = []
    for r in res[page * PER_PAGE:(page + 1) * PER_PAGE]:
        icon = "📖" if r["key"] in has else ("📺" if r["media"] == "tv" else "🎬")
        y = f" ({r['year']})" if r["year"] else ""
        star = f" ⭐{r['rating']}" if r["rating"] else ""
        txt = f"{icon} {r['title']}{y}{star}"[:60]
        if group:
            rows.append([Btn(txt, url=f"https://t.me/{temp.U_NAME}?start=t_{r['key']}{gtag(gid)}")])
        else:
            rows.append([Btn(txt, callback_data=f"tm_{skey}_{r['key']}")])
    if pages > 1 and not group:
        nav = []
        if page > 0:
            nav.append(Btn("⬅️ Back", callback_data=f"pg_{skey}_{page - 1}"))
        nav.append(Btn(f"{page + 1}/{pages}", callback_data="noop"))
        if page < pages - 1:
            nav.append(Btn("Next ➡️", callback_data=f"pg_{skey}_{page + 1}"))
        rows.append(nav)
    rows.append([Btn("🚫 Close", callback_data="close")])
    return Markup(rows)


async def show_results(client, message, query, results, group=False, pic=None):
    skey = cache(results)
    kb = await results_markup(skey, 0, group, message.chat.id if group else None)
    text = f"🔎 <b>{html.escape(query)}</b> — {len(results)} results mile.\n📖 = padhne ka content available hai. Title choose karo 👇"
    m = await reply_pic(message, pic, text, kb) if pic else await message.reply_text(text, reply_markup=kb, quote=True)
    if group and (await settings(message.chat.id))["auto_delete"]:
        asyncio.create_task(delete_later([m], C.DELETE_TIME))
    return m


# ---------------------------------------------------------------- card
class _Safe(dict):
    def __missing__(self, k):
        return ""


def caption(d, has, template=None):
    esc = html.escape
    if template:
        try:
            data = _Safe(
                title=esc(d["title"]), year=d["year"], rating=d["rating"], votes=d["votes"],
                genres=esc(", ".join(d["genres"])), runtime=d["runtime"] or "", lang=d["lang"],
                director=esc(d["director"] or ""), cast=esc(", ".join(d["cast"])),
                overview=esc(d["overview"][:C.CARD_OVERVIEW_LEN]), tagline=esc(d["tagline"]), status=d["status"],
                trailer=d["trailer"] or "", imdb=d["imdb"] or "", seasons=d["seasons"] or "")
            return template.format_map(data)[:1020]
        except Exception:
            pass
    y = f" ({d['year']})" if d["year"] else ""
    t = f"<b>{'📺' if d['media'] == 'tv' else '🎬'} {esc(d['title'])}{y}</b>\n"
    if d["tagline"]:
        t += f"<i>{esc(d['tagline'])}</i>\n"
    t += "\n"
    if d["rating"]:
        t += f"⭐ <b>{d['rating']}/10</b> ({d['votes']} votes)\n"
    if d["genres"]:
        t += f"🎭 {esc(', '.join(d['genres']))}\n"
    meta = []
    if d["runtime"]:
        meta.append(f"⏱ {d['runtime']} min")
    if d["lang"]:
        meta.append(f"🌐 {d['lang']}")
    if d["seasons"]:
        meta.append(f"📚 {d['seasons']} seasons")
    if d["status"]:
        meta.append(d["status"])
    if meta:
        t += " | ".join(meta) + "\n"
    if d["director"]:
        t += f"🎬 {esc(d['director'])}\n"
    if d["cast"]:
        t += f"👥 {esc(', '.join(d['cast']))}\n"
    ov = d["overview"]
    if ov:
        t += f"\n📝 {esc(ov[:C.CARD_OVERVIEW_LEN] + ('…' if len(ov) > C.CARD_OVERVIEW_LEN else ''))}\n"
    t += "\n" + ("📖 <b>Padhne ka content ready hai!</b>" if has else "🔔 Content jald add hoga — Read Now dabao, hum notify rakhenge.")
    return t[:1020]


async def send_card(client, chat_id, key, back=None, gid=None):
    d = await tmdb.details(key)
    if not d:
        return await client.send_message(chat_id, "❌ Details nahi mil payi, dobara try karo.")
    has = bool(await db.get_content(key))
    await db.bump_demand(key, d["title"], has)
    await db.bump_search(d["title"].lower())
    rows = []
    r1 = []
    if d["trailer"]:
        r1.append(Btn("▶️ Watch Trailer", url=d["trailer"]))
    if d["imdb"]:
        r1.append(Btn("⭐ IMDb", url=d["imdb"]))
    if r1:
        rows.append(r1)
    rows.append([Btn("📖 Read Now", callback_data=f"rd_{key}{gtag(gid)}")])
    last = []
    if back:
        last.append(Btn("🔙 Results", callback_data=f"pg_{back}_0"))
    last.append(Btn("🚫 Close", callback_data="close"))
    rows.append(last)
    kb = Markup(rows)
    photo = d["backdrop"] if (C.LANDSCAPE_POSTER and d["backdrop"]) else (d["poster"] or d["backdrop"])
    cap = caption(d, has, (await settings(gid))["template"])
    if photo:
        try:
            return await client.send_photo(chat_id, photo, caption=cap, reply_markup=kb)
        except Exception:
            pass
    return await client.send_message(chat_id, cap, reply_markup=kb, disable_web_page_preview=True)


# ---------------------------------------------------------------- read / verify / deliver
async def read_flow(client, uid, chat_id, key, gid=None):
    retry = f"https://t.me/{temp.U_NAME}?start=rd_{key}{gtag(gid)}"
    block = await fsub_block(client, uid, retry_url=retry, gid=gid)
    if block:
        return await send_pic(client, chat_id, fsub_pic(),
                              "⚠️ <b>Pehle neeche diye channel(s) join karo, phir Try Again dabao.</b>", Markup(block))
    step = await verify_step(uid, gid)
    if not step:
        return await deliver(client, uid, key, gid)
    token = rand(8)
    await db.new_token(uid, token)
    link = await shortlink(f"https://t.me/{temp.U_NAME}?start=vf_{uid}_{token}_{step}_{key}_{abs(gid) if gid else 0}", step, gid)
    s = await settings(gid)
    rows = [[Btn("♻️ Verify Karo", url=link)]]
    tut = s["tutorial"] if step == 1 else s["tutorial2"] if step == 2 else s["tutorial3"]
    if tut:
        rows.append([Btn("❓ Verify kaise kare", url=tut)])
    rows.append([Btn("💎 Ads hatao — Premium lo", callback_data="plan")])
    await client.send_message(
        chat_id,
        f"🔐 <b>Verification zaruri hai (Step {step})</b>\n\n"
        "Neeche <b>Verify Karo</b> dabao, link complete karo — fir bot par wapas aakar content mil jayega.\n"
        f"✅ Ek verify = {valid_text(s)} free access.",
        reply_markup=Markup(rows))


async def verify_return(client, message, uid, token, step, key, gid=None):
    if message.from_user.id != uid:
        return await message.reply_text("❌ Ye link aapke liye nahi hai.")
    t = await db.get_token(uid, token)
    if not t or t["used"]:
        return await message.reply_text("❌ Link expire ya already use ho chuka hai. Dobara <b>Read Now</b> dabao.")
    age = (now() - t["t"]).total_seconds()
    if age < C.MIN_VERIFY_TIME:
        return await message.reply_text("🚫 Bypass detect hua! Poora shortlink complete karke aao.")
    if age > 3600:
        return await message.reply_text("⌛ Token expire ho gaya. Dobara <b>Read Now</b> dabao.")
    await db.use_token(uid, token)
    await mark_verified(uid, int(step))
    s = await settings(gid)
    txt = f"#Verified\n👤 {message.from_user.mention} <code>{uid}</code> step {step}" + (f"\nGroup: <code>{gid}</code>" if gid else "")
    await log_msg(client, txt)
    if s["log"] and s["log"] != C.LOG_CHANNEL:      # group ke apne log channel me bhi
        await log_msg(client, txt, s["log"])
    kb = Markup([[Btn("✅ Click here to get content ✅", url=f"https://t.me/{temp.U_NAME}?start=rd_{key}{gtag(gid)}")]])
    dlt = await send_pic(client, message.chat.id, C.VERIFY_IMG,
                         f"✅ <b>Verification complete, {message.from_user.mention}!</b>\nAb {valid_text(s)} free access.\nNeeche button dabao 👇", kb)
    asyncio.create_task(delete_later([dlt], 300))


async def deliver(client, uid, key, gid=None):
    if key[0] == "F":
        return await deliver_files(client, uid, [key[1:]], gid)
    if key[0] == "A":
        return await deliver_files(client, uid, temp.FILES.get(key[1:], []), gid)
    c = await db.get_content(key)
    if not c:
        d = await db.demand.find_one({"_id": key}) or {}
        title = d.get("title", key)
        await log_msg(client, f"📭 #NoContent demand\n🎬 <b>{html.escape(title)}</b> (<code>{key}</code>)\nAdd: reply karke <code>/addcontent {key}</code>")
        return await client.send_message(
            uid, f"📭 <b>{html.escape(title)}</b> ka content abhi available nahi hai.\nJaise hi add hoga, aap /request se bata sakte ho.")
    sent = []
    s = await settings(gid)
    cap = None
    if s["caption"]:
        try:
            cap = s["caption"].format(title=html.escape(c.get("title", "")))
        except Exception:
            cap = None
    for mid in c["items"]:
        try:
            try:
                m = await client.copy_message(uid, C.CONTENT_CHANNEL, mid, caption=cap, protect_content=s["protect"])
            except Exception:
                m = await client.copy_message(uid, C.CONTENT_CHANNEL, mid, protect_content=s["protect"])
            sent.append(m)
        except Exception as e:
            await log_msg(client, f"❌ deliver error {key} msg {mid}: {e}")
    if sent and s["auto_delete"]:
        n = await client.send_message(
            uid, f"⏳ Ye content {readable(s['delete_time'])} me auto-delete ho jayega. Abhi save/forward kar lo.")
        sent.append(n)
        asyncio.create_task(delete_later(sent, s["delete_time"]))


# ---------------------------------------------------------------- movie update notification
async def notify_update(client, key):
    """Naya content add hone par update channel me card post (ek title ek hi baar)."""
    s = await settings()
    if not (C.MOVIE_UPDATE_CHANNEL and s["movie_update"]):
        return False
    if not await db.add_update_name(key):
        return False
    d = await tmdb.details(key)
    if not d:
        return False
    rows = []
    if d["trailer"]:
        rows.append([Btn("▶️ Trailer", url=d["trailer"])])
    rows.append([Btn("📖 Read Now", url=f"https://t.me/{temp.U_NAME}?start=t_{key}")])
    cap = "🆕 <b>New Update!</b>\n\n" + caption(d, True)
    kb = Markup(rows)
    photo = d["backdrop"] if (C.LANDSCAPE_POSTER and d["backdrop"]) else (d["poster"] or d["backdrop"])
    try:
        if photo:
            await client.send_photo(C.MOVIE_UPDATE_CHANNEL, photo, caption=cap[:1020], reply_markup=kb)
        else:
            await client.send_message(C.MOVIE_UPDATE_CHANNEL, cap, reply_markup=kb)
        return True
    except Exception as e:
        await log_msg(client, f"❌ update post fail: {e}")
        return False


# ---------------------------------------------------------------- files (indexed) delivery
class _S(dict):
    def __missing__(self, k):
        return ""


async def deliver_files(client, uid, sids, gid=None):
    s = await settings(gid)
    if not sids:
        return await client.send_message(uid, "⌛ Ye list expire ho gayi, dobara search karo.")
    sent = []
    fmt = s["caption"] or C.CUSTOM_FILE_CAPTION
    for sid in sids:
        d = await F.get_by_sid(sid)
        if not d:
            continue
        try:
            cap = fmt.format_map(_S(file_name=html.escape(d["file_name"]), file_size=get_size(d["file_size"]),
                                    file_caption=d.get("caption") or "", title=html.escape(d["file_name"])))
        except Exception:
            cap = f"<b>{html.escape(d['file_name'])}</b>"
        rows = []
        if C.STREAM_MODE:
            rows.append([Btn("🚀 Download / 🖥 Watch Online", callback_data=f"stl_{sid}")])
        if C.UPDATE_CHNL_LNK:
            rows.append([Btn("📌 Join Updates Channel", url=C.UPDATE_CHNL_LNK)])
        try:
            m = await client.send_cached_media(uid, d["_id"], caption=cap[:1024], protect_content=s["protect"],
                                               reply_markup=Markup(rows) if rows else None)
            sent.append(m)
        except Exception as e:
            await log_msg(client, f"❌ file send fail {d['file_name']}: {e}")
        if len(sids) > 1:
            await asyncio.sleep(0.5)
    if sent and s["auto_delete"]:
        n = await client.send_message(
            uid, f"⏳ Ye file(s) {readable(s['delete_time'])} me auto-delete ho jayengi. Abhi save/forward kar lo.")
        sent.append(n)
        asyncio.create_task(delete_later(sent, s["delete_time"]))


# ---------------------------------------------------------------- file search results UI
def _term(c):
    return f"{c['q']} {c['f']}".strip() if c.get("f") else c["q"]


async def file_results(skey, offset=0):
    """returns (text, markup) ya None agar cache expire."""
    c = temp.SEARCH.get(skey)
    if not isinstance(c, dict) or "q" not in c:
        return None
    st = await settings(c.get("gid"))
    per = 10 if st["max_btn"] else C.MAX_B_TN
    files, nxt, total = await F.get_search_results(_term(c), max_results=per, offset=offset)
    if not files:
        return ("❌ Is filter par koi file nahi mili.", Markup([[Btn("♻️ Filter hatao", callback_data=f"fc_{skey}")],
                                                              [Btn("🚫 Close", callback_data="close")]]))
    gid, group = c.get("gid"), c.get("group")
    rows = []
    allkey = rand(6)
    temp.FILES[allkey] = [f["sid"] for f in files]
    while len(temp.FILES) > 300:
        temp.FILES.pop(next(iter(temp.FILES)))
    if group:
        rows.append([Btn("📤 Send All", url=f"https://t.me/{temp.U_NAME}?start=rd_A{allkey}{gtag(gid)}")])
    else:
        rows.append([Btn("📤 Send All", callback_data=f"rd_A{allkey}")])
    links = ""
    for n, f in enumerate(files, 1):
        label = f"[{get_size(f['file_size'])}] {f['file_name']}"[:60]
        if not st["button"]:        # link-list mode (original 'button' setting OFF)
            links += f"\n{n}. <a href=\"https://t.me/{temp.U_NAME}?start=rd_F{f['sid']}{gtag(gid)}\">[{get_size(f['file_size'])}] {html.escape(f['file_name'][:80])}</a>"
        elif group:
            rows.append([Btn(label, url=f"https://t.me/{temp.U_NAME}?start=rd_F{f['sid']}{gtag(gid)}")])
        else:
            rows.append([Btn(label, callback_data=f"rd_F{f['sid']}")])
    rows.append([Btn("🎯 Quality", callback_data=f"ft_{skey}_q"), Btn("🌐 Language", callback_data=f"ft_{skey}_l"),
                 Btn("📺 Season", callback_data=f"ft_{skey}_s")])
    pages = max(1, (total + per - 1) // per)
    cur = offset // per + 1
    nav = []
    if offset > 0:
        nav.append(Btn("⬅️ Back", callback_data=f"fp_{skey}_{max(0, offset - per)}"))
    nav.append(Btn(f"{cur}/{pages}", callback_data="noop"))
    if nxt != "":
        nav.append(Btn("Next ➡️", callback_data=f"fp_{skey}_{nxt}"))
    rows.append(nav)
    last = []
    if st["tmdb"]:
        last.append(Btn("ℹ️ Info & Trailer", callback_data=f"fi_{skey}"))
    last.append(Btn("🚫 Close", callback_data="close"))
    rows.append(last)
    ftxt = f"\n🔎 Filter: <b>{html.escape(c['f'])}</b>" if c.get("f") else ""
    text = f"📚 <b>{total}</b> file(s) mili: <b>{html.escape(c['q'])}</b>{ftxt}\n{links}\n\nFile par tap karo 👇"
    return text, Markup(rows)


async def show_files(client, message, query, group=False):
    """Files mili to results dikhata hai (True), warna False."""
    probe, _, total = await F.get_search_results(query, max_results=1)
    if not total:
        return False
    skey = cache({"q": query, "uid": message.from_user.id, "gid": message.chat.id if group else None, "group": group, "f": ""})
    text, kb = await file_results(skey, 0)
    m = await message.reply_text(text, reply_markup=kb, quote=True, disable_web_page_preview=True)
    if group and (await settings(message.chat.id))["auto_delete"]:
        asyncio.create_task(delete_later([m], C.DELETE_TIME))
    return True


# ---------------------------------------------------------------- request moderation
async def send_request(client, user, text):
    kb = Markup([
        [Btn("✅ Uploaded", callback_data=f"ra_{user.id}_u"), Btn("🆕 Not Released", callback_data=f"ra_{user.id}_n")],
        [Btn("❗ Wrong Spelling", callback_data=f"ra_{user.id}_w"), Btn("♻️ Already Available", callback_data=f"ra_{user.id}_a")],
        [Btn("🚫 Unavailable", callback_data=f"ra_{user.id}_x"), Btn("🇮🇳 Not in Hindi", callback_data=f"ra_{user.id}_h")],
    ])
    await client.send_message(C.REQST_CHANNEL, f"📩 #Request\n👤 {user.mention} <code>{user.id}</code>\n🎬 {html.escape(text)}", reply_markup=kb)
