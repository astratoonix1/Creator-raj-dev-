import asyncio
import io
import os
import sys

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

import config as C
from core.db import db
from core.helpers import temp, settings, readable

A = filters.user(C.ADMINS)


# ---------------- broadcast ----------------
async def _cast(client, m, cursor, key, delete_fn, label):
    if not m.reply_to_message:
        return await m.reply_text("Kisi message ko reply karke command do.")
    msg = await m.reply_text(f"📣 {label} broadcast shuru…")
    ok = bad = 0
    async for x in cursor:
        cid = x[key]
        try:
            await m.reply_to_message.copy(cid)
            ok += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await m.reply_to_message.copy(cid)
                ok += 1
            except Exception:
                bad += 1
        except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
            await delete_fn(cid)
            bad += 1
        except Exception:
            bad += 1
        if (ok + bad) % 50 == 0:
            try:
                await msg.edit_text(f"📣 Done: {ok + bad} | ✅ {ok} | ❌ {bad}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await msg.edit_text(f"✅ <b>Broadcast complete</b>\nSuccess: {ok}\nFailed/removed: {bad}")


@Client.on_message(filters.command("broadcast") & A)
async def broadcast(client, m):
    await _cast(client, m, await db.all_users(), "id", db.del_user, "Users")


@Client.on_message(filters.command("grp_broadcast") & A)
async def grp_broadcast(client, m):
    await _cast(client, m, await db.all_chats(), "id", db.del_chat, "Groups")


@Client.on_message(filters.command("send") & A)
async def send(client, m):
    if not m.reply_to_message or len(m.command) < 2:
        return await m.reply_text("Reply karke: <code>/send user_id</code>")
    try:
        await m.reply_to_message.copy(int(m.command[1]))
        await m.reply_text("✅ Sent")
    except Exception as e:
        await m.reply_text(f"❌ {e}")


# ---------------- ban / chats ----------------
@Client.on_message(filters.command("ban") & A)
async def ban(client, m):
    if len(m.command) < 2 or not m.command[1].lstrip("-").isdigit():
        return await m.reply_text("Use: <code>/ban user_id reason</code>")
    uid = int(m.command[1])
    await db.ban_user(uid, " ".join(m.command[2:]) or "No reason")
    temp.BANNED_USERS.add(uid)
    await m.reply_text(f"🚫 Banned <code>{uid}</code>")


@Client.on_message(filters.command("unban") & A)
async def unban(client, m):
    if len(m.command) < 2 or not m.command[1].lstrip("-").isdigit():
        return await m.reply_text("Use: <code>/unban user_id</code>")
    uid = int(m.command[1])
    await db.unban_user(uid)
    temp.BANNED_USERS.discard(uid)
    await m.reply_text(f"✅ Unbanned <code>{uid}</code>")


@Client.on_message(filters.command("disable") & A)
async def disable(client, m):
    if len(m.command) < 2:
        return await m.reply_text("Use: <code>/disable chat_id reason</code>")
    cid = int(m.command[1])
    await db.set_chat(cid, disabled=True, reason=" ".join(m.command[2:]))
    temp.BANNED_CHATS.add(cid)
    await m.reply_text("🚫 Chat disabled.")


@Client.on_message(filters.command("enable") & A)
async def enable(client, m):
    if len(m.command) < 2:
        return await m.reply_text("Use: <code>/enable chat_id</code>")
    cid = int(m.command[1])
    await db.set_chat(cid, disabled=False, reason="")
    temp.BANNED_CHATS.discard(cid)
    await m.reply_text("✅ Chat enabled.")


@Client.on_message(filters.command("leave") & A)
async def leave(client, m):
    if len(m.command) < 2:
        return await m.reply_text("Use: <code>/leave chat_id</code>")
    try:
        await client.leave_chat(int(m.command[1]))
        await m.reply_text("👋 Left.")
    except Exception as e:
        await m.reply_text(f"❌ {e}")


@Client.on_message(filters.command("users") & A)
async def users(client, m):
    out = io.BytesIO()
    async for u in await db.all_users():
        out.write(f"{u['id']} - {u.get('name', '')}\n".encode())
    out.name = "users.txt"
    out.seek(0)
    await m.reply_document(out, caption=f"Total users: {await db.total_users()}")


@Client.on_message(filters.command("chats") & A)
async def chats(client, m):
    out = io.BytesIO()
    async for c in await db.all_chats():
        out.write(f"{c['id']} - {c.get('title', '')}\n".encode())
    out.name = "chats.txt"
    out.seek(0)
    await m.reply_document(out, caption=f"Total chats: {await db.total_chats()}")


@Client.on_message(filters.command("pm_search") & A)
async def pm_search(client, m):
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off"):
        return await m.reply_text("Use: <code>/pm_search on</code> ya <code>off</code>")
    await db.set_setting("pm_search", m.command[1].lower() == "on")
    await m.reply_text(f"✅ PM search: {m.command[1].upper()}")


# ---------------- misc admin ----------------
@Client.on_message(filters.command("delreq") & A)
async def delreq(client, m):
    await db.clear_join_req()
    await m.reply_text("✅ Join-request data clear.")


@Client.on_message(filters.command("logs") & A)
async def logs(client, m):
    if os.path.exists("logs.txt"):
        await m.reply_document("logs.txt")
    else:
        await m.reply_text("Log file nahi mili.")


@Client.on_message(filters.command("restart") & A)
async def restart(client, m):
    await m.reply_text("♻️ Restarting…")
    os.execl(sys.executable, sys.executable, *sys.argv)
