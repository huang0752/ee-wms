#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend/web"
RUNTIME_DIR="$ROOT_DIR/.dev-runtime"
PID_DIR="$RUNTIME_DIR/pids"
WINDOW_DIR="$RUNTIME_DIR/windows"
LOG_DIR="$RUNTIME_DIR/logs"

DEFAULT_TARGET="${EE_WMS_DEFAULT_TARGET:-api+web}"
UV_BIN=""
PNPM_BIN=""

usage() {
  cat <<EOF
macOS 一键启动脚本

用法:
  ./start-dev-macos.command [all|backend|frontend|api|web|api+web]

说明:
  默认目标: ${DEFAULT_TARGET}
  all       启动后端 API + 前端
  backend   启动后端 API
  frontend  启动前端
  api       启动后端 API，默认 http://localhost:41232
  web       启动前端，默认 http://localhost:41291
  api+web   启动后端 API + 前端

首次使用前请先安装依赖:
  cd backend && uv sync
  cd frontend/web && pnpm install

后端启动前会自动执行:
  uv run python main.py upgrade --env=dev

关闭服务:
  ./stop-dev-macos.command [同样参数]

终端:
  使用 macOS 自带 Terminal，不再启动 Ghostty
EOF
}

ensure_dir() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "目录不存在: $dir" >&2
    exit 1
  fi
}

ensure_file() {
  local file="$1"
  if [[ ! -e "$file" ]]; then
    echo "文件不存在: $file" >&2
    exit 1
  fi
}

ensure_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "命令不存在: $command_name" >&2
    exit 1
  fi
}

ensure_runtime_dirs() {
  mkdir -p "$PID_DIR" "$WINDOW_DIR" "$LOG_DIR"
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

service_already_running() {
  local service="$1"
  local title="$2"
  local pid_file="$PID_DIR/$service.pid"
  local pid

  pid="$(read_pid "$pid_file")"
  if [[ -n "$pid" ]] && is_pid_running "$pid"; then
    echo "$title 已在运行，PID: $pid"
    return 0
  fi

  rm -f "$pid_file" "$WINDOW_DIR/$service.terminal"
  return 1
}

build_shell_cmd() {
  local title="$1"
  local dir="$2"
  local pid_file="$3"
  local log_file="$4"
  local cmd="$5"
  local title_format

  title_format=$'\033]0;%s\007\033]1;%s\007'

  printf "cd %q && unset VIRTUAL_ENV && printf %q %q %q && echo \$\$ > %q && exec > >(/usr/bin/tee -a %q) 2>&1 && %s" \
    "$dir" \
    "$title_format" \
    "$title" \
    "$title" \
    "$pid_file" \
    "$log_file" \
    "$cmd"
}

record_terminal_tab() {
  local service="$1"
  local output="$2"
  local ref_file="$WINDOW_DIR/$service.terminal"

  if [[ "$output" =~ ^([0-9]+)\|(.+)$ ]]; then
    printf '%s|%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" > "$ref_file"
  fi
}

open_terminal_window() {
  local service="$1"
  local title="$2"
  local dir="$3"
  local cmd="$4"
  local shell_cmd
  local pid_file="$PID_DIR/$service.pid"
  local log_file="$LOG_DIR/$service.log"
  local terminal_output

  ensure_dir "$dir"
  ensure_runtime_dirs

  if service_already_running "$service" "$title"; then
    return 0
  fi

  shell_cmd="$(build_shell_cmd "$title" "$dir" "$pid_file" "$log_file" "$cmd")"

  terminal_output="$(osascript - "$shell_cmd" <<'APPLESCRIPT'
on run argv
  tell application "Terminal"
    activate
    do script item 1 of argv
    delay 0.2
    return ((id of front window) as text) & "|" & (tty of selected tab of front window)
  end tell
end run
APPLESCRIPT
)"

  record_terminal_tab "$service" "$terminal_output"
  echo "已启动: $title (Terminal)"
}

ensure_backend_ready() {
  ensure_dir "$BACKEND_DIR"
  ensure_file "$BACKEND_DIR/main.py"
  ensure_command "uv"
  UV_BIN="$(command -v uv)"
}

ensure_frontend_ready() {
  ensure_dir "$FRONTEND_DIR"
  ensure_file "$FRONTEND_DIR/package.json"
  ensure_command "pnpm"
  PNPM_BIN="$(command -v pnpm)"
}

launch_api() {
  ensure_backend_ready
  local uv_bin
  uv_bin="$(printf '%q' "$UV_BIN")"
  open_terminal_window \
    "api" \
    "EE WMS Backend API" \
    "$BACKEND_DIR" \
    "$uv_bin run python main.py upgrade --env=dev && exec $uv_bin run python main.py run --env=dev"
}

launch_web() {
  ensure_frontend_ready
  local pnpm_bin
  pnpm_bin="$(printf '%q' "$PNPM_BIN")"
  open_terminal_window \
    "web" \
    "EE WMS Frontend" \
    "$FRONTEND_DIR" \
    "exec $pnpm_bin dev --host 0.0.0.0"
}

main() {
  local target="${1:-$DEFAULT_TARGET}"

  if [[ "$target" == "-h" || "$target" == "--help" ]]; then
    usage
    exit 0
  fi

  command -v osascript >/dev/null 2>&1 || {
    echo "这个脚本只能在 macOS 上运行，需要 osascript。" >&2
    exit 1
  }

  case "$target" in
    all|api+web|default)
      launch_api
      sleep 1
      launch_web
      ;;
    backend|api)
      launch_api
      ;;
    frontend|web)
      launch_web
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
