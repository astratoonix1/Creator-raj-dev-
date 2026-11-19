"""TMDB API wrapper - sirf info, poster aur trailer (koi movie file nahi)."""
import aiohttp
from config import TMDB_API_KEY, TMDB_LANG

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"
_session = None


async def _get(path, **params):
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
    params.update(api_key=TMDB_API_KEY)
    try:
        async with _session.get(f"{BASE}{path}", params=params) as r:
            if r.status != 200:
                return None
            return await r.json()
    except Exception:
        return None


def _norm(x, media=None):
    media = media or x.get("media_type")
    if media not in ("movie", "tv"):
        return None
    title = x.get("title") or x.get("name") or "?"
    date = x.get("release_date") or x.get("first_air_date") or ""
    return {
        "key": ("m" if media == "movie" else "t") + str(x["id"]),
        "media": media,
        "id": x["id"],
        "title": title,
        "year": date[:4],
        "rating": round(x.get("vote_average") or 0, 1),
        "pop": x.get("popularity", 0),
    }


async def search(query):
    d = await _get("/search/multi", query=query, language=TMDB_LANG, include_adult="false")
    out = []
    for x in (d or {}).get("results", []):
        n = _norm(x)
        if n:
            out.append(n)
    return out


async def trending(media="all", window="week"):
    d = await _get(f"/trending/{media}/{window}", language=TMDB_LANG)
    out = []
    for x in (d or {}).get("results", []):
        n = _norm(x)
        if n:
            out.append(n)
    return out


async def details(key):
    """key = 'm123' (movie) ya 't123' (tv)"""
    media = "movie" if key[0] == "m" else "tv"
    mid = key[1:]
    d = await _get(
        f"/{media}/{mid}",
        language=TMDB_LANG,
        append_to_response="videos,credits,external_ids",
        include_video_language="en,hi,null",
    )
    if not d:
        return None
    base = _norm(d, media)
    vids = [v for v in d.get("videos", {}).get("results", []) if v.get("site") == "YouTube"]
    vids.sort(key=lambda v: (v.get("type") != "Trailer", not v.get("official"), v.get("type") != "Teaser"))
    trailer = f"https://www.youtube.com/watch?v={vids[0]['key']}" if vids else None
    crew = d.get("credits", {}).get("crew", [])
    director = next((c["name"] for c in crew if c.get("job") == "Director"), None)
    if not director and d.get("created_by"):
        director = ", ".join(c["name"] for c in d["created_by"][:2])
    cast = [c["name"] for c in d.get("credits", {}).get("cast", [])[:5]]
    runtime = d.get("runtime") or (d.get("episode_run_time") or [None])[0]
    imdb = d.get("external_ids", {}).get("imdb_id") or d.get("imdb_id")
    base.update(
        overview=d.get("overview") or "",
        tagline=d.get("tagline") or "",
        genres=[g["name"] for g in d.get("genres", [])],
        runtime=runtime,
        lang=(d.get("original_language") or "").upper(),
        status=d.get("status") or "",
        seasons=d.get("number_of_seasons"),
        votes=d.get("vote_count") or 0,
        poster=f"{IMG}/w780{d['poster_path']}" if d.get("poster_path") else None,
        backdrop=f"{IMG}/w1280{d['backdrop_path']}" if d.get("backdrop_path") else None,
        trailer=trailer,
        director=director,
        cast=cast,
        imdb=f"https://www.imdb.com/title/{imdb}/" if imdb else None,
    )
    return base
