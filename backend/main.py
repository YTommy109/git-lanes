"""FastAPI アプリケーションのエントリポイント。"""
from fastapi import FastAPI

app = FastAPI(title="Git Lanes")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """サーバーの稼働確認用エンドポイント。"""
    return {"status": "ok"}
