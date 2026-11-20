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

## Two-step daily token check-in

The bot's first-page callback **only navigates** to the reward submenu. The second-page callback performs the actual claim. The bot may *edit the same message ID* rather than creating a new message, so the script re-fetches the message after each click.

Before enabling any automatic schedule, run the navigation-only test:

```bash
cd ~/apps/tg-auto
git pull
.venv/bin/python checkin.py --navigate-only
```

This sends `/start` and clicks **only** the first-page `点击领取余额` navigation callback (or an unambiguous already-claimed reward entry). It checks that the reward submenu appeared but **never presses the daily claim button**.

After confirming the output matches the Telegram client, explicitly claim:

```bash
.venv/bin/python checkin.py --execute
```

The script will claim only if the submenu offers one unambiguous `点击领取每日…token` callback, and it verifies the updated submenu says already claimed. If it cannot confirm the result, it exits with an error rather than blindly retrying.

## User-level systemd timer (Debian)

The checked-in `systemd/tg-auto.service` and `systemd/tg-auto.timer` follow the same user-level service pattern as `tdl-bot`. The timer is an **example** (09:10 in the Debian host's local timezone, plus up to 5 minutes of randomized delay). Verify `timedatectl` and change the timer's `OnCalendar` if needed before enabling it.

```bash
cd ~/apps/tg-auto
git pull
mkdir -p ~/.config/systemd/user
cp systemd/tg-auto.service systemd/tg-auto.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemd-analyze --user calendar '*-*-* 09:10:00'
systemctl --user list-timers --all
```

The unit is not enabled by copying it. To test the same code path manually (including when today's reward is already claimed):

```bash
systemctl --user start tg-auto.service
systemctl --user status tg-auto.service
journalctl --user -u tg-auto.service -n 50 --no-pager
```

Only after verifying the schedule and successful manual service run, enable automatic daily execution:

```bash
systemctl --user enable --now tg-auto.timer
systemctl --user list-timers --all tg-auto.timer
```

To keep user services and timers running when logged out and at system boot, the system may require lingering:

```bash
loginctl show-user "$USER" -p Linger
# If Linger=no and you want the timer to run without a login session:
sudo loginctl enable-linger "$USER"
```

To pause scheduling: `systemctl --user disable --now tg-auto.timer`. The service is intentionally `Type=oneshot` with no automatic retry; an uncertain claim result is logged as an error rather than blindly retried. `Persistent=true` runs a missed calendar occurrence when the timer is activated again, so review that behavior if you prefer to skip missed days.

The timer's schedule uses **Debian's local time zone**, not Telegram's reset timezone. If the bot resets on a different clock, adjust the schedule accordingly. Never run an interactive login program from systemd.
