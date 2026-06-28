#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
START_SCRIPT="$ROOT_DIR/start-dev-macos.command"
STOP_SCRIPT="$ROOT_DIR/stop-dev-macos.command"
DEFAULT_TARGET="${EE_WMS_DEFAULT_TARGET:-api+web}"

usage() {
  cat <<EOF
macOS 一键重启脚本

用法:
  ./restart-dev-macos.command [all|backend|frontend|api|web|api+web]

说明:
  默认目标: ${DEFAULT_TARGET}
  all       重启后端 API + 前端
  backend   重启后端 API
  frontend  重启前端
  api       重启后端 API
  web       重启前端
  api+web   重启后端 API + 前端
EOF
}

main() {
  local target="${1:-$DEFAULT_TARGET}"

  if [[ "$target" == "-h" || "$target" == "--help" ]]; then
    usage
    exit 0
  fi

  if [[ ! -x "$START_SCRIPT" ]]; then
    echo "启动脚本不存在或不可执行: $START_SCRIPT" >&2
    exit 1
  fi

  if [[ ! -x "$STOP_SCRIPT" ]]; then
    echo "关闭脚本不存在或不可执行: $STOP_SCRIPT" >&2
    exit 1
  fi

  case "$target" in
    all|backend|frontend|api|web|api+web|default)
      ;;
    *)
      echo "不支持的参数: $target" >&2
      echo >&2
      usage
      exit 1
      ;;
  esac

  "$STOP_SCRIPT" "$target"
  sleep 0.5
  "$START_SCRIPT" "$target"
}

main "$@"
