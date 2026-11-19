"""Admin: kisi bhi movie/series ke naam par apna padhne ka content jodo."""
import html
import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core import tmdb
from core.db import db
from core.helpers import rand, temp
from core.flow import notify_update

KEY = re.compile(r"^[mt]\d+$")


async def _save(client, key, mid):
    d = await tmdb.details(key)
    title = f"{d['title']} ({d['year']})" if d else key
    await db.add_content(key, title, mid)
    c = await db.get_content(key)
    await notify_update(client, key)
    return title, len(c["items"])


@Client.on_message(filters.command("addcontent") & filters.user(C.ADMINS))
async def addcontent(client, m):
    r = m.reply_to_message
    if not r or len(m.command) < 2:
        return await m.reply_text(
            "<b>Use:</b> jo content (text/link/photo/pdf/post) dena hai usko <b>reply</b> karke:\n"
            "<code>/addcontent Pushpa 2</code>\nya direct id: <code>/addcontent m12345</code> (movie) / <code>/addcontent t1399</code> (series)\n\n"
            "Ek title par kai baar add kar sakte ho — sab ek saath milenge.")
    if not C.CONTENT_CHANNEL:
        return await m.reply_text("❌ CONTENT_CHANNEL env set nahi hai.")
    try:
        copied = await r.copy(C.CONTENT_CHANNEL)
    except Exception as e:
        return await m.reply_text(f"❌ CONTENT_CHANNEL me copy nahi hua (bot admin hai?)\n<code>{e}</code>")
    arg = m.text.split(None, 1)[1].strip()
    if KEY.match(arg.lower()):
        title, n = await _save(client, arg.lower(), copied.id)
        return await m.reply_text(f"✅ <b>{html.escape(title)}</b> me content add hua. Total items: {n}")
    res = await tmdb.search(arg)
    if not res:
        return await m.reply_text("❌ TMDB par ye naam nahi mila.")
    pk = rand(6)
    temp.PENDING[pk] = copied.id
    rows = [[Btn(f"{'📺' if x['media'] == 'tv' else '🎬'} {x['title']} ({x['year']})"[:60], callback_data=f"ac_{pk}_{x['key']}")] for x in res[:6]]
    rows.append([Btn("🚫 Cancel", callback_data="close")])
    await m.reply_text("Kis title me add karun? 👇", reply_markup=Markup(rows))


@Client.on_callback_query(filters.regex(r"^ac_") & filters.user(C.ADMINS))
async def ac_pick(client, q):
    _, pk, key = q.data.split("_")
    mid = temp.PENDING.pop(pk, None)
    if not mid:
        return await q.answer("Expire ho gaya, dobara /addcontent karo.", show_alert=True)
    title, n = await _save(client, key, mid)
    await q.message.edit_text(f"✅ <b>{html.escape(title)}</b> (<code>{key}</code>) me content add hua. Total items: {n}")


@Client.on_message(filters.command("delcontent") & filters.user(C.ADMINS))
async def delcontent(client, m):
    if len(m.command) < 2 or not KEY.match(m.command[1].lower()):
        return await m.reply_text("Use: <code>/delcontent m12345</code>")
    n = await db.del_content(m.command[1].lower())
    await m.reply_text("🗑 Deleted." if n else "❌ Is id par content nahi mila.")


@Client.on_message(filters.command("contents") & filters.user(C.ADMINS))
async def contents(client, m):
    rows = await db.list_contents()
    if not rows:
        return await m.reply_text("Abhi koi content nahi.")
    await m.reply_text("<b>📖 Latest contents</b>\n\n" + "\n".join(
        f"• {html.escape(x['title'])} — <code>{x['_id']}</code> ({len(x['items'])})" for x in rows))


@Client.on_message(filters.command("demand") & filters.user(C.ADMINS))
async def demand(client, m):
    """Jis title ki demand hai par content nahi - pehle wahi banao (zyada kamai)."""
    rows = await db.top_demand(missing_only=True)
    if not rows:
        return await m.reply_text("Sab demanded titles ka content available hai 🎉")
    await m.reply_text("<b>📭 Demand hai, content nahi</b>\n\n" + "\n".join(
        f"• {html.escape(x['title'])} — <code>{x['_id']}</code> — 👁 {x['count']}" for x in rows))
