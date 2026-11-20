"""Read the local Debian configuration outside the Git repository."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

CONFIG_DIR = Path.home() / ".config" / "tg-auto"
STATE_DIR = Path.home() / ".local" / "state" / "tg-auto"


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    session_path: Path
    proxy_url: str | None


def _credential(name: str) -> str:
    path = CONFIG_DIR / name
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"Credential file is empty: {path}")
    if os.name == "posix" and path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(f"Credential file permissions are too broad: {path}; use chmod 600")
    return value


def load_config() -> Config:
    api_id = int(_credential("api_id"))
    api_hash = _credential("api_hash")

    # Systemd EnvironmentFile variables override local settings.env when present.
    settings = dotenv_values(CONFIG_DIR / "settings.env")
    proxy_url = os.environ.get("TG_AUTO_PROXY", settings.get("TG_AUTO_PROXY") or "")
    proxy_url = proxy_url.strip() or None

    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE_DIR.chmod(0o700)
    return Config(
        api_id=api_id,
        api_hash=api_hash,
        session_path=STATE_DIR / "tg_auto",
        proxy_url=proxy_url,
    )
