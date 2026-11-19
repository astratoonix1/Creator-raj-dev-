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


# ---------------- ads / verify settings ----------------
async def _toggle(m, key, label):
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off"):
        return await m.reply_text(f"Use: <code>/{m.command[0]} on</code> ya <code>off</code>")
    v = m.command[1].lower() == "on"
    await db.set_setting(key, v)
    await m.reply_text(f"✅ {label}: {'ON' if v else 'OFF'}")


@Client.on_message(filters.command("verify") & A)
async def verify(client, m):
    await _toggle(m, "is_verify", "Verify (ads)")


@Client.on_message(filters.command("pm_search") & A)
async def pm_search(client, m):
    await _toggle(m, "pm_search", "PM search")


@Client.on_message(filters.command("group_search") & A)
async def group_search(client, m):
    await _toggle(m, "group_search", "Group search")


@Client.on_message(filters.command("auto_delete") & A)
async def auto_delete(client, m):
    await _toggle(m, "auto_delete", "Auto delete")


def _shortener(n):
    api_k, site_k = {1: ("api", "site"), 2: ("api2", "site2"), 3: ("api3", "site3")}[n]
    cmd = "set_shortner" + ("" if n == 1 else f"_{n}")

    @Client.on_message(filters.command(cmd) & A)
    async def h(client, m):
        if len(m.command) != 3:
            return await m.reply_text(f"Use: <code>/{cmd} example.com api_key</code>")
        await db.set_setting(site_k, m.command[1])
        await db.set_setting(api_k, m.command[2])
        await m.reply_text(f"✅ Shortener {n} set: {m.command[1]}")

    globals()[f"set_shortner_{n}"] = h   # pyrogram plugin loader ko dikhe


for _n in (1, 2, 3):
    _shortener(_n)


@Client.on_message(filters.command(["set_time", "set_time_2"]) & A)
async def set_time(client, m):
    """/set_time 1200 -> 2nd shortener gap | /set_time_2 54000 -> 3rd gap | /set_time valid 86400"""
    a = m.command
    if len(a) == 2 and a[1].isdigit():
        key = "gap2" if a[0] == "set_time" else "gap3"
        await db.set_setting(key, int(a[1]))
        return await m.reply_text(f"✅ {key} = {a[1]} sec")
    if len(a) == 3 and a[1] == "valid" and a[2].isdigit():
        await db.set_setting("valid", int(a[2]))
        return await m.reply_text(f"✅ valid = {a[2]} sec")
    await m.reply_text("Use:\n<code>/set_time 1200</code> (2nd verify gap)\n<code>/set_time_2 54000</code> (3rd verify gap)\n<code>/set_time valid 86400</code> (verify validity)")


@Client.on_message(filters.command("set_tutorial") & A)
async def set_tutorial(client, m):
    if len(m.command) != 2:
        return await m.reply_text("Use: <code>/set_tutorial https://t.me/...</code>")
    await db.set_setting("tutorial", m.command[1])
    await m.reply_text("✅ Tutorial link set.")


@Client.on_message(filters.command("settings") & A)
async def show_settings(client, m):
    s = await settings()
    sh = lambda a, w: f"{w} ✅" if a and w else "❌ not set"
    await m.reply_text(
        "<b>⚙️ Current Settings</b>\n\n"
        f"Verify (ads): {'ON' if s['is_verify'] else 'OFF'}\n"
        f"Shortener 1: {sh(s['api'], s['site'])}\nShortener 2: {sh(s['api2'], s['site2'])}\nShortener 3: {sh(s['api3'], s['site3'])}\n"
        f"Verify valid: {readable(s['valid'])}\n2nd gap: {readable(s['gap2'])} | 3rd gap: {readable(s['gap3'])}\n"
        f"Tutorial: {s['tutorial'] or '-'}\nPM search: {s['pm_search']} | Group search: {s['group_search']}\n"
        f"Auto delete: {s['auto_delete']} ({readable(s['delete_time'])})")


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
