"""Files: auto-index, manual index (/setskip), delete, search filters/pagination, stream links, request moderation.
Original DreamXBotz (index.py, files_delete.py, pmfilter.py) ka logic."""
import asyncio
import html
import logging
import re
import time
from math import ceil
from urllib.parse import quote_plus

from pyrogram import Client, filters, enums
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core import files as F, tmdb
from core.db import db
from core.flow import file_results, show_results, cache
from core.helpers import temp, readable, get_size, log_msg, settings
from stream.file_properties import get_name, get_hash

log = logging.getLogger(__name__)
A = filters.user(C.ADMINS)
media_filter = filters.document | filters.video | filters.audio
lock = asyncio.Lock()


def _media(message):
    for t in ("document", "video", "audio"):
        m = getattr(message, t, None)
        if m is not None:
            m.file_type = t
            m.caption = message.caption
            return m
    return None


# ================= auto index (CHANNELS) =================
@Client.on_message(filters.chat(C.CHANNELS) & media_filter)
async def auto_index(client, message):
    media = _media(message)
    if not media:
        return
    ok, code = await F.save_file(media)
    if not ok:
        return
    s = await settings()
    if not (C.MOVIE_UPDATE_CHANNEL and s["movie_update"]):
        return
    from core.flow import notify_update
    title = F.clean_title(media.file_name or "")
    try:
        if C.FILE_TMDB_MATCH:                      # movie/series channel: TMDB card
            res = await tmdb.search(title)
            if res:
                await notify_update(client, res[0]["key"])
            return
        if not await db.add_update_name("file:" + title.lower()):    # simple text update, ek title ek baar
            return
        d = await F.Media.find_one({"file_name": {"$regex": "^" + re.escape(F.clean_filename(title))}}) or {}
        kb = Markup([[Btn("📥 Get File", url=f"https://t.me/{temp.U_NAME}?start=rd_F{d['sid']}")]]) if d.get("sid") else None
        await client.send_message(C.MOVIE_UPDATE_CHANNEL, f"🆕 <b>New Upload</b>\n\n📄 {html.escape(title)}\n💾 {get_size(media.file_size)}", reply_markup=kb)
    except Exception as e:
        log.warning(f"file update post: {e}")


# ================= DELETE_CHANNELS = DB se delete =================
@Client.on_message(filters.chat(C.DELETE_CHANNELS) & media_filter)
async def delete_from_channel(client, message):
    media = _media(message)
    if media and await F.delete_one_media(media):
        log.info("File DB se delete hui.")


# ================= manual index =================
@Client.on_callback_query(filters.regex(r"^index"))
async def index_cb(bot, query):
    if query.data.startswith("index_cancel"):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, act, chat, lst, from_user = query.data.split("#")
    if query.from_user.id not in C.ADMINS:
        return await query.answer("Sirf admin.", show_alert=True)
    if act == "reject":
        await query.message.delete()
        return await bot.send_message(int(from_user), f"Aapka indexing request ({chat}) reject ho gaya.", reply_to_message_id=int(lst))
    if lock.locked():
        return await query.answer("Pehle wala process complete hone do.", show_alert=True)
    await query.answer("Processing…⏳", show_alert=True)
    if int(from_user) not in C.ADMINS:
        await bot.send_message(int(from_user), f"Aapka indexing request ({chat}) accept ho gaya, jald add hoga.", reply_to_message_id=int(lst))
    await query.message.edit("Starting Indexing", reply_markup=Markup([[Btn("Cancel", callback_data="index_cancel")]]))
    try:
        chat = int(chat)
    except ValueError:
        pass
    await index_files_to_db(int(lst), chat, query.message, bot)


LINK = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")


@Client.on_message((filters.forwarded | (filters.regex(LINK) & filters.text)) & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if message.text:
        match = LINK.match(message.text)
        if not match:
            return
        chat_id, last = match.group(4), int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply("Ye private channel/group ho sakta hai. Mujhe wahan admin banao.")
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("Invalid link.")
    except Exception as e:
        return await message.reply(f"Error - {e}")
    try:
        k = await bot.get_messages(chat_id, last)
    except Exception:
        return await message.reply("Private channel ho to mujhe wahan admin banao.")
    if k.empty:
        return await message.reply("Ye group ho sakta hai aur main admin nahi hoon.")
    uid = message.from_user.id
    if uid in C.ADMINS:
        return await message.reply(
            f"Is channel/group ko index karna hai?\n\nChat: <code>{chat_id}</code>\nLast Message ID: <code>{last}</code>\n\nSkip number ke liye 👉 /setskip",
            reply_markup=Markup([[Btn("Yes", callback_data=f"index#accept#{chat_id}#{last}#{uid}")], [Btn("Close", callback_data="close")]]))
    if isinstance(chat_id, int):
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply("Mujhe admin banao (invite link permission ke saath).")
    else:
        link = f"@{message.forward_from_chat.username}"
    kb = Markup([[Btn("Accept Index", callback_data=f"index#accept#{chat_id}#{last}#{uid}")],
                 [Btn("Reject Index", callback_data=f"index#reject#{chat_id}#{message.id}#{uid}")]])
    await bot.send_message(C.INDEX_REQ_CHANNEL,
                           f"#IndexRequest\n\nBy: {message.from_user.mention} (<code>{uid}</code>)\nChat: <code>{chat_id}</code>\nLast Msg ID: <code>{last}</code>\nLink: {link}",
                           reply_markup=kb)
    await message.reply("Thanks! Moderators verify karke files add karenge.")


@Client.on_message(filters.command("setskip") & A)
async def set_skip(bot, message):
    if len(message.command) == 2:
        try:
            temp.CURRENT = int(message.command[1])
        except ValueError:
            return await message.reply("Skip number integer hona chahiye.")
        return await message.reply(f"✅ SKIP number = {temp.CURRENT}")
    await message.reply("Use: <code>/setskip 0</code>")


def _bar(p, n=10):
    f = int(n * p / 100)
    return "🟩" * f + "⬜️" * (n - f)


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total = dup = err = deleted = no_media = unsupported = 0
    BATCH = 200
    start = time.time()
    cancel_kb = Markup([[Btn("Cancel", callback_data="index_cancel")]])
    close_kb = Markup([[Btn("Close", callback_data="close")]])
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            total_fetch = lst_msg_id - current
            if lst_msg_id <= 0 or total_fetch <= 0:
                return await msg.edit("🚫 Index karne ke liye messages nahi.", reply_markup=close_kb)
            batches = ceil(total_fetch / BATCH)
            times = []
            await msg.edit(f"📊 Indexing shuru…\n💬 Total: <code>{lst_msg_id}</code>\n📋 Fetch: <code>{total_fetch}</code>", reply_markup=cancel_kb)
            for b in range(batches):
                if temp.CANCEL:
                    break
                t0 = time.time()
                ids = list(range(current + 1, min(current + BATCH, lst_msg_id) + 1))
                try:
                    messages = await bot.get_messages(chat, ids)
                    if not isinstance(messages, list):
                        messages = [messages]
                except Exception:
                    err += len(ids)
                    current += len(ids)
                    continue
                tasks = []
                for m in messages:
                    current += 1
                    try:
                        if m.empty:
                            deleted += 1
                        elif not m.media:
                            no_media += 1
                        elif m.media not in (enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT):
                            unsupported += 1
                        else:
                            media = _media(m)
                            if media:
                                tasks.append(F.save_file(media))
                            else:
                                unsupported += 1
                    except Exception:
                        err += 1
                for r in await asyncio.gather(*tasks, return_exceptions=True):
                    if isinstance(r, Exception):
                        err += 1
                    else:
                        ok, code = r
                        if ok:
                            total += 1
                        elif code == 0:
                            dup += 1
                        else:
                            err += 1
                times.append(time.time() - t0)
                progress = current - temp.CURRENT
                pct = min(100, progress / total_fetch * 100)
                eta = (total_fetch - progress) / BATCH * (sum(times) / len(times))
                await msg.edit(
                    f"📊 Indexing 📦 Batch {b + 1}/{batches}\n{_bar(int(pct))} <code>{pct:.1f}%</code>\n\n"
                    f"Fetched: <code>{current}</code>\nSaved: <code>{total}</code>\nDuplicates: <code>{dup}</code>\n"
                    f"Deleted: <code>{deleted}</code>\nNon-media: <code>{no_media + unsupported}</code> (unsupported {unsupported})\n"
                    f"Errors: <code>{err}</code>\n⏱ Elapsed: <code>{readable(time.time() - start)}</code>\n⏰ ETA: <code>{readable(eta)}</code>",
                    reply_markup=cancel_kb)
            await msg.edit(
                f"✅ Indexing complete!\nFetched: <code>{current}</code>\nSaved: <code>{total}</code>\nDuplicates: <code>{dup}</code>\n"
                f"Deleted: <code>{deleted}</code>\nNon-media: <code>{no_media + unsupported}</code>\nErrors: <code>{err}</code>\n"
                f"⏱ Elapsed: <code>{readable(time.time() - start)}</code>", reply_markup=close_kb)
        except Exception as e:
            await msg.edit(f"❌ Error: <code>{e}</code>", reply_markup=close_kb)


# ================= delete commands =================
@Client.on_message(filters.command("delete") & A)
async def delete(bot, message):
    r = message.reply_to_message
    if not (r and r.media):
        return await message.reply("Jis file ko delete karna hai usko reply karke /delete likho.", quote=True)
    media = _media(r)
    if not media:
        return await message.reply("Ye file format supported nahi hai.")
    ok = await F.delete_one_media(media)
    await message.reply("✅ File database se delete ho gayi." if ok else "❌ File database me nahi mili.")


@Client.on_message(filters.command("deleteall") & A)
async def delete_all(bot, message):
    await message.reply_text("⚠️ Ye aapki saari indexed files delete kar dega!\nPakka continue?", quote=True,
                             reply_markup=Markup([[Btn("⚠️ YES ⚠️", callback_data="autofilter_delete")], [Btn("❌ NO ❌", callback_data="close")]]))


@Client.on_callback_query(filters.regex(r"^autofilter_delete") & A)
async def delete_all_cb(bot, q):
    await F.drop_all()
    await F.ensure_indexes()
    await q.answer("Everything's gone")
    await q.message.edit("✅ Saari indexed files delete ho gayi.")


@Client.on_message(filters.command("deletefiles") & A & filters.private)
async def delete_files(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("Use: <code>/deletefiles keyword</code>")
    kw = message.text.split(None, 1)[1]
    files, total = await F.get_bad_files(kw)
    await message.reply_text(f"<b>{total} files mili: {html.escape(kw)}\n\nDelete karni hai?</b>",
                             reply_markup=Markup([[Btn("⚠️ Yes, Continue", callback_data=f"killfilesdq#{kw}"[:64])], [Btn("❌ Abort", callback_data="close")]]))


@Client.on_callback_query(filters.regex(r"^killfilesdq#") & A)
async def kill_files(bot, q):
    kw = q.data.split("#", 1)[1]
    n = await F.delete_by_query(kw)
    await q.message.edit(f"✅ {n} files delete ho gayi (<b>{html.escape(kw)}</b>).")


# ================= file search: pagination / filters / info =================
def _owner(q, c):
    return isinstance(c, dict) and c.get("uid") == q.from_user.id


@Client.on_callback_query(filters.regex(r"^fp_"))
async def f_page(client, q):
    _, skey, off = q.data.split("_")
    c = temp.SEARCH.get(skey)
    if not _owner(q, c):
        return await q.answer("Ye search aapka nahi hai / expire ho gaya.", show_alert=True)
    r = await file_results(skey, int(off))
    try:
        await q.message.edit_text(r[0], reply_markup=r[1], disable_web_page_preview=True)
    except Exception:
        pass
    await q.answer()


@Client.on_callback_query(filters.regex(r"^ft_"))
async def f_filter_menu(client, q):
    _, skey, t = q.data.split("_")
    c = temp.SEARCH.get(skey)
    if not _owner(q, c):
        return await q.answer("Ye search aapka nahi hai / expire ho gaya.", show_alert=True)
    opts = {"q": C.QUALITIES, "l": list(C.LANGUAGES), "s": C.SEASONS}[t]
    rows, row = [], []
    for i, o in enumerate(opts):
        row.append(Btn(o, callback_data=f"fs_{skey}_{t}_{i}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([Btn("⬅️ Back", callback_data=f"fp_{skey}_0")])
    await q.message.edit_reply_markup(Markup(rows))
    await q.answer()


@Client.on_callback_query(filters.regex(r"^fs_"))
async def f_filter_pick(client, q):
    _, skey, t, i = q.data.split("_")
    c = temp.SEARCH.get(skey)
    if not _owner(q, c):
        return await q.answer("Ye search aapka nahi hai / expire ho gaya.", show_alert=True)
    val = {"q": C.QUALITIES, "l": list(C.LANGUAGES), "s": C.SEASONS}[t][int(i)]
    c["f"] = (c.get("f", "") + " " + val).strip() if t != "l" else (c.get("f", "") + " " + C.LANGUAGES[val]).strip()
    r = await file_results(skey, 0)
    try:
        await q.message.edit_text(r[0], reply_markup=r[1], disable_web_page_preview=True)
    except Exception:
        pass
    await q.answer(f"Filter: {val}")


@Client.on_callback_query(filters.regex(r"^fc_"))
async def f_clear(client, q):
    skey = q.data[3:]
    c = temp.SEARCH.get(skey)
    if not _owner(q, c):
        return await q.answer("Expire ho gaya.", show_alert=True)
    c["f"] = ""
    r = await file_results(skey, 0)
    await q.message.edit_text(r[0], reply_markup=r[1], disable_web_page_preview=True)
    await q.answer()


@Client.on_callback_query(filters.regex(r"^fi_"))
async def f_info(client, q):
    c = temp.SEARCH.get(q.data[3:])
    if not isinstance(c, dict):
        return await q.answer("Expire ho gaya.", show_alert=True)
    res = await tmdb.search(c["q"])
    if not res:
        return await q.answer("TMDB par info nahi mili.", show_alert=True)
    await q.answer()
    await show_results(client, q.message, c["q"], res, False)


# ================= stream / download link (original generate_stream_link) =================
@Client.on_callback_query(filters.regex(r"^stl_"))
async def stream_link(client, q):
    if C.PREMIUM_STREAM_MODE and not await db.is_premium(q.from_user.id) and q.from_user.id not in C.ADMINS:
        return await q.answer("🔒 Stream/Download sirf Premium users ke liye hai. /plan dekho.", show_alert=True)
    if not C.URL:
        return await q.answer("URL env set nahi hai (stream server ke liye zaruri).", show_alert=True)
    d = await F.get_by_sid(q.data[4:])
    if not d:
        return await q.answer("File nahi mili.", show_alert=True)
    try:
        log_msg_ = await client.send_cached_media(C.BIN_CHANNEL, d["_id"])
        name = quote_plus(get_name(log_msg_))
        h = get_hash(log_msg_)
        stream = f"{C.URL}watch/{log_msg_.id}/{name}?hash={h}"
        download = f"{C.URL}{log_msg_.id}/{name}?hash={h}"
        await log_msg_.reply_text(
            f"Link generated for #{q.from_user.id}\nUser: {q.from_user.mention}\nFile: {html.escape(d['file_name'])}",
            quote=True, disable_web_page_preview=True,
            reply_markup=Markup([[Btn("🚀 Fast Download", url=download), Btn("🖥 Watch online", url=stream)]]))
        rows = [[Btn("🚀 Download", url=download), Btn("🖥 Watch", url=stream)]]
        if C.UPDATE_CHNL_LNK:
            rows.append([Btn("📌 Join Updates Channel", url=C.UPDATE_CHNL_LNK)])
        await q.edit_message_reply_markup(Markup(rows))
        await q.answer()
    except Exception as e:
        log.exception("stream link")
        await q.answer(f"⚠️ Stream link error: {e}", show_alert=True)


# ================= request moderation (admin buttons) =================
@Client.on_callback_query(filters.regex(r"^ra_") & A)
async def req_action(client, q):
    _, uid, code = q.data.split("_")
    msgs = {
        "u": "✅ Aapki request upload ho gayi hai! Ab search karke dekho.",
        "n": "🆕 Ye abhi release/available nahi hai.",
        "w": "❗ Request spelling galat thi. Sahi naam ke saath dobara bhejo.",
        "a": "♻️ Ye pehle se available hai — sahi naam se search karo.",
        "x": "🚫 Ye abhi kisi source par available nahi hai.",
        "h": "🇮🇳 Ye Hindi me available nahi hai.",
    }
    try:
        await client.send_message(int(uid), msgs[code])
    except Exception:
        pass
    await q.message.edit_text(q.message.text.html + f"\n\n— Admin action: <b>{msgs[code][:2]}</b>")
    await q.answer("User ko bata diya.")
