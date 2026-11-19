# 🎬 TrailerBot — TMDB Trailer + Apna Content + Ads se Kamai

User movie/series ka naam bhejta hai → bot **TMDB** se poster, rating, cast, **trailer** dikhata hai (koi movie file nahi).
**📖 Read Now** dabane par aapka daala hua padhne wala content milta hai — us se pehle **shortener (ads) verify** hota hai = aapki kamai.

## Folder structure
```
bot.py  config.py  requirements.txt  Dockerfile  Procfile  .env.sample  README.md
core/     db.py  tmdb.py  flow.py  helpers.py     (engine)
plugins/  start.py  search.py  content.py  premium.py  admin.py   (commands)
```

## 1) Kya-kya chahiye (ek baar)
| Cheez | Kahan se |
|---|---|
| API_ID, API_HASH | https://my.telegram.org → API development tools |
| BOT_TOKEN | @BotFather → /newbot |
| DATABASE_URI | MongoDB Atlas (free) → Connect → Drivers → URI (password daalna na bhoolo, Network Access me 0.0.0.0/0) |
| TMDB_API_KEY | https://www.themoviedb.org/settings/api (free, "API Key (v3)") |
| Shortener | Koi bhi (gplinks, shrinkme, etc.) ka site domain + API key |

## 2) Telegram channels banao
1. **LOG_CHANNEL** (private) — bot ko admin banao. Naye users, verify, missing-content alerts yahan aate hain.
2. **CONTENT_CHANNEL** (private) — bot ko admin banao (post karne ki permission). Aapka content yahin store hota hai.
3. (Optional) **REQST_CHANNEL**, force-sub channels.
Channel ID nikalne ke liye channel ka koi message @userinfobot / @RawDataBot ko forward karo (`-100…` wali ID).

## 3) Environment variables
**Zaruri:** `API_ID` `API_HASH` `BOT_TOKEN` `ADMINS` (aapki Telegram ID, space se kai) `DATABASE_URI` `TMDB_API_KEY` `LOG_CHANNEL` `CONTENT_CHANNEL`

**Kamai (ads):**
`IS_VERIFY=True`, `SHORTENER_WEBSITE`, `SHORTENER_API` (+ `…2`, `…3` optional: 2nd/3rd verify ke liye alag shortener),
`TWO_VERIFY_GAP` (sec, default 1200), `THREE_VERIFY_GAP` (54000), `VERIFY_VALID` (ek verify kitne sec chale, default 86400), `MIN_VERIFY_TIME` (bypass guard, default 10), `TUTORIAL` (how-to-verify link)

**Optional:** `AUTH_CHANNELS` (force-sub, space se IDs), `AUTH_REQ_CHANNELS` (join-request force-sub), `PREMIUM_LOGS`, `REQST_CHANNEL`,
`QR_CODE` (image link), `OWNER_UPI_ID`, `OWNER_LNK`, `TRIAL_TIME` (e.g. `1hour`; khali = trial band), `PICS` (start photo links),
`GRP_LNK`, `UPDATE_CHNL_LNK`, `AUTO_DELETE` / `DELETE_TIME`, `PROTECT_CONTENT`, `PM_SEARCH`, `GROUP_SEARCH`, `LANDSCAPE_POSTER`, `TMDB_LANG` (`en-US` / `hi-IN`),
`URL` (Heroku/Koyeb/Render app URL — keep-alive), `PORT` (default 8080)

`.env.sample` ko `.env` naam se copy karke bhi bhar sakte ho (local run), ya hosting ke Environment/Config Vars me daalo.

## 4) Deploy
**VPS / local:** `pip install -r requirements.txt` → env set → `python3 bot.py`
**Docker (Koyeb/Render/Railway):** repo upload karo, Dockerfile auto use hoga, env vars daalo.
**Heroku:** Procfile ready hai (`web: python3 bot.py`), `URL` me app ka link daalo.

## 5) Content kaise jodna hai (aapka kaam)
1. Apna content (text/link/photo/pdf/post) bot ko **PM me bhejo** (ya kahin bhi bhejo).
2. Us message ko **reply** karke: `/addcontent Pushpa 2`
3. Bot TMDB se options dikhayega → sahi title chuno → ho gaya. (ya seedha `/addcontent m12345`, series ke liye `t1399` — id TMDB URL me hoti hai)
4. Ek title par kai baar add karo → sab ek saath milega.
Content search results me 📖 ke saath upar dikhta hai. `/demand` se pata chalta hai kis title ki demand hai par content nahi — pehle wahi banao.

## 6) Admin commands
`/addcontent /delcontent /contents /demand` • `/stats /users /chats` • `/broadcast /grp_broadcast /send` (reply karke)
`/ban /unban /disable /enable /leave` • `/add_premium id 1month` `/remove_premium /premium_users /add_redeem 1day 5 /trial_reset`
`/settings /verify on|off /set_shortner site api` (`_2`, `_3`) `/set_time 1200` `/set_time_2 54000` `/set_time valid 86400` `/set_tutorial link /pm_search on|off /group_search on|off /auto_delete on|off`
`/delreq /logs /restart`
(Shortener, verify on/off, gaps wagairah commands se badalte hi turant lagu — redeploy nahi chahiye.)

## 7) User flow
Naam bhejo → results → title → card (poster, rating, ▶️ Trailer, ⭐ IMDb, 📖 Read Now) → Read Now → force-sub check → shortener verify (premium users skip) → content, auto-delete ke saath.
Groups me bhi chalta hai (result buttons PM me khulte hain).
Premium: Telegram Stars (`STAR_PREMIUM_PLANS` config.py me), UPI/QR, redeem codes, free trial.

## Note
- Is bot me movie/video files nahi hain, na indexing/streaming. Sirf TMDB info + aapka content.
- Original DreamXBotz ke hardcoded API_ID/channel IDs hata diye gaye hain — sab apni daalo.
- Original ke removed extras: file indexing/stream server, font-style tool, telegraph uploader, per-group settings (ab settings global hain).
