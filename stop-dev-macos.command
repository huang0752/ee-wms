#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.dev-runtime"
PID_DIR="$RUNTIME_DIR/pids"
WINDOW_DIR="$RUNTIME_DIR/windows"

DEFAULT_TARGET="${EE_WMS_DEFAULT_TARGET:-api+web}"

usage() {
  cat <<EOF
macOS 一键停止脚本

用法:
  ./stop-dev-macos.command [all|backend|frontend|api|web|api+web]

说明:
  默认目标: ${DEFAULT_TARGET}
  all       停止后端 API + 前端
  backend   停止后端 API
  frontend  停止前端
  api       停止后端 API
  web       停止前端
  api+web   停止后端 API + 前端
EOF
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' < "$pid_file"
  fi
}

is_pid_running() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

close_terminal_tab() {
  local service="$1"
  local ref_file="$WINDOW_DIR/$service.terminal"
  local ref
  local window_id
  local tty_value

  if [[ ! -f "$ref_file" ]]; then
    return 0
  fi

  ref="$(tr -d '[:space:]' < "$ref_file")"
  if [[ "$ref" =~ ^([0-9]+)\|(.+)$ ]]; then
    window_id="${BASH_REMATCH[1]}"
    tty_value="${BASH_REMATCH[2]}"

    osascript - "$window_id" "$tty_value" <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run argv
  set windowId to item 1 of argv as integer
  set ttyValue to item 2 of argv as text

  tell application "Terminal"
    if exists window id windowId then
      try
        set targetTab to first tab of window id windowId whose tty is ttyValue
        close targetTab saving no
      on error
        try
          close (window id windowId) saving no
        end try
      end try
    end if
  end tell
end run
APPLESCRIPT
  fi

  rm -f "$ref_file"
}

stop_pid_tree() {
  local pid="$1"
  local child

  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    stop_pid_tree "$child"
  done

  kill "$pid" >/dev/null 2>&1 || true
}

force_stop_port() {
  local port="$1"
  local pids

  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    kill $pids >/dev/null 2>&1 || true
    sleep 0.3
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

stop_service() {
  local service="$1"
  local title="$2"
  local port="$3"
  local pid_file="$PID_DIR/$service.pid"
  local pid
  local stopped=0

  pid="$(read_pid "$pid_file")"
  if [[ "$pid" == "$$" || "$pid" == "${BASHPID:-}" || "$pid" == "$PPID" ]]; then
    echo "$title 的 PID 记录指向当前停止脚本，已清理旧记录"
    rm -f "$pid_file"
    pid=""
  fi

  if [[ -n "$pid" ]] && is_pid_running "$pid"; then
    stop_pid_tree "$pid"

    for _ in 1 2 3 4 5 6; do
      if ! is_pid_running "$pid"; then
        stopped=1
        break
      fi
      sleep 0.5
    done

    if [[ "$stopped" -eq 0 ]] && is_pid_running "$pid"; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi

    echo "已停止: $title"
  else
    echo "$title 未通过 PID 记录运行"
  fi

  force_stop_port "$port"
  close_terminal_tab "$service"
  rm -f "$pid_file"
}

main() {
  local target="${1:-$DEFAULT_TARGET}"

  if [[ "$target" == "-h" || "$target" == "--help" ]]; then
    usage
    exit 0
  fi

  case "$target" in
    all|api+web|default)
      stop_service "web" "EE WMS Frontend" "41291"
      stop_service "api" "EE WMS Backend API" "41232"
      ;;
    backend|api)
      stop_service "api" "EE WMS Backend API" "41232"
      ;;
    frontend|web)
      stop_service "web" "EE WMS Frontend" "41291"
      ;;
    *)
      echo "不支持的参数: $target" >&2
      echo >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
