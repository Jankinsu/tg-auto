# tg-auto

A lightweight, extensible Telegram automation toolkit powered by Python and Telethon.

## Design

This project follows the Debian layout of `tdl-bot`:

| Location | Purpose |
| --- | --- |
| `~/apps/tg-auto/` | GitHub-managed source code |
| `~/.config/tg-auto/api_id` | Telegram application API ID (one line) |
| `~/.config/tg-auto/api_hash` | Telegram application API hash (one line) |
| `~/.config/tg-auto/settings.env` | Non-secret runtime options |
| `~/.local/state/tg-auto/` | Private Telethon session and runtime state |

Keep all credentials and `*.session` files **outside Git**.

## First setup on Debian 13

Prerequisites: Python 3, `python3-venv`, Git, and Telegram API credentials already saved in the above files.

```bash
cd ~/apps
git clone git@github.com:Jankinsu/tg-auto.git
cd tg-auto
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Configure `~/.config/tg-auto/settings.env` using `config/settings.env.example` as a reference. If using Throne on the same Debian host, `TG_AUTO_PROXY=socks5://127.0.0.1:2080` is the intended example.

To authorize the Telegram personal user account (run interactively):

```bash
.venv/bin/python login.py
```

Telethon may ask for your phone, Telegram login code, and two-step verification password. The resulting session is saved at `~/.local/state/tg-auto/tg_auto.session` and should be chmod 600. This login is independent of existing `tdl` sessions.

## Inspect bot buttons (read-only)

After successful first login, set the target in `~/.config/tg-auto/settings.env`:

```dotenv
TG_AUTO_BOT_USERNAME=your_real_bot_username
```

Then pull and inspect recent messages:

```bash
git pull
.venv/bin/python inspect_buttons.py
# Alternatively, without editing settings.env:
.venv/bin/python inspect_buttons.py --bot @your_real_bot_username
```

This script **does not send messages or click buttons**. It displays message IDs, dates and visible button texts/types only; callback payloads and URLs remain hidden. If nothing appears, manually send `/start` to the bot and rerun; to inspect a secondary menu, open that menu manually first.

## Current scope

Stage 1: configuration and manual login completed. Stage 2: read-only inspection of existing bot messages and inline keyboards. No automated claims or systemd timer yet.

Next: implement the verified two-step menu navigation and claim flow, then user-level systemd timer.
