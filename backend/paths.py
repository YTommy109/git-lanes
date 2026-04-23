"""アプリケーションが参照するファイルシステム上のパスを解決する。"""

import os
from pathlib import Path


def data_dir() -> Path:
    """キャッシュ DB を置くディレクトリを返す。

    環境変数 ``GIT_LANES_DATA_DIR`` があればそれを優先し、なければ macOS の
    Application Support 配下を使う。

    Returns:
        ディレクトリパス（存在しなければ呼び出し側で mkdir する）。
    """
    override = os.environ.get("GIT_LANES_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / "Library" / "Application Support" / "git-lanes"


def primary_db_path() -> Path:
    """アプリ全体で共有する SQLite ファイルパスを返す。

    最小縦スライスではリポジトリ間で ``path`` の一意性を保つため、単一 DB に
    集約する。将来シャード化する場合はここを差し替える。

    Returns:
        ``{data_dir}/git-lanes.db``。
    """
    base = data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / "git-lanes.db"
