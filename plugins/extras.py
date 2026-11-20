import html

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core.db import db, now
from core.helpers import temp, ist, readable
from core import files as F

A = filters.user(C.ADMINS)


# ---------------- referral ----------------
async def _refer_msg(uid):
    pts = await db.refer_points(uid)
    link = f"https://t.me/{temp.U_NAME}?start=reff_{uid}"
    return (f"🎁 <b>Refer & Earn Premium</b>\n\nAapka link:\n<code>{link}</code>\n\n"
            f"Har naye dost ke join par <b>{C.REFER_POINTS} points</b>. {C.REFER_TARGET} points = <b>{C.REFER_PREMIUM}</b> premium.\n"
            f"⏳ Aapke points: <b>{pts}</b>")


@Client.on_message(filters.command("refer") & filters.private)
async def refer(client, m):
    await m.reply_text(await _refer_msg(m.from_user.id), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^refer$"))
async def refer_cb(client, q):
    await q.answer()
    await client.send_message(q.from_user.id, await _refer_msg(q.from_user.id), disable_web_page_preview=True)


# ---------------- latest lists ----------------
async def _latest(m, prefix, label):
    rows = await db.list_contents(15, prefix)
    if not rows:
        return await m.reply_text(f"❌ Abhi koi {label} content nahi.")
    kb = [[Btn(f"{'📺' if prefix == 't' else '🎬'} {x['title']}"[:60], url=f"https://t.me/{temp.U_NAME}?start=t_{x['_id']}")] for x in rows]
    await m.reply_text(f"<b>🆕 Latest {label}</b> (content ready)", reply_markup=Markup(kb))


@Client.on_message(filters.command("movies"))
async def movies(client, m):
    titles = await F.get_latest_singles()
    if titles:
        await m.reply_text("<b>Latest Uploads ✅</b>\n\n<b>🎬 Titles:</b>\n\n" + "\n".join(f"<b>{i + 1}. {html.escape(t)}</b>" for i, t in enumerate(titles))[:4000])
    await _latest(m, "m", "Movies") if await db.list_contents(1, "m") else (None if titles else await m.reply_text("❌ Abhi kuch nahi mila."))


@Client.on_message(filters.command("series"))
async def series(client, m):
    data = await F.get_latest_series()
    if data:
        t = "<b>Latest Uploads ✅</b>\n\n<b>📺 Series:</b>\n"
        t += "\n".join(f"<b>{i}. {html.escape(n)} - Season {', '.join(map(str, ss))}</b>" for i, (n, ss) in enumerate(data.items(), 1))
        await m.reply_text(t[:4000])
    await _latest(m, "t", "Series") if await db.list_contents(1, "t") else (None if data else await m.reply_text("❌ Abhi kuch nahi mila."))


# ---------------- movie update channel ----------------
@Client.on_message(filters.command("movie_update") & A)
async def movie_update(client, m):
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off"):
        return await m.reply_text("Use: <code>/movie_update on</code> ya <code>off</code>\n(MOVIE_UPDATE_CHANNEL env zaruri hai)")
    await db.set_setting("movie_update", m.command[1].lower() == "on")
    await m.reply_text(f"✅ Movie update notification: {m.command[1].upper()}")


@Client.on_message(filters.command("del_msg") & A)
async def del_msg(client, m):
    await db.clear_update_names()
    await m.reply_text("✅ Update-notification history clear. Ab purane titles dubara post ho sakte hain.")


# ---------------- admin utils ----------------
@Client.on_message(filters.command("get_premium") & A)
async def get_premium(client, m):
    if len(m.command) != 2 or not m.command[1].isdigit():
        return await m.reply_text("Use: <code>/get_premium user_id</code>")
    uid = int(m.command[1])
    p = await db.get_premium(uid)
    if not p or not p.get("expiry_time") or p["expiry_time"] < now():
        return await m.reply_text("❌ Is user ka premium data nahi mila.")
    left = (p["expiry_time"] - now()).total_seconds()
    await m.reply_text(f"⚜️ <b>Premium user</b>\n🆔 <code>{uid}</code>\n⏰ Left: {readable(left)}\n⌛ Expiry: {ist(p['expiry_time'])}")


@Client.on_message(filters.command("invite") & A)
async def invite(client, m):
    if len(m.command) < 2:
        return await m.reply_text("Use: <code>/invite chat_id</code>")
    try:
        link = await client.create_chat_invite_link(int(m.command[1]))
        await m.reply_text(f"🔗 {link.invite_link}")
    except Exception as e:
        await m.reply_text(f"❌ {e}")


@Client.on_message(filters.command("group_cmd"))
async def group_cmd(client, m):
    await m.reply_text(
        "<b>👥 Group commands (group admin)</b>\n\n/settings - Settings panel\n/connect - Group ko PM se jodo\n"
        "/verify on|off\n/set_shortner site api  (_2, _3 bhi)\n/set_time 1200 | /set_time_2 54000 | /set_time valid 86400\n"
        "/set_tutorial link\n/set_template text\n/set_caption text\n/set_fsub ids\n/set_log_channel id\n/reset_group")


@Client.on_message(filters.command("admin_cmd") & A)
async def admin_cmd(client, m):
    await m.reply_text(
        "<b>👑 Admin commands</b>\n\n<b>Content:</b> /addcontent /delcontent /contents /demand /movie_update /del_msg\n"
        "<b>Files:</b> /setskip /delete /deleteall /deletefiles (+ channel forward/link = index)\n"
        "<b>Users:</b> /stats /users /chats /broadcast /grp_broadcast /send /ban /unban /disable /enable /leave /invite /clear_junk /junk_group\n"
        "<b>Premium:</b> /add_premium /remove_premium /get_premium /premium_users /add_redeem /trial_reset\n"
        "<b>Settings:</b> /settings /verify /set_shortner(_2,_3) /set_time /set_tutorial /set_template /set_caption /set_fsub /set_log_channel /pm_search /resetallgroup\n"
        "<b>Other:</b> /delreq /logs /restart /set_commands /system")
