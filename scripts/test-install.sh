#!/usr/bin/env bash
# アップデートインストーラーのモック動作を検証する。
set -euo pipefail

touch /tmp/git-lanes-test.dmg
GL_MOCK_FROZEN=1 GL_MOCK_DMG=/tmp/git-lanes-test.dmg \
  uv run python -c 'from backend.services.update_installer import install_update; print(install_update())'
