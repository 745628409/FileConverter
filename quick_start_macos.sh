#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$ROOT_DIR/MacOSShotFinder"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[ERROR] 当前目录不是 FileConverter 仓库根目录。"
  echo "[HINT] 请先下载完整项目，再进入项目根目录后执行本脚本。"
  echo "[HINT] 你当前目录: $ROOT_DIR"
  exit 1
fi

cd "$PROJECT_DIR"

echo "[INFO] 当前项目目录: $(pwd)"

echo "[STEP] 检查 Python3"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 没有 python3，请先安装 Python 3.8+"
  exit 1
fi

echo "[STEP] 检查 ffmpeg"
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[ERROR] 没有 ffmpeg，请先执行: brew install ffmpeg"
  exit 1
fi

echo "[STEP] 进入打包流程"
chmod +x build_macos_installer.sh
./build_macos_installer.sh
