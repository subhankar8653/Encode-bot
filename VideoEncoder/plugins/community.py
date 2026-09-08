"""
community.py (plugin)
======================
/community <name>   — GLOBAL community/channel naam set karo (bot-wide,
                       sabhi upload paths — manual + auto-monitor — is
                       naam ko use karenge). Sirf owner/sudo chala
                       sakte hain, kyunki yeh sab users/uploads ke liye
                       ek saath badalta hai.
/community           — current community naam dekho.
/communityclear       — default 'sbanime' pe wapas reset karo.
"""

from pyrogram import Client, filters
from pyrogram.types import Message

from .. import owner, sudo_users
from ..utils.database.access_db import db
from ..utils.community import DEFAULT_COMMUNITY, get_community_name


def _is_auth(user_id: int) -> bool:
    return user_id in owner or user_id in sudo_users


@Client.on_message(filters.command("community"))
async def set_community(client: Client, message: Message):
    if len(message.command) < 2:
        current = await get_community_name()
        await message.reply(
            f"⚙️ <b>Community Branding</b> <i>(bot-wide)</i>\n\n"
            f"Current: <code>{current}</code>\n\n"
            f"Usage: <code>/community &lt;name&gt;</code>\n"
            f"Example: <code>/community bobanime</code>\n\n"
            f"Set karne ke baad thumbnail band, auto-caption tag aur "
            f"metadata title mein <code>{DEFAULT_COMMUNITY}</code> ki jagah "
            f"tumhara diya hua naam <b>sabhi uploads</b> mein (manual + "
            f"auto-monitor) use hoga.\n\n"
            f"Reset karne ke liye: <code>/communityclear</code>",
        )
        return

    if not _is_auth(message.from_user.id):
        await message.reply("❌ Sirf owner/sudo hi community naam badal sakte hain (yeh bot-wide setting hai).")
        return

    name = message.command[1].strip().lstrip("@")
    if not name or not name.replace("_", "").isalnum():
        await message.reply(
            "❌ Sahi naam do (sirf letters/numbers/underscore).\n"
            "Example: <code>/community bobanime</code>"
        )
        return

    name = name.lower()
    await db.set_community(name)
    await message.reply(
        f"✅ <b>Community set:</b> <code>{name}</code> <i>(bot-wide, sabke liye)</i>\n\n"
        f"Ab thumbnail band, auto-caption tag aur metadata title mein "
        f"<code>{DEFAULT_COMMUNITY}</code> ki jagah <code>@{name.upper()}</code> "
        f"(ya <code>{name.capitalize()}</code>) — manual aur auto-monitor "
        f"dono uploads mein — use hoga."
    )


@Client.on_message(filters.command("communityclear"))
async def clear_community(client: Client, message: Message):
    if not _is_auth(message.from_user.id):
        await message.reply("❌ Sirf owner/sudo hi community naam reset kar sakte hain.")
        return
    await db.set_community(None)
    await message.reply(
        f"🔄 Community reset ho gaya, ab default "
        f"<code>{DEFAULT_COMMUNITY}</code> use hoga (sabke liye)."
    )
