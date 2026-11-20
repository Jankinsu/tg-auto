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

## Current scope

Stage 1: config validation and manual login **only**. No bot buttons are clicked, no claims are performed, and no systemd timer is enabled yet.

Next: read-only inspection of the target bot's two-level inline keyboard. Subsequent stages will implement the precise navigation and claim flow, verify the response, then add a user-level systemd timer.
