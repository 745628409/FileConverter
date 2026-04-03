#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MacOSShotFinder"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
SPEC_FILE="$ROOT_DIR/${APP_NAME}.spec"
DMG_DIR="$ROOT_DIR/release"
DMG_FILE="$DMG_DIR/${APP_NAME}-macOS10.14.dmg"

cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 不存在，请先安装 Python 3.8+"
  exit 1
fi

if ! command -v pip3 >/dev/null 2>&1; then
  echo "[ERROR] pip3 不存在，请先安装 pip"
  exit 1
fi

if [[ "$(uname)" != "Darwin" ]]; then
  echo "[ERROR] 该打包脚本仅支持在 macOS 上运行"
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "[ERROR] 缺少 hdiutil，无法生成 dmg"
  exit 1
fi

echo "[1/5] 安装构建依赖"
pip3 install -r requirements.txt -r requirements-build.txt

echo "[2/5] 清理旧构建"
rm -rf "$DIST_DIR" "$BUILD_DIR" "$SPEC_FILE" "$DMG_DIR"

echo "[3/5] 使用 PyInstaller 构建 .app"
pyinstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "org.local.macosshotfinder" \
  src/app.py

APP_PATH="$DIST_DIR/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "[ERROR] 未找到生成的 .app: $APP_PATH"
  exit 1
fi

echo "[4/5] 组装 dmg 内容"
mkdir -p "$DMG_DIR"
cp -R "$APP_PATH" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"

echo "[5/5] 生成 dmg"
hdiutil create \
  -volname "$APP_NAME Installer" \
  -srcfolder "$DMG_DIR" \
  -ov \
  -format UDZO \
  "$DMG_FILE"

echo
echo "构建完成：$DMG_FILE"
echo "把 dmg 发给用户后，双击拖拽到 Applications 即可安装。"
