"""Read-only inspection of inline buttons in recent messages from a Telegram bot.

Never sends /start, clicks buttons, or claims rewards.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import dotenv_values
from telethon import TelegramClient
from telethon.tl.custom import Button

from login import parse_proxy
from tg_auto.config import CONFIG_DIR, load_config


def target_bot(argument: str | None) -> str:
    settings = dotenv_values(CONFIG_DIR / "settings.env")
    value = (argument or os.environ.get("TG_AUTO_BOT_USERNAME")
             or settings.get("TG_AUTO_BOT_USERNAME") or "").strip()
    if not value or value in ("example_bot", "@example_bot"):
        raise ValueError(
            "Specify the real bot username with --bot @name or "
            "TG_AUTO_BOT_USERNAME in ~/.config/tg-auto/settings.env"
        )
    return value if value.startswith("@") else "@" + value


async def inspect(bot_name: str, count: int) -> None:
    os.umask(0o077)
    cfg = load_config()
    if not Path(str(cfg.session_path) + ".session").is_file():
        raise RuntimeError("No existing session. Run login.py interactively first.")

    async with TelegramClient(
        str(cfg.session_path), cfg.api_id, cfg.api_hash,
        proxy=parse_proxy(cfg.proxy_url),
    ) as client:
        entity = await client.get_entity(bot_name)
        if not getattr(entity, "bot", False):
            raise ValueError("The specified username does not belong to a Telegram bot")

        messages = await client.get_messages(entity, limit=count)
        print(f"Inspecting {len(messages)} recent messages from {bot_name} (read-only)")
        found = 0
        for msg in messages:
            if not msg.out and msg.buttons:
                found += 1
                print(f"\nMessage ID: {msg.id} | Date (UTC): {msg.date.isoformat()}")
                for row_number, row in enumerate(msg.buttons, 1):
                    for col_number, button in enumerate(row, 1):
                        # Never disclose callback payloads or URL parameters in logs.
                        if button.data is not None:
                            kind = "callback"
                        elif button.url is not None:
                            kind = "url"
                        else:
                            kind = "other"
                        print(f"  [{row_number},{col_number}] {kind}: {button.text!r}")

        if not found:
            print("No inline buttons found. Open the bot in Telegram and send /start manually, then rerun.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect bot menus without clicking buttons")
    parser.add_argument("--bot", help="Telegram bot username, e.g. @example_bot")
    parser.add_argument("--limit", type=int, default=10, help="Recent message count (1-50)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")
    asyncio.run(inspect(target_bot(args.bot), args.limit))


if __name__ == "__main__":
    main()
