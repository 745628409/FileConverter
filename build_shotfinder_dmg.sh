#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$ROOT_DIR/MacOSShotFinder"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "[ERROR] 未找到目录: $TARGET_DIR"
  echo "请先确认你在 FileConverter 仓库根目录执行该脚本。"
  exit 1
fi

cd "$TARGET_DIR"
chmod +x build_macos_installer.sh
./build_macos_installer.sh
