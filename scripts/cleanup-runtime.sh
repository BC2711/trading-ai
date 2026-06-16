#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

remove_inside_root() {
  target="$1"
  case "$target" in
    "$ROOT_DIR"/*)
      rm -rf "$target"
      printf '%s\n' "Removed $target"
      ;;
    *)
      printf '%s\n' "Refusing to remove path outside repository: $target" >&2
      exit 2
      ;;
  esac
}

remove_inside_root "$ROOT_DIR/.tmp"
remove_inside_root "$ROOT_DIR/backend/.tmp"
remove_inside_root "$ROOT_DIR/backend/.pytest_cache"
remove_inside_root "$ROOT_DIR/frontend/dist"
remove_inside_root "$ROOT_DIR/frontend/.vite"
remove_inside_root "$ROOT_DIR/coverage"

printf '%s\n' "Runtime cleanup completed."
