"""
community.py
=============
Per-user "community" branding.

Bot mein pehle "sbanime" hardcoded default tha — thumbnail band, auto-caption
tag ([@SBANIME]) aur full-metadata video title mein. Ab jo bhi user
/community <name> chalayega, uske liye in sab jagah "sbanime" ki jagah
uska diya hua naam use hoga. Kuch set na kare toh 'sbanime' hi default
rehta hai (purana behaviour waisa hi).

Isse import karo taaki hardcoded '@SBANIME' / 'Sbanime' ki jagah dynamic
value resolve ho sake:

    from ..utils.community import get_community_tag
    channel = await get_community_tag(user_id)   # '@SBANIME' ya '@BOBANIME'
"""

from .database.access_db import db

DEFAULT_COMMUNITY = "sbanime"


async def get_community_name(user_id) -> str:
    """Raw community name, lowercase. Default: 'sbanime'."""
    try:
        name = await db.get_community(user_id)
    except Exception:
        name = None
    name = (name or DEFAULT_COMMUNITY).strip().lower()
    return name or DEFAULT_COMMUNITY


async def get_community_tag(user_id) -> str:
    """@-prefixed uppercase tag — caption/thumbnail band ke liye. e.g. '@BOBANIME'."""
    name = await get_community_name(user_id)
    return f"@{name.upper()}"


async def get_community_title(user_id) -> str:
    """Title-case naam — metadata title ke liye. e.g. 'Bobanime'."""
    name = await get_community_name(user_id)
    return name.capitalize()
