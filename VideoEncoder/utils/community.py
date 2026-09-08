"""
community.py
=============
GLOBAL (bot-wide) "community" branding.

Pehle "sbanime" hardcoded default tha — thumbnail band, auto-caption tag
([@SBANIME]) aur full-metadata video title mein. /community <name> se koi
bhi authorized (owner/sudo) account naam set kar sakta hai, aur woh naam
sab jagah — manual uploads AUR auto-monitor (automated channel upload)
dono mein — consistent use hota hai. Kuch set na kare toh 'sbanime' hi
default rehta hai.

NOTE: Yeh jaan-boojh kar GLOBAL hai, per-user NAHI — auto-monitor ka
upload pipeline internally sirf owner ID use karta hai, isliye per-user
setting hoti toh sudo account se set kiya naam auto-monitor tak kabhi
nahi pahunchta. `user_id` parameter sirf backward-compat ke liye accept
hota hai (purane call-sites tootne na paayein), lekin ignore hota hai.

    from ..utils.community import get_community_tag
    channel = await get_community_tag()   # '@SBANIME' ya '@BOBANIME'
"""

from .database.access_db import db

DEFAULT_COMMUNITY = "sbanime"


async def get_community_name(user_id=None) -> str:
    """Raw community name, lowercase. Default: 'sbanime'. (Global — user_id ignored.)"""
    try:
        name = await db.get_community()
    except Exception:
        name = None
    name = (name or DEFAULT_COMMUNITY).strip().lower()
    return name or DEFAULT_COMMUNITY


async def get_community_tag(user_id=None) -> str:
    """@-prefixed uppercase tag — caption/thumbnail band ke liye. e.g. '@BOBANIME'."""
    name = await get_community_name()
    return f"@{name.upper()}"


async def get_community_title(user_id=None) -> str:
    """Title-case naam — metadata title ke liye. e.g. 'Bobanime'."""
    name = await get_community_name()
    return name.capitalize()
