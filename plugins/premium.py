import asyncio
import html
import random
import string

from pyrogram import Client, filters
from pyrogram.types import (InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup,
                            LabeledPrice, PreCheckoutQuery)

import config as C
from core.db import db, now
from core.helpers import seconds, ist, log_msg


def plan_kb():
    rows = [[Btn(f"⭐ {amt} Stars — {t}", callback_data=f"buy_{amt}")] for amt, t in C.STAR_PREMIUM_PLANS.items()]
    if C.OWNER_UPI_ID or C.QR_CODE:
        rows.append([Btn("💳 UPI se kharido", callback_data="upi")])
    if C.TRIAL_TIME:
        rows.append([Btn("🎁 Free Trial", callback_data="trial")])
    rows.append([Btn("🚫 Close", callback_data="close")])
    return Markup(rows)


PLAN_TXT = ("💎 <b>Premium Plan</b>\n\n✅ Koi verify / ads nahi\n✅ Direct content access\n✅ Fast & priority\n\n"
            "Plan choose karo 👇")


@Client.on_message(filters.command("plan") & filters.private)
async def plan(client, m):
    await m.reply_text(PLAN_TXT, reply_markup=plan_kb())


@Client.on_callback_query(filters.regex(r"^plan$"))
async def plan_cb(client, q):
    await q.answer()
    await client.send_message(q.from_user.id, PLAN_TXT, reply_markup=plan_kb())


@Client.on_callback_query(filters.regex(r"^upi$"))
async def upi(client, q):
    t = f"💳 <b>UPI:</b> <code>{C.OWNER_UPI_ID}</code>\n\nPayment ka screenshot owner ko bhejo — premium turant active hoga."
    kb = Markup([[Btn("📨 Send Screenshot", url=C.OWNER_LNK)]])
    await q.answer()
    if C.QR_CODE:
        try:
            return await client.send_photo(q.from_user.id, C.QR_CODE, caption=t, reply_markup=kb)
        except Exception:
            pass
    await client.send_message(q.from_user.id, t, reply_markup=kb)


@Client.on_callback_query(filters.regex(r"^buy_\d+$"))
async def buy(client, q):
    amt = int(q.data.split("_")[1])
    if amt not in C.STAR_PREMIUM_PLANS:
        return await q.answer("Invalid plan", show_alert=True)
    try:
        await client.send_invoice(
            chat_id=q.from_user.id, title="Premium Subscription",
            description=f"{amt} Stars = Premium {C.STAR_PREMIUM_PLANS[amt]}",
            payload=f"prem_{amt}", currency="XTR",
            prices=[LabeledPrice(label="Premium", amount=amt)])
        await q.answer()
    except Exception as e:
        await q.answer("Payment error, baad me try karo.", show_alert=True)


@Client.on_pre_checkout_query()
async def pre_checkout(client, q: PreCheckoutQuery):
    ok = q.payload.startswith("prem_")
    await q.answer(success=ok, error_message=None if ok else "Invalid purchase")


@Client.on_message(filters.successful_payment)
async def paid(client, m):
    amt = int(m.successful_payment.total_amount)
    t = C.STAR_PREMIUM_PLANS.get(amt)
    if not t:
        return await m.reply_text("⚠️ Plan match nahi hua, owner se contact karo.")
    exp = await db.add_premium(m.from_user.id, seconds(t))
    await m.reply_text(f"✅ Premium active!\nPlan: {t}\nExpiry: {ist(exp)}")
    await log_msg(client, f"#Premium_Stars\n👤 {m.from_user.mention} <code>{m.from_user.id}</code>\n⭐ {amt} | {t}\nExpiry {ist(exp)}", C.PREMIUM_LOGS)


@Client.on_message(filters.command("myplan"))
async def myplan(client, m):
    p = await db.get_premium(m.from_user.id)
    if p and p.get("expiry_time") and p["expiry_time"] > now():
        return await m.reply_text(f"💎 <b>Premium active</b>\nExpiry: {ist(p['expiry_time'])}")
    await m.reply_text("❌ Aapke paas premium nahi hai. /plan dekho.")


# ---------- free trial ----------
@Client.on_callback_query(filters.regex(r"^trial$"))
async def trial(client, q):
    if not C.TRIAL_TIME:
        return await q.answer("Trial band hai.", show_alert=True)
    u = await db.get_user(q.from_user.id)
    if u.get("trial_used"):
        return await q.answer("Aap trial pehle le chuke ho.", show_alert=True)
    exp = await db.add_premium(q.from_user.id, seconds(C.TRIAL_TIME))
    await db.set_user(q.from_user.id, trial_used=True)
    await q.answer()
    await client.send_message(q.from_user.id, f"🎁 Free trial active! Expiry: {ist(exp)}")


@Client.on_message(filters.command("trial_reset") & filters.user(C.ADMINS))
async def trial_reset(client, m):
    if len(m.command) == 2 and m.command[1].isdigit():
        await db.set_user(int(m.command[1]), trial_used=False)
    else:
        await db.users.update_many({}, {"$set": {"trial_used": False}})
    await m.reply_text("✅ Trial reset.")


# ---------- admin ----------
@Client.on_message(filters.command("add_premium") & filters.user(C.ADMINS))
async def add_premium(client, m):
    if len(m.command) != 3 or not m.command[1].isdigit() or not seconds(m.command[2]):
        return await m.reply_text("Use: <code>/add_premium user_id 1month</code>\nUnits: s, min, hour, day, month, year")
    uid = int(m.command[1])
    exp = await db.add_premium(uid, seconds(m.command[2]))
    await m.reply_text(f"✅ <code>{uid}</code> premium till {ist(exp)}")
    try:
        await client.send_message(uid, f"🎉 Aapko premium mila! Expiry: {ist(exp)}")
    except Exception:
        pass
    await log_msg(client, f"#Premium_Added <code>{uid}</code> {m.command[2]}", C.PREMIUM_LOGS)


@Client.on_message(filters.command("remove_premium") & filters.user(C.ADMINS))
async def remove_premium(client, m):
    if len(m.command) != 2 or not m.command[1].isdigit():
        return await m.reply_text("Use: <code>/remove_premium user_id</code>")
    await db.remove_premium(int(m.command[1]))
    await m.reply_text("✅ Removed.")


@Client.on_message(filters.command("premium_users") & filters.user(C.ADMINS))
async def premium_users(client, m):
    rows = await db.all_premium()
    if not rows:
        return await m.reply_text("Koi premium user nahi.")
    await m.reply_text("<b>💎 Premium users</b>\n\n" + "\n".join(f"<code>{x['id']}</code> — {ist(x['expiry_time'])}" for x in rows))


@Client.on_message(filters.command("add_redeem") & filters.user(C.ADMINS))
async def add_redeem(client, m):
    if len(m.command) != 3 or not m.command[2].isdigit() or not seconds(m.command[1]):
        return await m.reply_text("Use: <code>/add_redeem 1day 5</code> (duration, kitne codes)")
    codes = []
    for _ in range(min(int(m.command[2]), 50)):
        c = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        await db.add_code(c, m.command[1])
        codes.append(f"<code>/redeem {c}</code>")
    await m.reply_text(f"🎟 <b>Codes ({m.command[1]})</b>\n\n" + "\n".join(codes))


@Client.on_message(filters.command("redeem"))
async def redeem(client, m):
    if len(m.command) != 2:
        return await m.reply_text("Use: <code>/redeem CODE</code>")
    c = await db.use_code(m.command[1])
    if not c:
        return await m.reply_text("❌ Code galat ya expire hai.")
    exp = await db.add_premium(m.from_user.id, seconds(c["duration"]))
    await m.reply_text(f"🎉 Premium active! Expiry: {ist(exp)}")
    await log_msg(client, f"#Redeem 👤 {m.from_user.mention} <code>{m.from_user.id}</code> {c['duration']}", C.PREMIUM_LOGS)


# ---------- expiry notifier (bot.py se start hota hai) ----------
async def expiry_loop(client):
    while True:
        try:
            for p in await db.expired():
                await db.remove_premium(p["id"])
                try:
                    await client.send_message(p["id"], "⌛ Aapka premium expire ho gaya. Dobara lene ke liye /plan dabao.")
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(60)
