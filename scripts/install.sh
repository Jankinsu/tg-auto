#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
usage() {
  echo 'Usage: bash scripts/install.sh [--enable-timer]'
  echo 'Installs dependencies and systemd user units, preserving config and session.'
  echo 'Pass --enable-timer to activate daily scheduling.'
}
enable=0
for arg in "$@"; do
  case "$arg" in
    --enable-timer) enable=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
[[ $(id -u) -ne 0 ]] || { echo 'Run as your regular user, not sudo/root.' >&2; exit 1; }
for cmd in git python3 systemctl; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd; install git python3 python3-venv first." >&2; exit 1; }
done

repo="$HOME/apps/tg-auto"
config="$HOME/.config/tg-auto"
state="$HOME/.local/state/tg-auto"
units="$HOME/.config/systemd/user"
[[ -f "$repo/requirements.txt" && -f "$repo/login.py" && -f "$repo/systemd/tg-auto.service" ]] || {
  echo "Clone https://github.com/Jankinsu/tg-auto to $repo first." >&2; exit 1;
}
for dir in "$repo" "$config" "$state" "$units"; do
  [[ ! -L "$dir" ]] || { echo "Refusing symlinked directory: $dir" >&2; exit 1; }
done
mkdir -p "$config" "$state" "$units"
chmod 700 "$config" "$state"
if [[ ! -e "$config/settings.env" ]]; then
  cp "$repo/config/settings.env.example" "$config/settings.env"
  echo 'Created local settings.env; replace example_bot before enabling schedule.'
fi
[[ ! -L "$config/settings.env" ]] || { echo 'settings.env cannot be a symlink.' >&2; exit 1; }
chmod 600 "$config/settings.env"
for name in api_id api_hash; do
  path="$config/$name"
  [[ ! -L "$path" ]] || { echo "Refusing symlinked credential $path" >&2; exit 1; }
  if [[ ! -e "$path" ]]; then
    [[ -t 0 ]] || { echo "Missing $path; run installer interactively." >&2; exit 1; }
    if [[ "$name" == api_id ]]; then
      read -r -p 'Telegram API ID: ' value
      [[ "$value" =~ ^[0-9]+$ ]] || { echo 'API ID must be digits.' >&2; exit 1; }
    else
      read -r -s -p 'Telegram API hash (hidden): ' value
      printf '\n'
      [[ "$value" =~ ^[a-fA-F0-9]{32}$ ]] || { echo 'API hash should be 32 hex characters.' >&2; exit 1; }
    fi
    printf '%s\n' "$value" > "$path"
    unset value
  fi
  chmod 600 "$path"
done
if [[ ! -x "$repo/.venv/bin/python" ]]; then
  if ! python3 -m venv "$repo/.venv"; then
    echo 'Python venv failed. Debian 13: sudo apt install python3.13-venv; rerun installer.' >&2
    exit 1
  fi
fi
"$repo/.venv/bin/python" -m pip install -r "$repo/requirements.txt"
if [[ ! -f "$state/tg_auto.session" ]]; then
  [[ -t 0 ]] || { echo 'Run login.py interactively first, then rerun.' >&2; exit 1; }
  echo 'Authorizing Telegram session interactively...'
  (cd "$repo" && "$repo/.venv/bin/python" login.py)
fi
[[ -f "$state/tg_auto.session" ]] || { echo 'No session created.' >&2; exit 1; }
chmod 600 "$state/tg_auto.session"

for unit in tg-auto.service tg-auto.timer; do
  src="$repo/systemd/$unit"
  dst="$units/$unit"
  [[ ! -L "$dst" ]] || { echo "Refusing symlinked unit $dst" >&2; exit 1; }
  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then
    backup=$(mktemp "$dst.backup.XXXXXXXX")
    cp -p "$dst" "$backup"
    echo "Backed up previous unit to $backup"
  fi
  cp "$src" "$dst"
done
systemctl --user daemon-reload
echo 'User service and timer installed. Existing credentials and session preserved.'
if [[ "$enable" -eq 1 ]]; then
  bot_name=$(sed -n 's/^TG_AUTO_BOT_USERNAME=//p' "$config/settings.env" | tail -n 1 | tr -d '\r"')
  [[ -n "$bot_name" && "$bot_name" != example_bot && "$bot_name" != @example_bot ]] || {
    echo 'Set real TG_AUTO_BOT_USERNAME in settings.env before enabling timer.' >&2; exit 1;
  }
  systemctl --user enable --now tg-auto.timer
  echo 'Timer enabled.'
else
  echo 'Timer not enabled; after checking time and service, run: systemctl --user enable --now tg-auto.timer'
fi
echo 'Check: systemctl --user list-timers --all tg-auto.timer'
