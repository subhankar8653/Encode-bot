"""
redeploy.py
============
/redeploy — Railway pe manually jaake redeploy karne ki jagah, seedha
Telegram se ek button tap karke bot ko redeploy kar do.

Railway ka Public API (GraphQL) use karta hai — koi extra library nahi
chahiye, httpx (already requirements.txt mein hai) se seedha call karte
hain.

Setup (config.env mein 3 naye optional variables):
  RAILWAY_API_TOKEN     -> railway.app/account/tokens se personal/account
                            token banao (Account Token, "All your
                            resources" scope kaafi hai)
  RAILWAY_SERVICE_ID    -> Railway dashboard mein service khol ke URL se:
                            railway.app/project/<projectId>/service/<serviceId>
  RAILWAY_ENVIRONMENT_ID -> wahi URL mein ?environmentId=<environmentId>
                            (ya Settings > General mein environment ID)

Teeno set na ho toh /redeploy bas setup instructions dikha dega — bot
crash nahi karega (lazy getenv, startup pe kuch check nahi hota).
"""

import logging
import os

import httpx
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)

from ..utils.helper import check_chat

LOGGER = logging.getLogger(__name__)

RAILWAY_API_URL = "https://backboard.railway.com/graphql/v2"

_REDEPLOY_MUTATION = """
mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
  serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""


def _railway_config():
    token = os.getenv("RAILWAY_API_TOKEN", "").strip()
    service_id = os.getenv("RAILWAY_SERVICE_ID", "").strip()
    env_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    return token, service_id, env_id


async def _trigger_railway_redeploy() -> tuple[bool, str]:
    """Returns (success, message)."""
    token, service_id, env_id = _railway_config()
    if not (token and service_id and env_id):
        return False, "config_missing"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                RAILWAY_API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": _REDEPLOY_MUTATION,
                    "variables": {"serviceId": service_id, "environmentId": env_id},
                },
            )
        data = resp.json()
        if resp.status_code != 200 or data.get("errors"):
            err = data.get("errors")[0].get("message") if data.get("errors") else f"HTTP {resp.status_code}"
            LOGGER.error(f"[Redeploy] Railway API error: {err}")
            return False, err
        if data.get("data", {}).get("serviceInstanceRedeploy"):
            return True, "ok"
        return False, "Railway ne redeploy confirm nahi kiya (unexpected response)."
    except Exception as e:
        LOGGER.error(f"[Redeploy] Request failed: {e}")
        return False, str(e)


_SETUP_INSTRUCTIONS = (
    "⚠️ **Redeploy set up nahi hai!**\n\n"
    "`config.env` mein 3 variables add karo:\n\n"
    "1️⃣ `RAILWAY_API_TOKEN` — [railway.app/account/tokens](https://railway.app/account/tokens) "
    "se Account Token banao\n"
    "2️⃣ `RAILWAY_SERVICE_ID` — Railway dashboard mein service khol ke URL se copy karo\n"
    "   `railway.app/project/<projectId>/service/`**`<serviceId>`**\n"
    "3️⃣ `RAILWAY_ENVIRONMENT_ID` — usi URL ke end mein\n"
    "   `?environmentId=`**`<environmentId>`**\n\n"
    "Set karne ke baad bot ko ek baar manually redeploy karo (Railway pe) — "
    "uske baad se `/redeploy` command se hi kaam chal jayega."
)


@Client.on_message(filters.command("redeploy"))
async def cmd_redeploy(client: Client, message: Message):
    c = await check_chat(message, chat="Sudo")
    if not c:
        return

    token, service_id, env_id = _railway_config()
    if not (token and service_id and env_id):
        await message.reply(_SETUP_INSTRUCTIONS, disable_web_page_preview=True)
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Confirm Redeploy", callback_data=f"rdply_go_{message.from_user.id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"rdply_cancel_{message.from_user.id}"),
    ]])
    await message.reply(
        "🔄 **Bot redeploy karna hai?**\n\n"
        "Railway pe naya deployment trigger hoga — bot kuch seconds ke liye "
        "restart hoga (jo bhi upload/download chal raha hai woh beech mein ruk sakta hai).",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^rdply_(go|cancel)_(\d+)$"))
async def redeploy_callback(client: Client, cb: CallbackQuery):
    action, uid_str = cb.matches[0].group(1), cb.matches[0].group(2)
    if cb.from_user.id != int(uid_str):
        await cb.answer("Yeh button tumhare liye nahi hai.", show_alert=True)
        return

    if action == "cancel":
        await cb.answer("Cancelled.")
        try:
            await cb.message.edit("❌ Redeploy cancelled.")
        except Exception:
            pass
        return

    await cb.answer("Redeploy trigger ho raha hai...")
    try:
        await cb.message.edit("⏳ **Redeploy trigger ho raha hai...**")
    except Exception:
        pass

    success, info = await _trigger_railway_redeploy()

    if success:
        try:
            await cb.message.edit(
                "✅ **Redeploy trigger ho gaya!**\n\n"
                "Railway pe naya build shuru ho gaya hai — bot kuch minute mein "
                "wapas online aa jayega."
            )
        except Exception:
            pass
    elif info == "config_missing":
        try:
            await cb.message.edit(_SETUP_INSTRUCTIONS, disable_web_page_preview=True)
        except Exception:
            pass
    else:
        try:
            await cb.message.edit(
                f"❌ **Redeploy fail ho gaya!**\n\n"
                f"Error: `{info[:200]}`\n\n"
                f"`RAILWAY_SERVICE_ID` / `RAILWAY_ENVIRONMENT_ID` / token sahi hain ya nahi check karo."
            )
        except Exception:
            pass
