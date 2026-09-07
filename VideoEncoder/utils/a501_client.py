"""
a501_client.py
================
A501 (Stremio-protocol) backend se anime ki details khींchne ke liye thin
client — /add_anime ke naye "auto-detail" step ke liye banaya gaya hai.

Kya milta hai:
  - poster/backdrop image URL       (update-post ki pic + thumbnail dono ke liye)
  - genres                          (update-post ke "Genres" field ke liye)
  - audio languages                 (update-post ke "Audio" field ke liye)
  - latest season number + us season ke total episodes
                                     (/schedule ke total_eps ke liye)

Config (config.env mein daalo):
  A501_BACKEND_URL   e.g. "https://a501-production.up.railway.app"
  A501_TOKEN         Wahi Stremio addon token jo A501 app/config mein use hota hai

Dono nahi diye toh yeh module chup-chaap None/[] return karta rahega —
/add_anime tab bhi kaam karega, bas auto-detail wala hissa skip ho jaayega
aur user ko baad mein /update_post_list se manually bharna hoga.
"""

import logging
import re
from os import getenv
from urllib.parse import quote

import aiohttp

LOGGER = logging.getLogger(__name__)

A501_BACKEND_URL = (getenv("A501_BACKEND_URL") or "").rstrip("/")
A501_TOKEN = (getenv("A501_TOKEN") or "").strip()

# Search ke liye A501 manifest ka koi bhi catalog chalega jo "search" extra
# support karta ho — series catalog use kar rahe hain kyunki anime yahan
# hamesha "series" (season/episode) ki tarah stored hote hain.
_SEARCH_MEDIA_TYPE = "series"
_SEARCH_CATALOG_ID = "top_series"

_TIMEOUT = aiohttp.ClientTimeout(total=15)


def is_configured() -> bool:
    return bool(A501_BACKEND_URL and A501_TOKEN)


def _normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


async def _get_json(url: str):
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    LOGGER.warning(f"[A501Client] {url} -> HTTP {resp.status}")
                    return None
                return await resp.json(content_type=None)
    except Exception as e:
        LOGGER.warning(f"[A501Client] request failed for {url}: {e}")
        return None


async def search_anime(query: str) -> list:
    """A501 catalog search karo, metas ki list lauta do (fail pe [])."""
    if not is_configured():
        return []
    url = (
        f"{A501_BACKEND_URL}/stremio/{A501_TOKEN}/catalog/"
        f"{_SEARCH_MEDIA_TYPE}/{_SEARCH_CATALOG_ID}/search={quote(query)}.json"
    )
    data = await _get_json(url)
    if not data:
        return []
    return data.get("metas", []) or []


async def get_meta(imdb_id: str, media_type: str = "series"):
    """Ek title ki full meta (videos/season/episode list samet) lo."""
    if not is_configured():
        return None
    url = f"{A501_BACKEND_URL}/stremio/{A501_TOKEN}/meta/{media_type}/{imdb_id}.json"
    data = await _get_json(url)
    if not data:
        return None
    meta = data.get("meta")
    return meta or None


async def fetch_anime_details(anime_name: str):
    """
    Anime name se best-match dhoondo aur /add_anime ke liye zaroori
    fields ek dict mein return karo:

      {
        "matched_name": str,   # API pe jo exact naam mila
        "image":        str,   # poster/backdrop URL ("" agar nahi mila)
        "audio":        str,   # "Hindi, English" jaisa comma list
        "genres":       str,   # "Action, Comedy" jaisa comma list
        "season":       int | None,   # latest/current season number
        "total_eps":    int,   # us season ke total episodes
      }

    Kuch bhi na mile (API down, config missing, ya koi match nahi) toh
    None return hota hai — caller isko "auto-detail nahi mila" treat kare.
    """
    results = await search_anime(anime_name)
    if not results:
        return None

    query_norm = _normalize(anime_name)
    best = None
    for item in results:
        if _normalize(item.get("name", "")) == query_norm:
            best = item
            break
    if not best:
        # Exact match nahi mila — pehla result hi sabse relevant maana jaata
        # hai (backend ka apna relevance-sorted search hai).
        best = results[0]

    imdb_id = best.get("id") or best.get("imdb_id")
    if not imdb_id:
        return None

    media_type = best.get("type") or _SEARCH_MEDIA_TYPE
    meta = await get_meta(imdb_id, media_type)
    if not meta:
        return None

    image = meta.get("poster") or meta.get("background") or ""
    genres = ", ".join(meta.get("genres") or [])
    audio = ", ".join(meta.get("languages") or [])

    season = None
    total_eps = 0
    videos = meta.get("videos") or []
    if videos:
        season_counts = {}
        for v in videos:
            s = v.get("season")
            if s is None:
                continue
            season_counts[s] = season_counts.get(s, 0) + 1
        # Season 0 = "combined/specials" bucket (A501 convention) — real
        # numbered seasons ko priority do, warna jo bhi mila wahi le lo.
        real_seasons = {s: c for s, c in season_counts.items() if s and s > 0}
        pool = real_seasons or season_counts
        if pool:
            season = max(pool.keys())
            total_eps = pool[season]

    return {
        "matched_name": meta.get("name") or best.get("name") or anime_name,
        "image": image,
        "audio": audio,
        "genres": genres,
        "season": season,
        "total_eps": total_eps,
    }
