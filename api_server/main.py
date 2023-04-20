from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.orm import Session
from shared.database import SessionLocal, engine
from shared import models
from celery_app import app as celery_app
import base64

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
async def compile_codal(file: UploadFile = File(...), user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """ FastAPI から Celery にタスクを送信する

    Args: file (UploadFile): アップロードされたファイル
        user_id (Optional[str]): ユーザーID
        db (Session): DB への接続
    Returns: dict: タスクID
    """
    source_code = await file.read()
    source_code_str = base64.b64encode(source_code).decode('utf-8')
    task = celery_app.send_task("compile_worker.tasks.compile_codal", args=[source_code_str, user_id])
    return {"task_id": task.id}


@app.get("/api/compile/{task_id}/result")
async def get_result(task_id: str, db: Session = Depends(get_db)):
    """ タスクの実行結果を取得する
     
    Args: task_id (str): タスクID
        db (Session): DB への接続

    Returns: FileResponse: HEXファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")

    # 一時的にHEXファイルを保存
    tmp_hex_path = f"/tmp/{task_id}.hex"
    with open(tmp_hex_path, "wb") as f:
        f.write(task_result.result)

    # FileResponseを使ってHEXファイルをクライアントに提供
    return FileResponse(tmp_hex_path, media_type="application/octet-stream", filename=f"{task_id}.hex")
