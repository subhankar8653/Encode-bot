"""
community.py (plugin)
======================
/community <name>   — apna community/channel naam set karo. Uske baad
                       thumbnail band, auto-caption tag ([@NAME]) aur
                       full-metadata video title mein har jagah default
                       "sbanime" ki jagah yeh naam use hoga.
/community           — current community naam dekho.
/communityclear       — default 'sbanime' pe wapas reset karo.
"""

from pyrogram import Client, filters
from pyrogram.types import Message

from ..utils.database.access_db import db
from ..utils.community import DEFAULT_COMMUNITY, get_community_name


@Client.on_message(filters.command("community"))
async def set_community(client: Client, message: Message):
    if len(message.command) < 2:
        current = await get_community_name(message.from_user.id)
        await message.reply(
            f"⚙️ <b>Community Branding</b>\n\n"
            f"Current: <code>{current}</code>\n\n"
            f"Usage: <code>/community &lt;name&gt;</code>\n"
            f"Example: <code>/community bobanime</code>\n\n"
            f"Set karne ke baad thumbnail band, auto-caption tag aur "
            f"metadata title mein <code>{DEFAULT_COMMUNITY}</code> ki jagah "
            f"tumhara diya hua naam use hoga.\n\n"
            f"Reset karne ke liye: <code>/communityclear</code>",
        )
        return

    name = message.command[1].strip().lstrip("@")
    if not name or not name.replace("_", "").isalnum():
        await message.reply(
            "❌ Sahi naam do (sirf letters/numbers/underscore).\n"
            "Example: <code>/community bobanime</code>"
        )
        return

    name = name.lower()
    await db.set_community(message.from_user.id, name)
    await message.reply(
        f"✅ <b>Community set:</b> <code>{name}</code>\n\n"
        f"Ab thumbnail band, auto-caption tag aur metadata title mein "
        f"<code>{DEFAULT_COMMUNITY}</code> ki jagah <code>@{name.upper()}</code> "
        f"(ya <code>{name.capitalize()}</code>) use hoga."
    )


@Client.on_message(filters.command("communityclear"))
async def clear_community(client: Client, message: Message):
    await db.set_community(message.from_user.id, None)
    await message.reply(
        f"🔄 Community reset ho gaya, ab default "
        f"<code>{DEFAULT_COMMUNITY}</code> use hoga."
    )
