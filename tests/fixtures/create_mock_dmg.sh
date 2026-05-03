#!/bin/bash
# テスト用 DMG を生成するスクリプト
set -e

OUTPUT="/tmp/git-lanes-test.dmg"
WORK_DIR=$(mktemp -d)
APP_DIR="$WORK_DIR/MockApp.app"

mkdir -p "$APP_DIR/Contents/MacOS"
printf '#!/bin/bash\necho MockApp\n' > "$APP_DIR/Contents/MacOS/MockApp"
chmod +x "$APP_DIR/Contents/MacOS/MockApp"

hdiutil create -size 5m -volname "Git Lanes Test" -srcfolder "$WORK_DIR" -ov -format UDZO "$OUTPUT"
rm -rf "$WORK_DIR"
echo "作成完了: $OUTPUT"
