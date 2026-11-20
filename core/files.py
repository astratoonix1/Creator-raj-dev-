"""File index database - original ia_filterdb.py ka logic (umongo ki jagah seedha motor)."""
import base64
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from struct import pack

import motor.motor_asyncio
from pymongo.errors import DuplicateKeyError
from pyrogram.file_id import FileId

import config as C
from core.helpers import rand

log = logging.getLogger(__name__)

_c1 = motor.motor_asyncio.AsyncIOMotorClient(C.DATABASE_URI)
_d1 = _c1[C.DATABASE_NAME]
Media = _d1[C.COLLECTION_NAME]
if C.MULTIPLE_DB:
    _c2 = motor.motor_asyncio.AsyncIOMotorClient(C.DATABASE_URI2)
    _d2 = _c2[C.DATABASE_NAME]
    Media2 = _d2[C.COLLECTION_NAME]
else:
    _d2 = None
    Media2 = None

_cache = {"ts": None, "size": 0.0}


async def ensure_indexes():
    for col in (Media, Media2):
        if col is None:
            continue
        try:
            await col.create_index([("file_name", "text")])
            await col.create_index("sid")
        except Exception as e:
            log.warning(f"index create: {e}")


async def db_size_mb():
    """Primary DB ka size (10 min cache)."""
    now = datetime.utcnow()
    if _cache["ts"] and now - _cache["ts"] < timedelta(minutes=10) and _cache["size"] < 10:
        return _cache["size"]
    try:
        st = await _d1.command("dbstats")
        _cache.update(ts=now, size=(st["dataSize"] + st["indexSize"]) / 1048576)
    except Exception as e:
        log.warning(f"dbsize: {e}")
    return _cache["size"]


# ---------------- file id helpers (original) ----------------
def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(ref: bytes) -> str:
    return base64.urlsafe_b64encode(ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    d = FileId.decode(new_file_id)
    fid = encode_file_id(pack("<iiqq", int(d.file_type), d.dc_id, d.media_id, d.access_hash))
    return fid, encode_file_ref(d.file_reference)


def clean_filename(name):
    prefixes = ("[", "@", "www.")
    bad = {w.lower() for w in C.BAD_WORDS}
    return " ".join(w for w in name.split() if not (w.startswith(prefixes) or w.lower() in bad))


# ---------------- save ----------------
async def save_file(media):
    """returns (saved?, code) : 1 saved, 0 duplicate, 2 invalid, 3 error"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    name = re.sub(r"[_\-\.#+$%^&*()!~`,;:\"'?/<>\[\]{}=|\\]", " ", str(media.file_name))
    name = clean_filename(re.sub(r"\s+", " ", name).strip())
    if not name or not media.file_size:
        return False, 2
    col = Media
    if C.MULTIPLE_DB:
        try:
            if await Media.count_documents({"_id": file_id}, limit=1):
                return False, 0
            if await db_size_mb() >= C.DB_SIZE_LIMIT_MB:
                col = Media2
        except Exception as e:
            log.error("multi-db check fail, primary use ho raha", exc_info=e)
    doc = {
        "_id": file_id, "file_ref": file_ref, "file_name": name, "file_size": media.file_size,
        "file_type": media.file_type, "mime_type": media.mime_type, "sid": rand(10),
        "caption": (media.caption.html if media.caption and C.INDEX_CAPTION else None),
    }
    try:
        await col.insert_one(doc)
    except DuplicateKeyError:
        return False, 0
    except Exception:
        log.exception(f"save fail {name}")
        return False, 3
    return True, 1


# ---------------- search (original regex logic) ----------------
def _pattern(q):
    q = q.strip()
    if not q:
        return "."
    if " " not in q:
        return r"(\b|[\.\+\-_])" + re.escape(q) + r"(\b|[\.\+\-_])"
    return re.escape(q).replace(r"\ ", r".*[\s\.\+\-_()\[\]]")


def _filter(query, file_type=None):
    if isinstance(query, list):
        regs = [re.compile(_pattern(q), re.I) for q in query if q.strip()]
        f = {"$or": [{"file_name": r} for r in regs] + ([{"caption": r} for r in regs] if C.USE_CAPTION_FILTER else [])}
    else:
        r = re.compile(_pattern(query), re.I)
        f = {"$or": [{"file_name": r}, {"caption": r}]} if C.USE_CAPTION_FILTER else {"file_name": r}
    if file_type:
        f["file_type"] = file_type
    return f


async def get_search_results(query, file_type=None, max_results=None, offset=0):
    max_results = max_results or C.MAX_B_TN
    try:
        f = _filter(query, file_type)
    except re.error:
        return [], "", 0
    total = await Media.count_documents(f)
    if C.MULTIPLE_DB:
        total += await Media2.count_documents(f)
    files = await Media.find(f).sort("$natural", -1).skip(offset).limit(max_results).to_list(max_results)
    if C.MULTIPLE_DB and len(files) < max_results:
        rem = max_results - len(files)
        files += await Media2.find(f).sort("$natural", -1).skip(offset).limit(rem).to_list(rem)
    nxt = offset + len(files)
    return files, ("" if nxt >= total else nxt), total


async def get_bad_files(query, file_type=None):
    f = _filter(query, file_type)
    files = await Media.find(f).sort("$natural", -1).to_list(None)
    if C.MULTIPLE_DB:
        files += await Media2.find(f).sort("$natural", -1).to_list(None)
    return files, len(files)


async def get_by_sid(sid):
    d = await Media.find_one({"sid": sid})
    if not d and C.MULTIPLE_DB:
        d = await Media2.find_one({"sid": sid})
    return d


async def get_file_details(file_id):
    d = await Media.find_one({"_id": file_id})
    if not d and C.MULTIPLE_DB:
        d = await Media2.find_one({"_id": file_id})
    return d


async def total_files():
    n = await Media.count_documents({})
    if C.MULTIPLE_DB:
        n += await Media2.count_documents({})
    return n


# ---------------- delete ----------------
async def delete_one_media(media):
    """Original ka 4-step fallback delete. media = pyrogram document/video/audio. returns True/False"""
    file_id, _ = unpack_new_file_id(media.file_id)
    cols = [c for c in (Media, Media2) if c is not None]
    for c in cols:
        if (await c.delete_one({"_id": file_id})).deleted_count:
            return True
    spaced = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    for name in (spaced, media.file_name):
        for c in cols:
            r = await c.delete_many({"file_name": name, "file_size": media.file_size, "mime_type": media.mime_type})
            if r.deleted_count:
                return True
    return False


async def delete_by_query(keyword):
    f = _filter(keyword)
    n = (await Media.delete_many(f)).deleted_count
    if C.MULTIPLE_DB:
        n += (await Media2.delete_many(f)).deleted_count
    return n


async def drop_all():
    await Media.drop()
    if C.MULTIPLE_DB:
        await Media2.drop()


# ---------------- latest titles (/movies /series) ----------------
async def latest(limit):
    if C.MULTIPLE_DB and await db_size_mb() > C.DB_SIZE_LIMIT_MB:
        return await Media2.find().sort("$natural", -1).limit(limit).to_list(limit)
    return await Media.find().sort("$natural", -1).limit(limit).to_list(limit)


_JUNK = r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)"


def clean_title(filename, is_series=False):
    ym = re.search(r"^(.*?(\d{4}|\(\d{4}\)))", filename, re.I)
    if ym:
        return re.sub(_JUNK, " ", ym.group(1).replace("(", "").replace(")", "")).strip().title()
    if is_series:
        sm = re.search(r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?", filename, re.I)
        if sm:
            season = sm.group(2) or sm.group(3) or sm.group(4)
            return f"{re.sub(_JUNK, ' ', sm.group(1).strip()).strip().title()} S{int(season):02}"
    return re.sub(_JUNK, " ", filename).strip().title()


async def get_latest_singles(limit=20):
    pat = r"(?:s\d{1,2}|season\s*\d+|season\d+)(?:\s*combined)?(?:e\d{1,2}|episode\s*\d+)?\b"
    out = set()
    for f in await latest(limit * 2):
        if not re.search(pat, f.get("file_name", ""), re.I):
            out.add(clean_title(f["file_name"]))
        if len(out) >= limit:
            break
    return sorted(out)[:limit]


async def get_latest_series(limit=30):
    pat = r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?(?:E(\d{1,2})|Episode\s*(\d+))?\b"
    g = defaultdict(list)
    for f in await latest(limit * 5):
        m = re.search(pat, f.get("file_name", ""), re.I)
        if m:
            g[clean_title(m.group(1), True)].append(int(m.group(2) or m.group(3) or m.group(4)))
    return {t: sorted(set(s))[:10] for t, s in g.items() if s}
