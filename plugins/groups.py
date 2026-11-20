"""Per-group settings: har group apna shortener/verify/template/fsub/log set kar sakta hai.
PM me /connect se group jodkar wahin se bhi manage ho sakta hai. Bot admin PM me (bina connect) = global settings."""
import html

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup

import config as C
from core.db import db
from core.helpers import settings, is_admin, readable

GROUP = (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)


async def target(client, m):
    """(ok, gid). gid=None => global settings (sirf bot admin, PM me)."""
    uid = m.from_user.id
    if m.chat.type in GROUP:
        ok = uid in C.ADMINS or await is_admin(client, m.chat.id, uid)
        return ok, m.chat.id
    ag = (await db.get_user(uid)).get("active_grp")
    if ag:
        if uid in C.ADMINS or await is_admin(client, ag, uid):
            return True, ag
        return False, ag
    return (uid in C.ADMINS), None


async def save(gid, key, value):
    if gid:
        await db.set_group_setting(gid, key, value)
    else:
        await db.set_setting(key, value)


NO = "⚠️ Ye command group admin ke liye hai. Group me use karo, ya PM me pehle <code>/connect</code> se group jodo."


def _cmd(names, usage, key, cast=None, fixed_key=None):
    """Simple 'ek value set' command banane ka helper."""
    @Client.on_message(filters.command(names))
    async def h(client, m):
        ok, gid = await target(client, m)
        if not ok:
            return await m.reply_text(NO)
        if len(m.command) < 2:
            return await m.reply_text(f"Use: <code>{usage}</code>")
        val = " ".join(m.command[1:])
        k = fixed_key.get(m.command[0].lower(), key) if fixed_key else key
        if cast:
            try:
                val = cast(val)
            except Exception:
                return await m.reply_text(f"Use: <code>{usage}</code>")
        await save(gid, k, val)
        await m.reply_text(f"✅ <b>{k}</b> set ho gaya{'' if gid else ' (global)'}.")
    return h


set_tutorial = _cmd(["set_tutorial", "set_tutorial_2", "set_tutorial_3"], "/set_tutorial https://t.me/link", "tutorial",
                    fixed_key={"set_tutorial": "tutorial", "set_tutorial_2": "tutorial2", "set_tutorial_3": "tutorial3"})
set_template = _cmd(["set_template"], "/set_template {title} ({year}) ⭐{rating}\\n{overview}  (placeholders: title year rating votes genres runtime lang director cast overview tagline status trailer imdb)", "template")
set_caption = _cmd(["set_caption"], "/set_caption {title} — Join @channel", "caption")
set_log_channel = _cmd(["set_log_channel"], "/set_log_channel -100xxxxxxxxxx", "log", cast=int)
set_fsub = _cmd(["set_fsub"], "/set_fsub -100111 -100222  (khali karne ke liye /set_fsub 0)", "fsub",
                cast=lambda v: [int(x) for x in v.split() if x != "0"] or None)


def _shortener(n):
    api_k, site_k = {1: ("api", "site"), 2: ("api2", "site2"), 3: ("api3", "site3")}[n]
    cmd = "set_shortner" + ("" if n == 1 else f"_{n}")

    @Client.on_message(filters.command(cmd))
    async def h(client, m):
        ok, gid = await target(client, m)
        if not ok:
            return await m.reply_text(NO)
        if len(m.command) != 3:
            return await m.reply_text(f"Use: <code>/{cmd} example.com api_key</code>")
        await save(gid, site_k, m.command[1])
        await save(gid, api_k, m.command[2])
        await m.reply_text(f"✅ Shortener {n} set: {m.command[1]}{'' if gid else ' (global)'}")
    globals()[f"set_shortner_{n}"] = h


for _n in (1, 2, 3):
    _shortener(_n)


@Client.on_message(filters.command(["set_time", "set_time_2"]))
async def set_time(client, m):
    ok, gid = await target(client, m)
    if not ok:
        return await m.reply_text(NO)
    a = m.command
    if len(a) == 2 and a[1].isdigit():
        key = "gap2" if a[0] == "set_time" else "gap3"
        await save(gid, key, int(a[1]))
        return await m.reply_text(f"✅ {key} = {a[1]} sec")
    if len(a) == 3 and a[1] == "valid" and a[2].isdigit():
        await save(gid, "valid", int(a[2]))
        return await m.reply_text(f"✅ valid = {a[2]} sec")
    if len(a) == 3 and a[1] == "midnight" and a[2].lower() in ("on", "off"):
        await save(gid, "midnight", a[2].lower() == "on")
        return await m.reply_text(f"✅ Midnight mode: {a[2].upper()} (ON = raat 12 baje IST tak valid)")
    await m.reply_text("Use:\n<code>/set_time 1200</code> (2nd verify gap)\n<code>/set_time_2 54000</code> (3rd verify gap)\n<code>/set_time valid 86400</code> (verify kitni der valid, seconds)\n<code>/set_time midnight on</code> (raat 12 baje tak valid, original jaisa)")


@Client.on_message(filters.command("verify"))
async def verify(client, m):
    ok, gid = await target(client, m)
    if not ok:
        return await m.reply_text(NO)
    if len(m.command) < 2 or m.command[1].lower() not in ("on", "off"):
        return await m.reply_text("Use: <code>/verify on</code> ya <code>/verify off</code>")
    await save(gid, "is_verify", m.command[1].lower() == "on")
    await m.reply_text(f"✅ Verify: {m.command[1].upper()}")


# ---------------- /settings panel ----------------
TOG = {"v": ("is_verify", "Verify (ads)"), "ad": ("auto_delete", "Auto delete"), "pc": ("protect", "Protect content"),
       "wl": ("welcome", "Welcome msg"), "gs": ("group_search", "Search"),
       "sc": ("spell_check", "Spell check"), "im": ("tmdb", "Info button"),
       "mb": ("max_btn", "Max buttons (10)"), "bt": ("button", "Button mode")}


async def panel(gid):
    s = await settings(gid)
    sh = lambda a, w: f"{w} ✅" if a and w else "—"
    title = "Global (bot)" if not gid else f"Group <code>{gid}</code>"
    text = (f"<b>⚙️ Settings — {title}</b>\n\n"
            f"Shortener 1: {sh(s['api'], s['site'])}\nShortener 2: {sh(s['api2'], s['site2'])}\nShortener 3: {sh(s['api3'], s['site3'])}\n"
            f"Verify valid: {'midnight IST' if s['midnight'] else readable(s['valid'])} | 2nd gap: {readable(s['gap2'])} | 3rd gap: {readable(s['gap3'])}\n"
            f"Tutorial: {s['tutorial'] or '—'}\nFsub: {s['fsub'] or '(global)'}\nLog channel: <code>{s['log']}</code>\n"
            f"Template: {'custom ✅' if s['template'] else 'default'} | Caption: {'custom ✅' if s['caption'] else '—'}\n\n"
            "<i>Commands: /set_shortner /set_shortner_2 /set_shortner_3 /set_time /set_tutorial /set_template /set_caption /set_fsub /set_log_channel /reset_group</i>")
    rows = [[Btn(f"{label}: {'✅ ON' if s[k] else '❌ OFF'}", callback_data=f"gs_{gid or 0}_{code}")] for code, (k, label) in TOG.items()]
    rows.append([Btn("🚫 Close", callback_data="close")])
    return text, Markup(rows)


@Client.on_message(filters.command("settings"))
async def settings_cmd(client, m):
    ok, gid = await target(client, m)
    if not ok:
        return await m.reply_text(NO)
    if m.chat.type in GROUP:      # original: settings yahin kholo ya PM me
        return await m.reply_text(
            "⚙️ Settings kahan kholni hain?",
            reply_markup=Markup([[Btn("👤 Open in PM", callback_data=f"opnsetpm_{gid}"), Btn("👥 Open here", callback_data=f"opnsetgrp_{gid}")]]))
    text, kb = await panel(gid)
    await m.reply_text(text, reply_markup=kb, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^opnset(pm|grp)_"))
async def open_settings(client, q):
    kind, gid = q.data[6:].split("_", 1)[0], int(q.data.split("_", 1)[1])
    uid = q.from_user.id
    if not (uid in C.ADMINS or await is_admin(client, gid, uid)):
        return await q.answer("Sirf group admin.", show_alert=True)
    text, kb = await panel(gid)
    if kind == "grp":
        await q.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        return await q.answer()
    try:
        await db.connect_group(gid, uid)
        await db.set_user(uid, active_grp=gid)
        await client.send_message(uid, text, reply_markup=kb, disable_web_page_preview=True)
        await q.message.edit_text("✅ Settings aapke PM me bhej di gayi.")
        await q.answer()
    except Exception:
        await q.answer("Pehle bot ko PM me /start karo, phir dobara try karo.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^gs_"))
async def toggle(client, q):
    _, gid, code = q.data.split("_")
    gid = int(gid) or None
    uid = q.from_user.id
    ok = uid in C.ADMINS if not gid else (uid in C.ADMINS or await is_admin(client, gid, uid))
    if not ok:
        return await q.answer("Sirf admin ke liye.", show_alert=True)
    k, label = TOG[code]
    cur = (await settings(gid))[k]
    await save(gid, k, not cur)
    text, kb = await panel(gid)
    try:
        await q.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass
    await q.answer(f"{label}: {'ON' if not cur else 'OFF'}")


@Client.on_message(filters.command("reset_group"))
async def reset_group(client, m):
    ok, gid = await target(client, m)
    if not ok or not gid:
        return await m.reply_text(NO)
    await db.reset_group_settings(gid)
    await m.reply_text("✅ Group settings default par aa gayi.")


@Client.on_message(filters.command("resetallgroup") & filters.user(C.ADMINS))
async def resetall(client, m):
    n = await db.reset_group_settings()
    await m.reply_text(f"✅ {n} groups ki settings reset.")


# ---------------- connections (PM se group manage) ----------------
@Client.on_message(filters.command(["connect", "reload", "details"]))
async def connect(client, m):
    uid = m.from_user.id
    if m.chat.type in GROUP:
        if not (uid in C.ADMINS or await is_admin(client, m.chat.id, uid)):
            return await m.reply_text("⚠️ Sirf group admin.")
        await db.connect_group(m.chat.id, uid)
        await db.set_user(uid, active_grp=m.chat.id)
        return await m.reply_text("✅ Group aapke PM se connect ho gaya. Ab PM me /settings aur /set_* commands chalenge.")
    if len(m.command) < 2:
        return await m.reply_text("Group me <code>/connect</code> likho, ya PM me <code>/connect group_id</code>")
    try:
        gid = int(m.command[1])
        if not (uid in C.ADMINS or await is_admin(client, gid, uid)):
            return await m.reply_text("⚠️ Aap us group ke admin nahi ho.")
        chat = await client.get_chat(gid)
        await db.connect_group(gid, uid)
        await db.set_user(uid, active_grp=gid)
        await m.reply_text(f"✅ <b>{html.escape(chat.title)}</b> connected & active.")
    except Exception:
        await m.reply_text("❌ Invalid group id ya bot us group me nahi hai.")


@Client.on_message(filters.command("connections") & filters.private)
async def connections(client, m):
    gs = await db.connected(m.from_user.id)
    ag = (await db.get_user(m.from_user.id)).get("active_grp")
    rows = []
    for g in gs:
        try:
            t = (await client.get_chat(g)).title
        except Exception:
            t = str(g)
        rows.append([Btn(f"{'🟢 ' if g == ag else ''}{t}", callback_data=f"cn_{g}"), Btn("❌", callback_data=f"dc_{g}")])
    if m.from_user.id in C.ADMINS:
        rows.append([Btn(f"{'🟢 ' if not ag else ''}🌐 Global settings", callback_data="cn_0")])
    if not rows:
        return await m.reply_text("Koi group connected nahi. Group me <code>/connect</code> likho.")
    await m.reply_text("<b>🔗 Connected groups</b>\nActive group par aapke settings commands chalte hain.", reply_markup=Markup(rows))


@Client.on_callback_query(filters.regex(r"^cn_"))
async def cn(client, q):
    g = int(q.data[3:])
    await db.set_user(q.from_user.id, active_grp=g or None)
    await q.answer("Active group set ✅" if g else "Global mode ✅")
    await q.message.delete()


@Client.on_callback_query(filters.regex(r"^dc_"))
async def dc(client, q):
    await db.disconnect_group(int(q.data[3:]), q.from_user.id)
    await q.answer("Disconnected")
    await q.message.delete()
