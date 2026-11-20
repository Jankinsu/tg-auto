"""Two-step Telegram bot daily token check-in.

Use --navigate-only to test the first menu callback without claiming.
Use --execute to perform the daily claim.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

from telethon import TelegramClient

from inspect_buttons import target_bot
from login import parse_proxy
from tg_auto.config import load_config

ENTRY_TEXT = "点击领取余额"
DAILY_PATTERN = re.compile(r"^点击领取每日\s*\d+(?:\.\d+)?万?\s*token$", re.IGNORECASE)
POLL_INTERVAL = 0.7
WAIT_SECONDS = 15


def clickable_buttons(message):
    if message is None or not message.buttons:
        return []
    return [button for row in message.buttons for button in row if button.data is not None]


def signature(message):
    return tuple((b.text, b.data) for b in clickable_buttons(message))


def find_entry(message):
    buttons = clickable_buttons(message)
    matches = [b for b in buttons if b.text.strip() == ENTRY_TEXT]
    if len(matches) == 1:
        return matches[0]
    # The home button sometimes displays today's claim status, but remains the
    # navigation entry. Only treat it as such when it is unambiguous.
    matches = [b for b in buttons if "已领取" in b.text and "奖励" in b.text]
    if len(matches) == 1:
        return matches[0]
    return None


def daily_state(message):
    buttons = clickable_buttons(message)
    # Identify the secondary screen by its 'return to main panel' control.
    if not any(b.text.strip() == "返回主面板" for b in buttons):
        return "not-secondary", None
    choices = [b for b in buttons if DAILY_PATTERN.fullmatch(b.text.strip())]
    claimed = [b for b in buttons if "已领取" in b.text and ("次日" in b.text or "每日" in b.text or "token" in b.text.lower())]
    if len(claimed) == 1:
        return "already-claimed", None
    if len(choices) == 1:
        return "available", choices[0]
    return "unknown", None


async def most_recent_bot_message(client, entity, min_id=0):
    messages = await client.get_messages(entity, limit=10)
    for message in messages:
        if not message.out and message.id >= min_id and message.buttons:
            return message
    return None


async def wait_for_menu(client, entity, start_id, timeout=WAIT_SECONDS):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        msg = await most_recent_bot_message(client, entity, min_id=start_id)
        if msg:
            return msg
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError("No new bot menu appeared after /start")


async def wait_for_secondary(client, entity, original_id, timeout=WAIT_SECONDS):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        msg = await client.get_messages(entity, ids=original_id)
        if daily_state(msg)[0] != "not-secondary":
            return msg
        # Some bots send another message instead of editing the current one.
        newer = await most_recent_bot_message(client, entity, min_id=original_id + 1)
        if newer and daily_state(newer)[0] != "not-secondary":
            return newer
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError("Could not confirm the secondary menu")


async def wait_for_claimed(client, entity, message_id, timeout=WAIT_SECONDS):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        msg = await client.get_messages(entity, ids=message_id)
        state, _ = daily_state(msg)
        if state == "already-claimed":
            return
        newer = await most_recent_bot_message(client, entity, min_id=message_id + 1)
        if newer and daily_state(newer)[0] == "already-claimed":
            return
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError("Clicked the daily claim but could not verify the claimed state")


async def checkin(bot_name: str, navigate_only: bool) -> None:
    os.umask(0o077)
    cfg = load_config()
    client = TelegramClient(
        str(cfg.session_path), cfg.api_id, cfg.api_hash,
        proxy=parse_proxy(cfg.proxy_url),
    )
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session is not authorized. Run login.py interactively.")
        entity = await client.get_entity(bot_name)
        if not getattr(entity, "bot", False):
            raise ValueError("Target is not a Telegram bot")

        print(f"[{datetime.now(timezone.utc).isoformat()}] Bot: {bot_name}", flush=True)
        previous = await client.get_messages(entity, limit=1)
        baseline = previous[0].id if previous else 0
        sent = await client.send_message(entity, "/start")
        home = await wait_for_menu(client, entity, sent.id)
        print(f"Home menu: message {home.id}")
        entry = find_entry(home)
        if entry is None:
            raise RuntimeError("Could not uniquely identify the home-page reward entry")
        # Use the message-bound button rather than sending raw callback data.
        await entry.click()
        secondary = await wait_for_secondary(client, entity, home.id)
        state, claim_button = daily_state(secondary)
        print(f"Secondary menu: message {secondary.id}; status={state}")
        if state == "unknown":
            raise RuntimeError("Secondary menu format changed; no claim was attempted")
        if navigate_only:
            print("Navigation test complete. Did not click the daily claim button.")
            return
        if state == "already-claimed":
            print("Already claimed today; no duplicate claim attempted.")
            return
        if state != "available" or claim_button is None:
            raise RuntimeError("The daily claim button was not uniquely identified")
        await claim_button.click()
        await wait_for_claimed(client, entity, secondary.id)
        print("Daily claim verified: secondary menu reports already claimed.")
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram two-step daily claim")
    parser.add_argument("--bot", help="Override TG_AUTO_BOT_USERNAME in local settings.env")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--navigate-only", action="store_true", help="Open the secondary menu; do not claim")
    mode.add_argument("--execute", action="store_true", help="Attempt one daily claim and verify result")
    args = parser.parse_args()
    try:
        asyncio.run(checkin(target_bot(args.bot), args.navigate_only))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
