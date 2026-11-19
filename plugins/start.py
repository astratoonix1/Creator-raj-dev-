import asyncio
import html
import random
import time

import psutil
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup, ChatJoinRequest

import config as C
from core.db import db
from core.flow import send_card, read_flow, verify_return, gid_of
from core.helpers import temp, log_msg, readable, fsub_block, settings, seconds, ist


# ---------- ban gate (sabse pehle chalta hai) ----------
@Client.on_message((filters.private | filters.group) & ~filters.service, group=-2)
async def ban_gate(client, m):
    if m.from_user and m.from_user.id in temp.BANNED_USERS:
        if m.chat.type == enums.ChatType.PRIVATE and m.text and m.text.startswith("/start"):
            await m.reply_text("🚫 Aap bot se ban ho.")
        m.stop_propagation()
    if m.chat.id in temp.BANNED_CHATS:
        m.stop_propagation()


@Client.on_callback_query(group=-2)
async def ban_gate_cb(client, q):
    if q.from_user.id in temp.BANNED_USERS:
        await q.answer("🚫 Aap ban ho.", show_alert=True)
        q.stop_propagation()


# ---------- fsub join requests ----------
@Client.on_chat_join_request()
async def join_req(client, r: ChatJoinRequest):
    if r.chat.id in C.AUTH_REQ_CHANNELS:
        await db.add_join_req(r.from_user.id, r.chat.id)


# ---------- group me add hone par ----------
@Client.on_message(filters.new_chat_members & filters.group)
async def added(client, m):
    if any(u.id == temp.ME for u in m.new_chat_members):
        if await db.add_chat(m.chat.id, m.chat.title):
            await log_msg(client, f"#NewGroup\n{html.escape(m.chat.title)} <code>{m.chat.id}</code>\nMembers: {await client.get_chat_members_count(m.chat.id)}")
        return await m.reply_text("Thanks for adding me! 🎬 Movie/series ka naam likho — trailer & info milegi.\n\nGroup admin: /settings se verify, shortener, template wagairah set karo.")
    st = await settings(m.chat.id)
    if st["welcome"]:
        names = ", ".join(u.mention for u in m.new_chat_members if not u.is_bot)
        if names:
            text = f"👋 Welcome {names} to <b>{html.escape(m.chat.title)}</b>!\nMovie/series ka naam likho — trailer & info milegi 🎬"
            try:
                if C.MELCOW_PHOTO:
                    r = await m.reply_photo(C.MELCOW_PHOTO, caption=text)
                else:
                    r = await m.reply_text(text)
                if st["auto_delete"]:
                    from core.helpers import delete_later
                    asyncio.create_task(delete_later([r], 120))
            except Exception:
                pass


# ---------- /start ----------
def home_kb():
    rows = [[Btn("🔥 Trending", callback_data="home_trend"), Btn("💎 Premium", callback_data="plan")]]
    ex = []
    if C.UPDATE_CHNL_LNK:
        ex.append(Btn("📢 Updates", url=C.UPDATE_CHNL_LNK))
    if C.GRP_LNK:
        ex.append(Btn("💬 Group", url=C.GRP_LNK))
    if ex:
        rows.append(ex)
    rows.append([Btn("➕ Add me to Group", url=f"https://t.me/{temp.U_NAME}?startgroup=true")])
    return Markup(rows)


@Client.on_message(filters.command("start"))
async def start(client, m):
    uid = m.from_user.id
    if m.chat.type != enums.ChatType.PRIVATE:
        await db.add_chat(m.chat.id, m.chat.title)
        return await m.reply_text("Movie/series ka naam bhejo 🎬")
    is_new = await db.add_user(uid, m.from_user.first_name)
    if is_new:
        await log_msg(client, f"#NewUser\n👤 {m.from_user.mention} <code>{uid}</code>\nTotal: {await db.total_users()}")
    arg = m.command[1] if len(m.command) > 1 else ""
    if arg.startswith("reff_"):
        await referral(client, m, is_new, arg)
        arg = ""
    parts = arg.split("_")
    if arg.startswith("t_"):
        gid = gid_of(parts[2]) if len(parts) > 2 else None
        block = await fsub_block(client, uid, retry_url=f"https://t.me/{temp.U_NAME}?start={arg}", gid=gid)
        if block:
            return await m.reply_text("⚠️ <b>Pehle channel join karo, fir Try Again dabao.</b>", reply_markup=Markup(block))
        return await send_card(client, m.chat.id, parts[1], gid=gid)
    if arg.startswith("rd_"):
        return await read_flow(client, uid, m.chat.id, parts[1], gid_of(parts[2]) if len(parts) > 2 else None)
    if arg.startswith("vf_"):
        try:
            _, u, token, step, key, g = arg.split("_", 5)
            return await verify_return(client, m, int(u), token, step, key, gid_of(g))
        except ValueError:
            return await m.reply_text("❌ Invalid link.")
    text = (f"👋 <b>Hi {m.from_user.mention}!</b>\n\n"
            "🎬 Kisi bhi <b>movie / web-series</b> ka naam bhejo.\n"
            "Mujhse milega: poster, rating, cast, <b>trailer</b> aur 📖 padhne ka content.\n\n"
            "Try: <code>Pushpa 2</code>")
    if C.PICS:
        try:
            return await m.reply_photo(random.choice(C.PICS), caption=text, reply_markup=home_kb())
        except Exception:
            pass
    await m.reply_text(text, reply_markup=home_kb())


async def referral(client, m, is_new, arg):
    uid = m.from_user.id
    try:
        ref = int(arg.split("_")[1])
    except (ValueError, IndexError):
        return await m.reply_text("Invalid refer link!")
    if ref == uid or not is_new or await db.already_referred(uid) or not await db.is_user_exist(ref):
        return await m.reply_text("ℹ️ Refer sirf naye users ke liye valid hai.")
    await db.mark_referred(uid)
    pts = await db.refer_points(ref) + C.REFER_POINTS
    msg = f"🎉 Aapke refer se <b>{m.from_user.first_name}</b> join hua! +{C.REFER_POINTS} points. Total: {pts}"
    if pts >= C.REFER_TARGET:
        exp = await db.add_premium(ref, seconds(C.REFER_PREMIUM))
        pts = 0
        msg += f"\n\n💎 Congrats! {C.REFER_PREMIUM} premium mila. Expiry: {ist(exp)}"
    await db.set_refer_points(ref, pts)
    try:
        await client.send_message(ref, msg)
    except Exception:
        pass
    await m.reply_text("✅ Refer link se join karne ke liye thanks!")


@Client.on_callback_query(filters.regex(r"^home_trend$"))
async def home_trend(client, q):
    from core import tmdb
    from core.flow import show_results
    res = await tmdb.trending()
    await q.answer()
    await show_results(client, q.message, "Trending this week", res)


# ---------- small commands ----------
@Client.on_message(filters.command(["help", "commands"]))
async def help_cmd(client, m):
    t = ("<b>📚 Commands</b>\n/start - Start\n/trending - Is hafte ke trending\n/movies /series - Latest content\n/trendlist - Top searches\n"
         "/request name - Request\n/plan - Premium\n/myplan - Aapka plan\n/refer - Refer & earn\n/redeem code - Code redeem\n"
         "/font text - Fancy fonts\n/telegraph - Image ko link banao (reply)\n/id /info /stickerid /ping /system\n"
         "/group_cmd - Group admin commands\n")
    if m.from_user.id in C.ADMINS:
        t += "\n👑 Admin ke liye: /admin_cmd"
    await m.reply_text(t)


@Client.on_message(filters.command("id"))
async def id_cmd(client, m):
    t = f"👤 Your ID: <code>{m.from_user.id}</code>\n💬 Chat ID: <code>{m.chat.id}</code>"
    if m.reply_to_message and m.reply_to_message.from_user:
        t += f"\n↩️ Replied user: <code>{m.reply_to_message.from_user.id}</code>"
    await m.reply_text(t)


@Client.on_message(filters.command("info"))
async def info_cmd(client, m):
    u = m.reply_to_message.from_user if (m.reply_to_message and m.reply_to_message.from_user) else m.from_user
    prem = await db.is_premium(u.id)
    await m.reply_text(f"<b>ℹ️ User Info</b>\nName: {u.mention}\nID: <code>{u.id}</code>\nUsername: @{u.username}\nPremium: {'✅' if prem else '❌'}")


@Client.on_message(filters.command(["ping", "alive"]))
async def ping(client, m):
    t = time.time()
    r = await m.reply_text("🏓 …")
    await r.edit_text(f"✅ <b>Alive!</b>\nPing: {round((time.time() - t) * 1000)} ms\nUptime: {readable(time.time() - temp.BOT_START)}")


@Client.on_message(filters.command("request"))
async def request(client, m):
    if len(m.command) < 2:
        return await m.reply_text("Usage: <code>/request Movie Name</code>")
    text = m.text.split(None, 1)[1]
    await client.send_message(C.REQST_CHANNEL, f"📩 #Request\n👤 {m.from_user.mention} <code>{m.from_user.id}</code>\n🎬 {html.escape(text)}")
    await m.reply_text("✅ Request admin ko bhej di gayi.")


@Client.on_message(filters.command("stats") & filters.user(C.ADMINS))
async def stats(client, m):
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    await m.reply_text(
        "<b>📊 Bot Stats</b>\n"
        f"👤 Users: <code>{await db.total_users()}</code>\n💬 Groups: <code>{await db.total_chats()}</code>\n"
        f"📖 Contents: <code>{await db.total_contents()}</code>\n💎 Premium: <code>{len(await db.all_premium())}</code>\n"
        f"🗄 DB size: <code>{round(await db.db_size() / 1048576, 2)} MB</code>\n"
        f"⚙️ CPU {cpu}% | RAM {ram}%\n⏱ Uptime: {readable(time.time() - temp.BOT_START)}")
