"""
encode_mode.py
==============
Global ON/OFF switch — bot ka overall behaviour control karta hai:

  /encode_mode          → current status dekho
  /encode_mode on       → (default) full VideoEncoder bot — /start pe
                          normal welcome + Settings button aata hai,
                          sara existing feature-set jaisa abhi hai
                          waisa hi kaam karta hai.
  /encode_mode off      → auto-upload-bot-only mode:
                            - /start sirf "Yeh ek auto upload bot hai!"
                              bolega, Settings button nahi aayega
                            - video/document bhejte hi seedha encode
                              shuru ho jaata hai (koi settings menu ya
                              extra prompt nahi)

Bot-wide toggle hai (col2 mein save hota hai) — sabhi users ke liye
same, per-user nahi. Sirf owner/sudo command chala sakte hain.
"""

import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from .. import owner, sudo_users
from ..utils.database.access_db import db

LOGGER = logging.getLogger(__name__)


def _is_auth(user_id: int) -> bool:
    return user_id in owner or user_id in sudo_users


async def get_encode_mode() -> bool:
    """True = ON (default, full VideoEncoder features), False = OFF (auto-upload bot only)."""
    doc = await db.col2.find_one({'id': 'encode_mode'})
    if not doc:
        return True
    return doc.get('enabled', True)


async def _set_encode_mode(enabled: bool):
    await db.col2.update_one(
        {'id': 'encode_mode'},
        {'$set': {'enabled': enabled}},
        upsert=True,
    )


@Client.on_message(filters.command("encode_mode") & filters.private)
async def cmd_encode_mode(client: Client, message: Message):
    if not _is_auth(message.from_user.id):
        return

    parts = message.text.split(None, 1)
    if len(parts) < 2 or parts[1].strip().lower() not in ("on", "off"):
        current = await get_encode_mode()
        status = "🟢 ON" if current else "🔴 OFF"
        await message.reply(
            f"⚙️ **Encode Mode**\n\n"
            f"Current Status: **{status}**\n\n"
            f"• `/encode_mode on` — full VideoEncoder bot (Settings, quality menu, waghera)\n"
            f"• `/encode_mode off` — auto-upload bot only "
            f"(/start pe settings nahi dikhenge, video bhejte hi seedha encode hoga)"
        )
        return

    enabled = (parts[1].strip().lower() == "on")
    await _set_encode_mode(enabled)

    if enabled:
        await message.reply(
            "✅ **Encode Mode: ON**\n\n"
            "Bot ab full VideoEncoder ki tarah kaam karega — "
            "/start pe Settings button wapas aayega."
        )
    else:
        await message.reply(
            "🔴 **Encode Mode: OFF**\n\n"
            "Bot ab sirf ek auto-upload bot ki tarah kaam karega — "
            "/start pe koi settings nahi dikhenge."
        )
