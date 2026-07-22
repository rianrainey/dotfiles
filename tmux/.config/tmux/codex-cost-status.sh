#!/usr/bin/env bash

set -euo pipefail

cache_dir="${XDG_STATE_HOME:-$HOME/.config}/tmux"
cache_file="$cache_dir/.codex-cost-status"
cache_ttl=60

cache_is_fresh() {
  [[ -f "$cache_file" ]] || return 1
  local now modified
  now="$(date +%s)"
  modified="$(stat -f %m "$cache_file" 2>/dev/null || echo 0)"
  (( now - modified < cache_ttl ))
}

print_cache() {
  [[ -f "$cache_file" ]] && cat "$cache_file"
}

focused_pane_is_codex() {
  local pane_command pane_tty tty_name

  pane_command="$(tmux display-message -p -F '#{pane_current_command}' 2>/dev/null || true)"
  case "${pane_command##*/}" in
    codex|codex-*) return 0 ;;
  esac

  pane_tty="$(tmux display-message -p -F '#{pane_tty}' 2>/dev/null || true)"
  [[ -n "$pane_tty" ]] || return 1

  tty_name="${pane_tty#/dev/}"
  ps -t "$tty_name" -o comm= 2>/dev/null |
    awk -F/ '$NF == "codex" || $NF ~ /^codex-/ { found = 1 } END { exit !found }'
}

build_status() {
  local today month_start week_start report_start
  local business_days_per_week=5 business_days_per_month=20
  local daily_report session_report session_cost day_cost month_cost week_cost pace_cost

  today="$(date +%F)"
  month_start="$(date +%Y-%m-01)"
  week_start="$(date -v-6d +%F)"
  report_start="$month_start"
  [[ "$week_start" < "$month_start" ]] && report_start="$week_start"

  daily_report="$(ccusage codex daily --since "$report_start" --until "$today" --json 2>/dev/null)"
  session_report="$(ccusage codex session --json 2>/dev/null)"

  session_cost="$(
    jq -r '(.sessions // [] | max_by(.lastActivity) | .costUSD) // 0' <<<"$session_report" 2>/dev/null || echo 0
  )"

  read -r day_cost month_cost week_cost <<<"$(
    jq -r \
      --arg today "$today" \
      --arg month_start "$month_start" \
      --arg week_start "$week_start" \
      '
        .daily as $daily |
        ($daily | map(select(.date == $today) | .costUSD) | add // 0) as $day |
        ($daily | map(select(.date >= $month_start) | .costUSD) | add // 0) as $month |
        ($daily | map(select(.date >= $week_start) | .costUSD) | add // 0) as $week |
        [$day, $month, $week] | @tsv
      ' <<<"$daily_report" 2>/dev/null || printf '0\t0\t0'
  )"

  pace_cost="$(awk -v week="$week_cost" -v week_days="$business_days_per_week" -v month_days="$business_days_per_month" 'BEGIN { printf "%.2f", (week / week_days) * month_days }')"

  printf 'S $%.2f · D $%.2f · M $%.2f · Pace $%.2f/mo ' \
    "$session_cost" "$day_cost" "$month_cost" "$pace_cost"
}

main() {
  if ! focused_pane_is_codex; then
    exit 0
  fi

  if cache_is_fresh; then
    print_cache
    exit 0
  fi

  local status
  if ! status="$(build_status)"; then
    print_cache
    exit 0
  fi

  mkdir -p "$cache_dir"
  printf '%s\n' "$status" >"$cache_file"
  printf '%s\n' "$status"
}

main
