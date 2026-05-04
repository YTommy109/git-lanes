"""ドメイン例外クラス。"""

from __future__ import annotations


class AppError(Exception):
    """アプリケーション例外の基底クラス。HTTP 出力層でステータスコードに変換する。"""

    status_code: int = 500
    detail: str = ""


class RepositoryNotFoundError(AppError):
    """リポジトリが存在しない場合の例外。"""

    status_code = 404
    detail = "リポジトリが見つかりません"


class GitOpenError(AppError):
    """Git リポジトリとして開けない場合の例外。"""

    status_code = 400
    detail = "Git リポジトリを開けません"


class CommitNotFoundError(AppError):
    """コミットが存在しない場合の例外。"""

    status_code = 404
    detail = "コミットが見つかりません"


class DirectoryNotFoundError(AppError):
    """ディレクトリが存在しない場合の例外。"""

    status_code = 400
    detail = "ディレクトリが存在しません"


class RepositoryAlreadyRegisteredError(AppError):
    """パスが既に登録済みの場合の例外。"""

    status_code = 409
    detail = "このパスは既に登録されています"
