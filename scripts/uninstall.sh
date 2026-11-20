#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
usage() {
  echo 'Usage: bash scripts/uninstall.sh [--purge] [--yes]'
  echo 'Default removes systemd units only. --purge also deletes code/config/session.'
  echo '--yes skips confirmation for --purge. Remote GitHub repository is untouched.'
}
purge=0
yes=0
for arg in "$@"; do
  case "$arg" in
    --purge) purge=1 ;;
    --yes) yes=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
[[ $(id -u) -ne 0 ]] || { echo 'Run as regular user, not sudo/root.' >&2; exit 1; }
repo="$HOME/apps/tg-auto"
config="$HOME/.config/tg-auto"
state="$HOME/.local/state/tg-auto"
units="$HOME/.config/systemd/user"
for dir in "$repo" "$config" "$state" "$units"; do
  [[ ! -L "$dir" ]] || { echo "Refusing symlinked directory: $dir" >&2; exit 1; }
done
if [[ "$purge" -eq 1 && "$yes" -ne 1 ]]; then
  [[ -t 0 ]] || { echo 'Noninteractive purge requires --purge --yes.' >&2; exit 1; }
  printf 'Permanent local deletion:\n  %s\n  %s\n  %s\n' "$repo" "$config" "$state"
  echo 'Includes Telegram session and credentials; remote GitHub unaffected.'
  read -r -p 'Type DELETE tg-auto to confirm: ' response
  [[ "$response" == 'DELETE tg-auto' ]] || { echo 'Cancelled.'; exit 1; }
fi
if command -v systemctl >/dev/null; then
  systemctl --user disable --now tg-auto.timer 2>/dev/null || true
  systemctl --user stop tg-auto.service 2>/dev/null || true
fi
for unit in tg-auto.service tg-auto.timer; do
  [[ ! -L "$units/$unit" ]] || { echo "Refusing symlinked unit: $unit" >&2; exit 1; }
  rm -f -- "$units/$unit"
done
if command -v systemctl >/dev/null; then
  systemctl --user daemon-reload
  systemctl --user reset-failed tg-auto.service tg-auto.timer 2>/dev/null || true
fi
echo 'Removed tg-auto systemd service and timer.'
if [[ "$purge" -eq 1 ]]; then
  cd "$HOME"
  rm -rf -- "$repo" "$config" "$state"
  for backup in "$units"/tg-auto.service.backup.* "$units"/tg-auto.timer.backup.*; do
    if [[ -f "$backup" && ! -L "$backup" ]]; then rm -f -- "$backup"; fi
  done
  echo 'Deleted local code, settings, API credentials, and Telegram session.'
  echo 'Deleting the local session does NOT revoke its authorization on Telegram servers.'
else
  echo 'Preserved local code, settings, credentials, and session.'
fi
echo 'Unchanged: tdl-bot, Throne, QingLong, shared Python/apt packages, linger, remote GitHub, journal history.'
