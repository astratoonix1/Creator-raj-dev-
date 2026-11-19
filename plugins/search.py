import html
import random

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core import tmdb
from core.db import db
from core.flow import show_results, results_markup, send_card, read_flow, cache, gid_of
from core.helpers import temp, clean_query, settings, fsub_block, log_msg


@Client.on_message(filters.text & ~filters.regex(r"^[/!.]") & (filters.private | filters.group) & ~filters.via_bot, group=1)
async def on_text(client, m):
    if not m.from_user:
        return
    group = m.chat.type.name in ("GROUP", "SUPERGROUP")
    s = await settings(m.chat.id if group else None)
    if (group and not s["group_search"]) or (not group and not s["pm_search"] and m.from_user.id not in C.ADMINS):
        return
    q = clean_query(m.text)
    if len(q) < 2 or (group and len(q) > 60):
        return
    if not group:
        block = await fsub_block(client, m.from_user.id, retry_url=f"https://t.me/{temp.U_NAME}")
        if block:
            return await m.reply_text("⚠️ <b>Pehle neeche diye channel(s) join karo, phir dobara search karo.</b>",
                                      reply_markup=Markup(block))
    res = await tmdb.search(q)
    if not res and len(q.split()) > 2:
        res = await tmdb.search(" ".join(q.split()[:2]))
    if not res:
        if group:
            return      # group me no-result par chup rehna
        k = cache(q)
        await log_msg(client, f"🔍 #NoResult\n👤 {m.from_user.mention} <code>{m.from_user.id}</code>\n📝 {html.escape(q)}")
        return await m.reply_text(
            f"❌ <b>{html.escape(q)}</b> nahi mila.\nSpelling check karke dobara bhejo (movie/series ka official naam).",
            reply_markup=Markup([[Btn("📩 Request Admin", callback_data=f"rq_{k}")]]))
    await db.bump_search(q.lower())
    await show_results(client, m, q, res, group)


@Client.on_message(filters.command("trending"))
async def trending(client, m):
    res = await tmdb.trending()
    if not res:
        return await m.reply_text("❌ TMDB se data nahi aaya.")
    group = m.chat.type.name in ("GROUP", "SUPERGROUP")
    await show_results(client, m, "Trending this week", res, group)


@Client.on_message(filters.command(["trendlist", "top_search"]))
async def trendlist(client, m):
    top = await db.top_searches()
    if not top:
        return await m.reply_text("Abhi koi data nahi.")
    await m.reply_text("<b>🔥 Top Searches</b>\n\n" + "\n".join(f"{i}. {html.escape(x['_id'].title())} — {x['count']}" for i, x in enumerate(top, 1)))


# ---------------- callbacks ----------------
@Client.on_callback_query(filters.regex(r"^pg_"))
async def page(client, q):
    _, skey, p = q.data.split("_")
    kb = await results_markup(skey, int(p))
    if not kb:
        return await q.answer("Search expire ho gaya, dobara search karo.", show_alert=True)
    try:
        await q.message.edit_reply_markup(kb)
    except Exception:
        pass
    await q.answer()


@Client.on_callback_query(filters.regex(r"^tm_"))
async def card(client, q):
    _, skey, key = q.data.split("_")
    await q.answer("Loading…")
    try:
        await q.message.delete()
    except Exception:
        pass
    await send_card(client, q.message.chat.id, key, back=skey if skey in temp.SEARCH else None)


@Client.on_callback_query(filters.regex(r"^rd_"))
async def read(client, q):
    parts = q.data[3:].split("_")
    await q.answer()
    await read_flow(client, q.from_user.id, q.message.chat.id, parts[0], gid_of(parts[1]) if len(parts) > 1 else None)


@Client.on_callback_query(filters.regex(r"^rq_"))
async def request_cb(client, q):
    text = temp.SEARCH.get(q.data[3:])
    if not isinstance(text, str):
        return await q.answer("Expire ho gaya.", show_alert=True)
    await client.send_message(C.REQST_CHANNEL, f"📩 #Request\n👤 {q.from_user.mention} <code>{q.from_user.id}</code>\n🎬 {html.escape(text)}")
    await q.message.edit_text("✅ Request admin ko bhej di gayi.")
    await q.answer()


@Client.on_callback_query(filters.regex(r"^close$"))
async def close(client, q):
    try:
        await q.message.delete()
    except Exception:
        await q.answer()


@Client.on_callback_query(filters.regex(r"^noop$"))
async def noop(client, q):
    await q.answer()
