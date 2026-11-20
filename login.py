"""Authorize a personal Telegram session using the local credentials."""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import socks
from telethon import TelegramClient

from tg_auto.config import load_config


def parse_proxy(url: str | None):
    """Convert the optional proxy URL to Telethon 1.x PySocks parameters."""
    if not url:
        return None

    parsed = urlparse(url)
    types = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
    }
    if parsed.scheme not in types or not parsed.hostname or parsed.port is None:
        raise ValueError("TG_AUTO_PROXY must be socks5://host:port, socks4://host:port, or http://host:port")
    return (
        types[parsed.scheme],
        parsed.hostname,
        parsed.port,
        True,  # Resolve DNS using the proxy when supported.
        parsed.username,
        parsed.password,
    )


async def main() -> None:
    config = load_config()
    async with TelegramClient(
        str(config.session_path),
        config.api_id,
        config.api_hash,
        proxy=parse_proxy(config.proxy_url),
    ) as client:
        me = await client.get_me()
        if me is None:
            raise RuntimeError("Telegram authorization did not return an account")
        print(f"Login succeeded. Telegram user ID: {me.id}")
        print(f"Private session directory: {config.session_path.parent}")


if __name__ == "__main__":
    asyncio.run(main())
