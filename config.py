import re
from os import environ

_id = re.compile(r"^-?\d+$")


def _bool(v, d=False):
    v = str(environ.get(v, d)).lower()
    return v in ("true", "yes", "1", "on", "y")


def _ids(key, default=""):
    return [int(x) for x in environ.get(key, default).split() if _id.match(x)]


# ---------- Telegram ----------
API_ID = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")
SESSION = environ.get("SESSION", "trailerbot")
ADMINS = _ids("ADMINS")

# ---------- Database ----------
DATABASE_URI = environ.get("DATABASE_URI", "")
DATABASE_NAME = environ.get("DATABASE_NAME", "trailerbot")

# ---------- TMDB ----------
TMDB_API_KEY = environ.get("TMDB_API_KEY", "")
TMDB_LANG = environ.get("TMDB_LANG", "en-US")          # overview language
LANDSCAPE_POSTER = _bool("LANDSCAPE_POSTER", False)    # True = backdrop use hoga

# ---------- Channels ----------
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))
CONTENT_CHANNEL = int(environ.get("CONTENT_CHANNEL", "0"))   # private channel: yahan aapka padhne wala content store hota hai
PREMIUM_LOGS = int(environ.get("PREMIUM_LOGS", str(LOG_CHANNEL)))
REQST_CHANNEL = int(environ.get("REQST_CHANNEL", str(LOG_CHANNEL)))
AUTH_CHANNELS = _ids("AUTH_CHANNELS")          # normal force-sub
AUTH_REQ_CHANNELS = _ids("AUTH_REQ_CHANNELS")  # join-request force-sub

# ---------- Verify / Ads (shortener) ----------
IS_VERIFY = _bool("IS_VERIFY", False)
SHORTENER_API = environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = environ.get("SHORTENER_WEBSITE", "")
SHORTENER_API2 = environ.get("SHORTENER_API2", "")
SHORTENER_WEBSITE2 = environ.get("SHORTENER_WEBSITE2", "")
SHORTENER_API3 = environ.get("SHORTENER_API3", "")
SHORTENER_WEBSITE3 = environ.get("SHORTENER_WEBSITE3", "")
VERIFY_VALID = int(environ.get("VERIFY_VALID", "86400"))      # ek verify kitne sec valid
TWO_VERIFY_GAP = int(environ.get("TWO_VERIFY_GAP", "1200"))   # itne sec baad 2nd shortener
THREE_VERIFY_GAP = int(environ.get("THREE_VERIFY_GAP", "54000"))
MIN_VERIFY_TIME = int(environ.get("MIN_VERIFY_TIME", "10"))   # isse jaldi aaya = bypass
TUTORIAL = environ.get("TUTORIAL", "")

# ---------- Premium ----------
QR_CODE = environ.get("QR_CODE", "")
OWNER_UPI_ID = environ.get("OWNER_UPI_ID", "")
OWNER_LNK = environ.get("OWNER_LNK", "https://t.me/")
STAR_PREMIUM_PLANS = {10: "7day", 20: "15day", 40: "1month", 55: "45day", 75: "60day"}
TRIAL_TIME = environ.get("TRIAL_TIME", "")     # e.g. 1hour  (khali = trial band)

# ---------- Misc ----------
PICS = environ.get("PICS", "").split()
GRP_LNK = environ.get("GRP_LNK", "")
UPDATE_CHNL_LNK = environ.get("UPDATE_CHNL_LNK", "")
AUTO_DELETE = _bool("AUTO_DELETE", True)
DELETE_TIME = int(environ.get("DELETE_TIME", "600"))
PROTECT_CONTENT = _bool("PROTECT_CONTENT", False)
PM_SEARCH = _bool("PM_SEARCH", True)
GROUP_SEARCH = _bool("GROUP_SEARCH", True)
PORT = int(environ.get("PORT", "8080"))
URL = environ.get("URL", "")   # Heroku/Koyeb app url (keep-alive ke liye, optional)

# ---------- Extra features ----------
MOVIE_UPDATE_CHANNEL = int(environ.get("MOVIE_UPDATE_CHANNEL", "0"))   # naya content add hone par yahan auto post
MOVIE_UPDATE_NOTIFICATION = _bool("MOVIE_UPDATE_NOTIFICATION", True)
MELCOW_NEW_USERS = _bool("MELCOW_NEW_USERS", False)                    # group me welcome message
MELCOW_PHOTO = environ.get("MELCOW_PHOTO", "")
IMGBB_API_KEY = environ.get("IMGBB_API_KEY", "")                       # /telegraph /img ke liye (imgbb.com se free)
REFER_POINTS = int(environ.get("REFER_POINTS", "10"))                  # ek refer = itne points
REFER_TARGET = int(environ.get("REFER_TARGET", "100"))                 # itne points = premium
REFER_PREMIUM = environ.get("REFER_PREMIUM", "1month")
TUTORIAL_2 = environ.get("TUTORIAL_2", "")
TUTORIAL_3 = environ.get("TUTORIAL_3", "")
CARD_TEMPLATE = environ.get("CARD_TEMPLATE", "")                       # khali = default card; placeholders README me
CONTENT_CAPTION = environ.get("CONTENT_CAPTION", "")                   # content ke saath lagne wala caption ({title})
BOT_COMMANDS = {
    "start": "Start the bot", "trending": "Trending movies/series", "movies": "Latest movies content",
    "series": "Latest series content", "trendlist": "Top searches", "request": "Request a title",
    "plan": "Premium plans", "myplan": "Your premium status", "refer": "Refer & earn premium",
    "redeem": "Redeem a code", "font": "Fancy font styles", "telegraph": "Upload image link",
    "id": "Get Telegram ID", "info": "User info", "settings": "Group settings",
    "connect": "Connect group to PM", "connections": "Your connected groups",
    "alive": "Bot alive check", "help": "All commands",
}
