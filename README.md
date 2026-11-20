# 🎬 TrailerBot — Files + TMDB Trailer + Apna Content + Ads se Kamai

User movie/series ka naam bhejta hai → bot **TMDB** se poster, rating, cast, **trailer** dikhata hai (koi movie file nahi).
**📖 Read Now** dabane par aapka daala hua padhne wala content milta hai — us se pehle **shortener (ads) verify** hota hai = aapki kamai.

## Folder structure
```
bot.py  config.py  requirements.txt  Dockerfile  Procfile  .env.sample  README.md
core/     db.py  tmdb.py  flow.py  helpers.py  files.py  fonts.py   (engine)
plugins/  start.py  search.py  files.py  content.py  premium.py  admin.py
          groups.py  extras.py  tools.py  font.py                   (commands)
stream/   route.py  custom_dl.py  clients.py  render_template.py ...  (stream/download web server)
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
`TWO_VERIFY_GAP` (sec, default 1200), `THREE_VERIFY_GAP` (54000), `VERIFY_VALID` (ek verify kitne sec chale, default 86400 = 24 ghante; 3600 = 1 ghanta), `VERIFY_MIDNIGHT=True` (original jaisa: raat 12 baje IST tak valid), `MIN_VERIFY_TIME` (bypass guard, default 10), `TUTORIAL` (how-to-verify link)

**Optional:** `AUTH_CHANNELS` (force-sub, space se IDs), `AUTH_REQ_CHANNELS` (join-request force-sub), `PREMIUM_LOGS`, `REQST_CHANNEL`,
`QR_CODE` (image link), `OWNER_UPI_ID`, `OWNER_LNK`, `TRIAL_TIME` (e.g. `1hour`; khali = trial band), `PICS` (start photo links),
`MOVIE_UPDATE_CHANNEL` (naya content add hote hi yahan auto post; `MOVIE_UPDATE_NOTIFICATION=True`), `MELCOW_NEW_USERS` + `MELCOW_PHOTO` (group welcome), `IMGBB_API_KEY` (/telegraph ke liye, imgbb.com se free), `REFER_POINTS` (10) `REFER_TARGET` (100) `REFER_PREMIUM` (1month), `TUTORIAL_2` `TUTORIAL_3`, `CARD_TEMPLATE`, `CONTENT_CAPTION`,
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

## 6) Commands
**Users:** `/start /trending /movies /series /trendlist(/top_search) /request /plan /myplan /refer /redeem /font /telegraph(/img,/cup) /id /info /stickerid /ping(/alive) /system /help /group_cmd`

**Content (admin):** `/addcontent /delcontent /contents /demand /movie_update on|off /del_msg`
**Files (admin):** `/setskip /delete /deleteall /deletefiles` + forward/link = index

**Admin:** `/stats /users /chats /broadcast /grp_broadcast /send` (reply karke) • `/ban /unban /disable /enable /leave /invite /clear_junk /junk_group`
`/add_premium id 1month /remove_premium /get_premium /premium_users /add_redeem 1day 5 /trial_reset` • `/pm_search on|off /resetallgroup /delreq /logs /restart /set_commands /admin_cmd`

**Settings — group admin group me, ya bot admin PM me (global):**
`/settings` (toggle panel) • `/verify on|off` • `/set_shortner site api` (`_2`, `_3`) • `/set_time 1200` `/set_time_2 54000` `/set_time valid 86400` `/set_time midnight on|off`
`/set_tutorial link` (`_2`, `_3`) • `/set_template` • `/set_caption` • `/set_fsub ids` • `/set_log_channel id` • `/reset_group`
PM se group manage: group me `/connect` (ya `/reload`, `/details`), PM me `/connections` se active group chuno.
Bina connect ke bot admin PM me jo set kare wo **global** hota hai; group ka apna set ho to wahi us group se aane walon par lagta hai.

**Card template placeholders:** `{title} {year} {rating} {votes} {genres} {runtime} {lang} {director} {cast} {overview} {tagline} {status} {trailer} {imdb} {seasons}`
Example: `/set_template 🎬 <b>{title}</b> ({year})\n⭐ {rating}\n{overview}`
**Content caption:** `/set_caption {title} — Join @mychannel` (media content par lagta hai).

(Shortener, verify, gaps wagairah commands se badalte hi turant lagu — redeploy nahi chahiye.)

## 6b) Files (index + search + stream) — original DreamXBotz ka logic
Education channel ke liye: apne PDFs/videos/notes ko search-able banao. **Sirf wahi files index karo jinka aapke paas haq/permission ho.**
- **Auto index:** `CHANNELS` env me channel ID daalo (bot admin) → us channel me aane wali har file (document/video/audio) DB me save.
- **Manual index (purani files):** bot ko PM me channel ki **last message forward** karo ya uska link bhejo (`https://t.me/c/123/456`) → **Yes** → progress bar ke saath index. Pehle `/setskip 0` (kahan se shuru). Non-admin bheje to `INDEX_REQ_CHANNEL` me accept/reject aata hai.
- **Search:** user naam likhe → files ki list (size ke saath), **Quality / Language / Season** filter, pagination, **Send All**, aur ℹ️ Info & Trailer (TMDB). Pehle files dhundhta hai, na mile to TMDB card dikhata hai.
- **Verify/ads, force-sub, premium, auto-delete, protect, caption** — files par bhi wahi lagte hain (ek hi flow).
- **Delete:** `/delete` (file par reply), `/deletefiles keyword`, `/deleteall`, ya `DELETE_CHANNELS` me file daalo = DB se delete.
- **Stream/Download:** `STREAM_MODE=True`, `URL=https://aapka-app-link` (zaruri), `BIN_CHANNEL` (private channel, bot admin). File ke neeche 🚀 Download / 🖥 Watch Online button. `PREMIUM_STREAM_MODE=True` = sirf premium. Speed ke liye extra bots: `MULTI_TOKEN1`, `MULTI_TOKEN2` … (bot tokens).
- **Multiple DB:** `MULTIPLE_DB=True` + `DATABASE_URI2` → pehla DB `DB_SIZE_LIMIT_MB` (407) ka hone par doosre me save.
- **Env:** `CHANNELS` `DELETE_CHANNELS` `BIN_CHANNEL` `INDEX_REQ_CHANNEL` `COLLECTION_NAME` `USE_CAPTION_FILTER` `SAVE_CAPTION` `MAX_B_TN` (files per page) `FILE_SEARCH` `FILE_TMDB_MATCH` `CUSTOM_FILE_CAPTION` (`{file_name} {file_size} {file_caption}`) `AUTH_USERS` (khali = sab) `STREAM_MODE` `PREMIUM_STREAM_MODE`
- **Bad words:** `config.py` me `BAD_WORDS` — file name se ye shabd aur `[`, `@`, `www.` se shuru hone wale shabd hat jate hain.
- **Update channel:** `MOVIE_UPDATE_CHANNEL` set ho to nayi file aate hi post (ek title ek baar). `FILE_TMDB_MATCH=True` = TMDB poster card (movie channel ke liye).
- **Requests:** `/request` ya "Request Admin" → `REQST_CHANNEL` me admin buttons (Uploaded / Not released / Wrong spelling / Already available) → user ko auto reply.

## 6c) /start look (original jaisa)
`/start` par: bada **emoji reaction** (`EMOJI_MODE=True`) → ⏳ animation → **random photo** (`PICS`, space se kai links) + time ke hisaab se Good Morning/Afternoon/Evening/Night + buttons (Add me to Group / Help / About / Top Searching / Upgrade).
Photos: `PICS` (start), `FSUB_PICS` (force-sub), `VERIFY_IMG` (verify complete), `NOR_IMG` (kuch nahi mila), `SPELL_IMG` (suggestions). Khali chhodo to original wale default photo lagte hain; apni photo ka link daal sakte ho. `TIMEZONE` se greeting ka time.

## 7) User flow
Naam bhejo → results → title → card (poster, rating, ▶️ Trailer, ⭐ IMDb, 📖 Read Now) → Read Now → force-sub check → shortener verify (premium users skip) → content, auto-delete ke saath.
Groups me bhi chalta hai (result buttons PM me khulte hain).
Premium: Telegram Stars (`STAR_PREMIUM_PLANS` config.py me), UPI/QR, redeem codes, free trial.

## Note
- Original ke hardcoded API_ID, API_HASH, channel IDs aur imgbb key hata di gayi hain — sab apni daalo.
- Original ki styled (small-caps) texts/menus aur kuch cosmetic cheezein simple rakhi hain. Logic wahi hai.
- Referral me sirf **naye** users count hote hain (fraud se bachne ke liye).
