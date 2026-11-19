"""Search results, movie card, verify/ads flow aur content delivery - sab yahin."""
import asyncio
import html
import time

from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core import tmdb
from core.db import db, now
from core.helpers import (temp, rand, settings, shortlink, verify_step, mark_verified,
                          fsub_block, delete_later, log_msg, readable)

PER_PAGE = 8


def cache(data):
    k = rand(6)
    temp.SEARCH[k] = data
    while len(temp.SEARCH) > 600:
        temp.SEARCH.pop(next(iter(temp.SEARCH)))
    return k


# ---------------------------------------------------------------- results
async def results_markup(skey, page, group=False):
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
            rows.append([Btn(txt, url=f"https://t.me/{temp.U_NAME}?start=t_{r['key']}")])
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


async def show_results(client, message, query, results, group=False):
    skey = cache(results)
    kb = await results_markup(skey, 0, group)
    text = f"🔎 <b>{html.escape(query)}</b> — {len(results)} results mile.\n📖 = padhne ka content available hai. Title choose karo 👇"
    m = await message.reply_text(text, reply_markup=kb, quote=True)
    if group and (await settings())["auto_delete"]:
        asyncio.create_task(delete_later([m], C.DELETE_TIME))
    return m


# ---------------------------------------------------------------- card
def caption(d, has):
    esc = html.escape
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
        t += f"\n📝 {esc(ov[:330] + ('…' if len(ov) > 330 else ''))}\n"
    t += "\n" + ("📖 <b>Padhne ka content ready hai!</b>" if has else "🔔 Content jald add hoga — Read Now dabao, hum notify rakhenge.")
    return t[:1020]


async def send_card(client, chat_id, key, back=None):
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
    rows.append([Btn("📖 Read Now", callback_data=f"rd_{key}")])
    last = []
    if back:
        last.append(Btn("🔙 Results", callback_data=f"pg_{back}_0"))
    last.append(Btn("🚫 Close", callback_data="close"))
    rows.append(last)
    kb = Markup(rows)
    photo = d["backdrop"] if (C.LANDSCAPE_POSTER and d["backdrop"]) else (d["poster"] or d["backdrop"])
    cap = caption(d, has)
    if photo:
        try:
            return await client.send_photo(chat_id, photo, caption=cap, reply_markup=kb)
        except Exception:
            pass
    return await client.send_message(chat_id, cap, reply_markup=kb, disable_web_page_preview=True)


# ---------------------------------------------------------------- read / verify / deliver
async def read_flow(client, uid, chat_id, key):
    retry = f"https://t.me/{temp.U_NAME}?start=rd_{key}"
    block = await fsub_block(client, uid, retry_url=retry)
    if block:
        return await client.send_message(
            chat_id, "⚠️ <b>Pehle neeche diye channel(s) join karo, phir Try Again dabao.</b>",
            reply_markup=Markup(block))
    step = await verify_step(uid)
    if not step:
        return await deliver(client, uid, key)
    token = rand(8)
    await db.new_token(uid, token)
    link = await shortlink(f"https://t.me/{temp.U_NAME}?start=vf_{uid}_{token}_{step}_{key}", step)
    s = await settings()
    rows = [[Btn("♻️ Verify Karo", url=link)]]
    if s["tutorial"]:
        rows.append([Btn("❓ Verify kaise kare", url=s["tutorial"])])
    rows.append([Btn("💎 Ads hatao — Premium lo", callback_data="plan")])
    await client.send_message(
        chat_id,
        f"🔐 <b>Verification zaruri hai (Step {step})</b>\n\n"
        "Neeche <b>Verify Karo</b> dabao, link complete karo — fir bot par wapas aakar content mil jayega.\n"
        f"✅ Ek verify = {readable(s['valid'])} tak free access.",
        reply_markup=Markup(rows))


async def verify_return(client, message, uid, token, step, key):
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
    s = await settings()
    await message.reply_text(f"✅ <b>Verified!</b> Ab {readable(s['valid'])} tak free access.")
    await log_msg(client, f"#Verified\n👤 {message.from_user.mention} <code>{uid}</code> step {step}")
    nxt = await verify_step(uid)
    if nxt:    # chain: agle step ke liye turant dubara
        return await read_flow(client, uid, message.chat.id, key)
    await deliver(client, uid, key)


async def deliver(client, uid, key):
    c = await db.get_content(key)
    if not c:
        d = await db.demand.find_one({"_id": key}) or {}
        title = d.get("title", key)
        await log_msg(client, f"📭 #NoContent demand\n🎬 <b>{html.escape(title)}</b> (<code>{key}</code>)\nAdd: reply karke <code>/addcontent {key}</code>")
        return await client.send_message(
            uid, f"📭 <b>{html.escape(title)}</b> ka content abhi available nahi hai.\nJaise hi add hoga, aap /request se bata sakte ho.")
    sent = []
    for mid in c["items"]:
        try:
            sent.append(await client.copy_message(uid, C.CONTENT_CHANNEL, mid, protect_content=C.PROTECT_CONTENT))
        except Exception as e:
            await log_msg(client, f"❌ deliver error {key} msg {mid}: {e}")
    s = await settings()
    if sent and s["auto_delete"]:
        n = await client.send_message(
            uid, f"⏳ Ye content {readable(s['delete_time'])} me auto-delete ho jayega. Abhi save/forward kar lo.")
        sent.append(n)
        asyncio.create_task(delete_later(sent, s["delete_time"]))
