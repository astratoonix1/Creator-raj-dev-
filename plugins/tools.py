import asyncio
import os

import aiohttp
import psutil
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from pyrogram.types import BotCommand

import config as C
from core.db import db
from core.helpers import readable

A = filters.user(C.ADMINS)


# ---------------- image -> link (imgbb) ----------------
@Client.on_message(filters.command(["img", "cup", "telegraph"]) & filters.reply)
async def upload(client, m):
    if not C.IMGBB_API_KEY:
        return await m.reply_text("❌ IMGBB_API_KEY env set nahi hai (imgbb.com se free key lo).")
    r = m.reply_to_message
    if not (r.photo or (r.document and r.document.mime_type and r.document.mime_type.startswith("image"))):
        return await m.reply_text("Kisi image ko reply karke command do.")
    if r.document and r.document.file_size > 5 * 1024 * 1024:
        return await m.reply_text("File size limit 5 MB.")
    msg = await m.reply_text("⏳ Uploading…")
    path = None
    try:
        path = await r.download()
        data = aiohttp.FormData()
        data.add_field("key", C.IMGBB_API_KEY)
        with open(path, "rb") as f:
            data.add_field("image", f.read(), filename=os.path.basename(path))
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.imgbb.com/1/upload", data=data) as resp:
                j = await resp.json()
        if j.get("success"):
            await msg.edit_text(j["data"]["url"])
        else:
            await msg.edit_text("❌ Upload fail, baad me try karo.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


# ---------------- sticker id / system / bot menu ----------------
@Client.on_message(filters.command("stickerid"))
async def stickerid(client, m):
    r = m.reply_to_message
    if r and r.sticker:
        return await m.reply_text(f"<b>File ID:</b>\n<code>{r.sticker.file_id}</code>\n\n<b>Unique ID:</b>\n<code>{r.sticker.file_unique_id}</code>")
    await m.reply_text("Kisi sticker ko reply karke /stickerid likho.")


@Client.on_message(filters.command("system"))
async def system(client, m):
    d = psutil.disk_usage("/")
    mem = psutil.virtual_memory()
    await m.reply_text(
        f"<b>🖥 System</b>\nCPU: {psutil.cpu_percent()}%\nRAM: {mem.percent}% ({round(mem.used / 2**30, 2)}/{round(mem.total / 2**30, 2)} GB)\n"
        f"Disk: {d.percent}% ({round(d.used / 2**30, 1)}/{round(d.total / 2**30, 1)} GB)")


async def set_menu(client):
    await client.set_bot_commands([BotCommand(c, d) for c, d in C.BOT_COMMANDS.items()])


@Client.on_message(filters.command("set_commands") & A)
async def set_commands(client, m):
    await set_menu(client)
    await m.reply_text("✅ Bot menu commands update ho gaye.")


# ---------------- junk cleaner ----------------
@Client.on_message(filters.command("clear_junk") & A)
async def clear_junk(client, m):
    msg = await m.reply_text("🧹 Dead/blocked users check ho rahe hain…")
    ok = dead = 0
    async for u in await db.all_users():
        try:
            await client.send_chat_action(u["id"], enums.ChatAction.TYPING)
            ok += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
            await db.del_user(u["id"])
            dead += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await msg.edit_text(f"✅ Done\nActive: {ok}\nRemoved (deleted/blocked): {dead}")


@Client.on_message(filters.command(["junk_group", "clear_junk_group"]) & A)
async def junk_group(client, m):
    msg = await m.reply_text("🧹 Groups check ho rahe hain…")
    ok = dead = 0
    async for c in await db.all_chats():
        try:
            await client.get_chat(c["id"])
            await client.get_chat_member(c["id"], "me")
            ok += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            await db.del_chat(c["id"])
            dead += 1
        await asyncio.sleep(0.05)
    await msg.edit_text(f"✅ Done\nActive groups: {ok}\nRemoved: {dead}")
