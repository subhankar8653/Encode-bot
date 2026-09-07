"""
anime_api.py
================
/add_anime ke "auto-detail" step ke liye independent anime-metadata client.

Koi bhi third-party backend/token nahi chahiye — dono APIs public & free hain:

  - AniList   (https://anilist.co)  → title match, genres, description,
                                       poster/banner, total episodes, status
  - AniZip    (https://api.ani.zip) → AniList id se episode-level mapping
                                       (season/episode count cross-check ke liye)

Bina kisi config ke kaam karta hai — koi env var set karne ki zaroorat nahi.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Optional

import httpx

LOGGER = logging.getLogger(__name__)

ANILIST_URL = "https://graphql.anilist.co"
ANIZIP_URL = "https://api.ani.zip/mappings"

_TITLE_MATCH_THRESHOLD = 0.55
_TIMEOUT = httpx.Timeout(15.0)

_ANILIST_FIELDS = """
    id
    title { romaji english }
    synonyms
    seasonYear
    startDate { year }
    status
    format
    episodes
    genres
    coverImage { extraLarge large }
    bannerImage
"""

_ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
""" + _ANILIST_FIELDS + """
  }
}
"""

_client: Optional[httpx.AsyncClient] = None


def is_configured() -> bool:
    # AniList/AniZip public hain — hamesha "available" maana jaata hai.
    return True


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "urlenbot/1.0"},
        )
    return _client


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r"^\b(the|a|an)\b\s+", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _title_match_score(query: str, media: dict) -> float:
    titles = media.get("title") or {}
    candidates = [titles.get("romaji"), titles.get("english"), *(media.get("synonyms") or [])]
    q = _normalize_title(query)
    if not q:
        return 0.0
    best = 0.0
    for cand in candidates:
        cn = _normalize_title(cand)
        if cn:
            best = max(best, _fuzzy_ratio(q, cn))
    return best


async def _anilist_search(query: str) -> Optional[dict]:
    try:
        client = await _get_client()
        resp = await client.post(ANILIST_URL, json={"query": _ANILIST_QUERY, "variables": {"search": query}})
        if resp.status_code != 200:
            return None
        return ((resp.json() or {}).get("data") or {}).get("Media")
    except Exception as e:
        LOGGER.warning(f"[AnimeAPI] AniList search failed for '{query}': {e}")
        return None


async def _anizip_mappings(anilist_id: int) -> Optional[dict]:
    try:
        client = await _get_client()
        resp = await client.get(ANIZIP_URL, params={"anilist_id": anilist_id})
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        LOGGER.warning(f"[AnimeAPI] ani.zip mappings failed for {anilist_id}: {e}")
        return None


async def search_anime(query: str) -> list:
    """AniList pe title search karo, matched media (dict, agar mila) wapas do."""
    media = await _anilist_search(query)
    if not media:
        return []
    return [media]


async def fetch_anime_details(anime_name: str):
    """
    AniList (+ AniZip) se anime ki details nikalo, /add_anime ke liye
    zaroori fields ek dict mein:

      {
        "matched_name": str,
        "image":        str,   # poster/banner URL ("" agar nahi mila)
        "genres":       str,   # "Action, Comedy"
        "audio":        str,   # AniList audio-language nahi deta — default
                                # "Hindi ORG" (baad mein /update_post_list se
                                # manually change kar sakte ho)
        "season":       None,  # AniList per-season track nahi karta
        "total_eps":    int,   # total episode count
        "status":       str,   # "Ongoing" / "Finished" / ""
      }

    Match na mile ya API fail ho jaaye toh None.
    """
    media = await _anilist_search(anime_name)
    if not media:
        LOGGER.info(f"[AnimeAPI] No AniList match for '{anime_name}'")
        return None

    score = _title_match_score(anime_name, media)
    if score < _TITLE_MATCH_THRESHOLD:
        titles = media.get("title") or {}
        LOGGER.info(
            f"[AnimeAPI] Rejecting low-confidence match for '{anime_name}': "
            f"got '{titles.get('english') or titles.get('romaji')}' (score={score:.2f})"
        )
        return None

    doc = await _anizip_mappings(media.get("id")) or {}
    titles = media.get("title") or {}
    cover = media.get("coverImage") or {}

    total_eps = media.get("episodes") or 0
    if not total_eps:
        # AniList "episodes" ongoing shows ke liye null hota hai — AniZip ke
        # actual episode-mapping count se fallback lo.
        total_eps = len((doc.get("episodes") or {}))

    status_map = {
        "RELEASING": "Ongoing",
        "FINISHED": "Finished",
        "NOT_YET_RELEASED": "Upcoming",
        "CANCELLED": "Cancelled",
        "HIATUS": "On Hiatus",
    }

    return {
        "matched_name": titles.get("english") or titles.get("romaji") or anime_name,
        "image": cover.get("extraLarge") or cover.get("large") or media.get("bannerImage") or "",
        "genres": ", ".join(media.get("genres") or []),
        "audio": "Hindi ORG",
        "season": None,
        "total_eps": total_eps,
        "status": status_map.get(media.get("status") or "", ""),
    }
