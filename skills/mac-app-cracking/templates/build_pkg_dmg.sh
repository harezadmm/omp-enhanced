#!/bin/bash
# ============================================================
# MAC APP — PKG DMG BUILDER TEMPLATE
# ============================================================
# Customize: APP_NAME, PKG_ID, version detection.
# Builds self-contained .pkg inside .dmg
# ============================================================

set -e

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'; RED='\033[0;31m'

APP_NAME="REPLACE_APP_NAME"
PKG_ID="REPLACE_PKG_ID"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${2:-$HOME/Desktop}"
ORIGINAL_DMG="${1:-}"

echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║  ${APP_NAME} — PKG DMG BUILDER       ║"
echo "  ║  LTX-QUASAR                           ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ─── Find source ─────────────────────────────────────────
APP_SOURCE=""
SHOULD_UNMOUNT=0

if [ -n "$ORIGINAL_DMG" ] && [ -f "$ORIGINAL_DMG" ]; then
    echo -e "${GREEN}[1/7] Mounting source DMG...${NC}"
    MOUNT_OUT=$(hdiutil attach "$ORIGINAL_DMG" -nobrowse -readonly 2>&1)
    MOUNT_POINT=$(echo "$MOUNT_OUT" | grep "^/Volumes/" | head -1)
    if [ -z "$MOUNT_POINT" ]; then echo -e "${RED}✗ Mount failed${NC}"; exit 1; fi
    APP_SOURCE=$(find "$MOUNT_POINT" -name "*.app" -maxdepth 2 | head -1)
    if [ -z "$APP_SOURCE" ]; then hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true; echo -e "${RED}✗ No .app${NC}"; exit 1; fi
    SHOULD_UNMOUNT=1
elif [ -d "/Applications/${APP_NAME}.app" ]; then
    APP_SOURCE="/Applications/${APP_NAME}.app"
else
    echo -e "${RED}✗ No source. Install app or provide DMG.${NC}"; exit 1
fi

VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$APP_SOURCE/Contents/Info.plist" 2>/dev/null || echo "1.0")
echo -e "  ${GREEN}✓ Source: ${APP_NAME} v${VERSION}${NC}"

# ─── Workspace ───────────────────────────────────────────
WORK_DIR=$(mktemp -d -t macapp-pkg)
ROOT_DIR="$WORK_DIR/root"; mkdir -p "$ROOT_DIR/Applications"
SCRIPTS_DIR="$WORK_DIR/scripts"; mkdir -p "$SCRIPTS_DIR"

# ─── Copy + strip app ────────────────────────────────────
echo -e "${GREEN}[2/7] Preparing app...${NC}"
cp -R "$APP_SOURCE" "$ROOT_DIR/Applications/${APP_NAME}.app"
TARGET_APP="$ROOT_DIR/Applications/${APP_NAME}.app"
[ "$SHOULD_UNMOUNT" -eq 1 ] && hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true

codesign --remove-signature "$TARGET_APP" 2>/dev/null || true
rm -rf "$TARGET_APP/Contents/_CodeSignature" 2>/dev/null || true
rm -f "$TARGET_APP/Contents/CodeResources" 2>/dev/null || true
xattr -cr "$TARGET_APP" 2>/dev/null || true
codesign --force --deep --sign - "$TARGET_APP" 2>/dev/null || true
echo -e "  ${GREEN}✓ Stripped + signed${NC}"

# ─── Copy postinstall ────────────────────────────────────
echo -e "${GREEN}[3/7] Preparing postinstall...${NC}"
if [ -f "$SCRIPT_DIR/postinstall.sh" ]; then
    cp "$SCRIPT_DIR/postinstall.sh" "$SCRIPTS_DIR/postinstall"
else
    echo -e "${RED}✗ postinstall.sh missing${NC}"; exit 1
fi
chmod +x "$SCRIPTS_DIR/postinstall"
echo -e "  ${GREEN}✓ Ready${NC}"

# ─── Build .pkg ──────────────────────────────────────────
echo -e "${GREEN}[4/7] Building .pkg...${NC}"
PKG_PATH="$WORK_DIR/${APP_NAME// /_}_${VERSION}_Cracked.pkg"
pkgbuild --root "$ROOT_DIR" --install-location "/" --scripts "$SCRIPTS_DIR" \
    --identifier "$PKG_ID" --version "$VERSION" "$PKG_PATH" 2>&1
PKG_SIZE=$(du -h "$PKG_PATH" | cut -f1)
echo -e "  ${GREEN}✓ PKG: ${PKG_SIZE}${NC}"

# ─── Wrap in DMG ─────────────────────────────────────────
echo -e "${GREEN}[5/7] Creating DMG...${NC}"
DMG_WORK="$WORK_DIR/dmg"; mkdir -p "$DMG_WORK"
cp "$PKG_PATH" "$DMG_WORK/"

cat > "$DMG_WORK/📖 README.txt" << README
====================================
 ${APP_NAME} — PRO LIFETIME
 v${VERSION} · Cracked by LTX-QUASAR
====================================

 INSTALL:
   ① Double-click ${APP_NAME// /_}_${VERSION}_Cracked.pkg
   ② Enter password (needs sudo for /etc/hosts)
   ③ Done — Pro active!

 Gatekeeper blocking?
   System Settings → Privacy & Security → Open Anyway
====================================
README

DMG_OUT="$OUTPUT_DIR/${APP_NAME// /_}_${VERSION}_Cracked.dmg"
rm -f "$DMG_OUT" 2>/dev/null || true
hdiutil create -volname "${APP_NAME} Pro" -srcfolder "$DMG_WORK" -ov -format UDZO "$DMG_OUT" 2>&1

DMG_SIZE=$(du -h "$DMG_OUT" | cut -f1)
echo -e "  ${GREEN}✓ DMG: ${DMG_SIZE}${NC}"

# ─── Cleanup ─────────────────────────────────────────────
rm -rf "$WORK_DIR" 2>/dev/null || true

echo ""
echo -e "  ${CYAN}${BOLD}✅ Self-contained DMG ready${NC}"
echo -e "  ${BOLD}File:${NC} ${GREEN}$DMG_OUT${NC}"
echo -e "  ${BOLD}Use:${NC} Mount → double-click .pkg → Pro"
echo ""