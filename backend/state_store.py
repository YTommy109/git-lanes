"""ウィンドウ状態の永続化。"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)
_lock = threading.Lock()


@dataclass
class WindowState:
    """保存するウィンドウ状態。"""

    x: int | None = None
    y: int | None = None
    width: int = 1280
    height: int = 800
    repo_id: str | None = None
    commit_hash: str | None = None
    show_remote: bool = True
    show_tags: bool = True


_FIELDS = frozenset(WindowState.__dataclass_fields__)


def load(path: Path) -> WindowState:
    """JSON からウィンドウ状態を読み込む。

    Args:
        path: JSON ファイルパス。

    Returns:
        保存済みの状態。ファイルが存在しないか壊れている場合はデフォルト値。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return WindowState(**{k: v for k, v in data.items() if k in _FIELDS})
    except Exception:
        return WindowState()


def save(path: Path, state: WindowState) -> None:
    """ウィンドウ状態を JSON にアトミックに書き込む。

    Args:
        path: 書き込み先 JSON ファイルパス。
        state: 保存するウィンドウ状態。
    """
    with _lock:
        _write(path, state)


def update(path: Path, **fields: object) -> None:
    """指定フィールドだけ上書きして保存する。

    Args:
        path: JSON ファイルパス。
        **fields: 更新するフィールド名と値。
    """
    with _lock:
        state = load(path)
        for k, v in fields.items():
            if hasattr(state, k):
                setattr(state, k, v)
        _write(path, state)


def _write(path: Path, state: WindowState) -> None:
    """JSON にアトミックに書き込む（呼び出し元がロックを保持していること）。"""
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(
            json.dumps(asdict(state), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError:
        _logger.warning("ウィンドウ状態の保存に失敗しました: %s", path)
