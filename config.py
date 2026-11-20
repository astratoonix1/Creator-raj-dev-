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
PICS = environ.get("PICS", "https://graph.org/file/56b5deb73f3b132e2bb73.jpg https://graph.org/file/5303692652d91d52180c2.jpg https://graph.org/file/425b6f46efc7c6d64105f.jpg https://graph.org/file/876867e761c6c7a29855b.jpg").split()
GRP_LNK = environ.get("GRP_LNK", "")
UPDATE_CHNL_LNK = environ.get("UPDATE_CHNL_LNK", "")
AUTO_DELETE = _bool("AUTO_DELETE", True)
DELETE_TIME = int(environ.get("DELETE_TIME", "600"))
PROTECT_CONTENT = _bool("PROTECT_CONTENT", False)
PM_SEARCH = _bool("PM_SEARCH", True)
GROUP_SEARCH = _bool("GROUP_SEARCH", True)
PORT = int(environ.get("PORT", "8080"))
URL = environ.get("URL", "")   # app ka public https link (stream + keep-alive ke liye)
if URL and not URL.endswith("/"):
    URL += "/"

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

# ---------- File index / search / stream (original DreamXBotz logic) ----------
CHANNELS = _ids("CHANNELS")                       # in channels me aane wali files auto-index hongi (bot admin ho)
DELETE_CHANNELS = _ids("DELETE_CHANNELS")         # in channels me file daalo = DB se delete
BIN_CHANNEL = int(environ.get("BIN_CHANNEL", str(LOG_CHANNEL)))   # stream/download link ke liye files yahan copy hoti hain
INDEX_REQ_CHANNEL = int(environ.get("INDEX_REQ_CHANNEL", str(LOG_CHANNEL)))
COLLECTION_NAME = environ.get("COLLECTION_NAME", "files")
MULTIPLE_DB = _bool("MULTIPLE_DB", False)
DATABASE_URI2 = environ.get("DATABASE_URI2", "") or DATABASE_URI
DB_SIZE_LIMIT_MB = int(environ.get("DB_SIZE_LIMIT_MB", "407"))    # isse zyada hone par 2nd DB use hota hai
USE_CAPTION_FILTER = _bool("USE_CAPTION_FILTER", True)
INDEX_CAPTION = _bool("SAVE_CAPTION", True)
MAX_B_TN = int(environ.get("MAX_B_TN", "10"))                     # ek page par kitni files
FILE_SEARCH = _bool("FILE_SEARCH", True)
FILE_TMDB_MATCH = _bool("FILE_TMDB_MATCH", False)                 # naye file par TMDB card post (movie channel ke liye)
STREAM_MODE = _bool("STREAM_MODE", False)
PREMIUM_STREAM_MODE = _bool("PREMIUM_STREAM_MODE", False)
SLEEP_THRESHOLD = int(environ.get("SLEEP_THRESHOLD", "60"))
AUTH_USERS = _ids("AUTH_USERS")                                   # khali = sab use kar sakte hain
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", "<b>{file_name}</b>\n\n💾 Size: {file_size}\n\n{file_caption}")
LANGUAGES = {"Hindi": "hin", "English": "eng", "Tamil": "tam", "Telugu": "tel", "Malayalam": "mal", "Kannada": "kan",
             "Gujarati": "guj", "Marathi": "mar", "Punjabi": "pun", "Bengali": "ben", "Urdu": "urdu"}
QUALITIES = ["360P", "480P", "720P", "1080P", "1440P", "2160P", "4K"]
SEASONS = [f"S{str(i).zfill(2)}" for i in range(1, 13)]
BAD_WORDS = {"join", "www", "tg", "original", "telegram", "channel", "movies", "hdhub4u", "mkvcinemas", "skymovieshd"}

CARD_OVERVIEW_LEN = int(environ.get("CARD_OVERVIEW_LEN", "330"))      # original LONG_IMDB_DESCRIPTION jaisa: 1000 kar do
NO_RESULTS_MSG = _bool("NO_RESULTS_MSG", True)                        # kuch na milne par LOG_CHANNEL me alert

VERIFY_MIDNIGHT = _bool("VERIFY_MIDNIGHT", False)   # True = verify raat 12 baje (IST) tak valid (original jaisa), False = VERIFY_VALID seconds

# ---------- /start look (original jaisa) ----------
EMOJI_MODE = _bool("EMOJI_MODE", True)         # /start par bada emoji reaction animation
REACTIONS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"]
TIMEZONE = environ.get("TIMEZONE", "Asia/Kolkata")
FSUB_PICS = environ.get("FSUB_PICS", "https://graph.org/file/7478ff3eac37f4329c3d8.jpg https://graph.org/file/56b5deb73f3b132e2bb73.jpg").split()
VERIFY_IMG = environ.get("VERIFY_IMG", "https://telegra.ph/file/9ecc5d6e4df5b83424896.jpg")
NOR_IMG = environ.get("NOR_IMG", "https://graph.org/file/e20b5fdaf217252964202.jpg")      # kuch nahi mila
SPELL_IMG = environ.get("SPELL_IMG", "https://graph.org/file/13702ae26fb05df52667c.jpg")    # spelling suggestions
