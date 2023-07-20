from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.orm import Session
from shared.database import SessionLocal, engine
from shared import models
from celery_app import app as celery_app
import base64
from urllib.parse import urljoin

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS設定
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """ DB への接続を管理する
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/compile/codal")
async def compile_codal(request: Request, file: UploadFile = File(...), user_id: Optional[str] = None):
    """ FastAPI から Celery にタスクを送信する

    Args: file (UploadFile): アップロードされたファイル
        user_id (Optional[str]): ユーザーID
    Returns: dict: タスクIDと結果取得用のURL
    """
    source_code = await file.read()
    source_code_str = base64.b64encode(source_code).decode('utf-8')
    task = celery_app.send_task("compile_worker.tasks.compile_codal", args=[source_code_str, user_id])
    result_url = urljoin(request.url._url, f"/api/compile/{task.id}/result")
    return {"task_id": task.id,
             "url": result_url}


@app.get("/api/compile/{task_id}/result")
async def get_result(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ タスクの実行結果を取得する
     
    Args: task_id (str): タスクID
    Returns: FileResponse: HEXファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")

    if task_result.result is not None:
        # 一時的にHEXファイルを保存
        tmp_hex_path = f"/tmp/{task_id}.hex"
        with open(tmp_hex_path, "wb") as f:
            f.write(task_result.result)

        # FileResponseを使ってHEXファイルをクライアントに提供
        return FileResponse(tmp_hex_path, media_type="application/octet-stream", filename=f"microbitv2.hex", status_code=200)
    else:
        # タスクが完了していない場合は、再度，リロードするようにメッセージを返すHTTPレスポンスを返す
        html = f"""
        <!DOCTYPE html>
        <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>ファイル生成中</title>
            </head>
            <body>
                <h2>ファイル生成中</h2>
                <p>現在，サーバーでファイルを生成中です．8秒後に再度ダウンロードを行います．</p>
                <p>下記リンクをクリックすることで直接ダウンロードします．</p>
                <a href="{request.url._url}" target="_blank" rel="noopener noreferrer">ファイルをダウンロード</a>
                <script type="text/javascript">
                    setTimeout("location.reload()", 8000);
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html, media_type="text/html", status_code=200)


