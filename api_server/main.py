from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.orm import Session
from shared.database import SessionLocal, engine
from shared import models
from celery_app import app as celery_app
import base64
from urllib.parse import urljoin

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


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


def _remove_protocol(url: str):
    """ URLからプロトコルを除去する
    """
    return url.replace("http://", "//")


@app.post("/api/compile/codal")
async def compile_codal(request: Request, file: UploadFile = File(...), user_id: str = Form(None)):
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
             "url": _remove_protocol(result_url)}


def _get_result_url(base_url: str, task_id: str):
    """ タスクの結果取得用のURLを生成する
    """
    result_url = urljoin(base_url, f"/api/compile/{task_id}/result")
    return _remove_protocol(result_url)


def _get_time_to_compile(modified_at, created_at):
    """ コンパイル時間を取得する
    """
    if modified_at is None:
        return None
    if created_at is None:
        return None
    return (modified_at - created_at).total_seconds()


@app.get("/api/compile/list")
async def get_task_list(request: Request, db: Session = Depends(get_db)):
    """
    タスクの一覧を最新から100件取得する
    """
    base_url = request.url._url
    # task_idとuser_idとコンパイル時間，結果取得用のURLを取得する
    
    task_results = db.query(models.TaskResult.task_id, models.TaskResult.user_id, models.TaskResult.created_at,models.TaskResult.modified_at).order_by(models.TaskResult.created_at.desc()).limit(100).all()
    tasks = [dict(task_id=task_result[0], user_id=task_result[1], 
                  result_url=_get_result_url(base_url, task_result[0]),
                  created_at=task_result[2], modified_at=task_result[3],
                  time_to_compile=_get_time_to_compile(task_result[3], task_result[2])
                  ) for task_result in task_results]
    return {"tasks": tasks}


@app.get("/api/compile/{task_id}/result")
async def get_result(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ タスクの実行結果を取得する
     
    Args: task_id (str): タスクID
    Returns: FileResponse: HEXファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    data = {"title": "コンパイル中", }
    if task_result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result is not None:
        if task_result.result != b"":
            # 一時的にHEXファイルを保存
            tmp_hex_path = f"/tmp/{task_id}.hex"
            with open(tmp_hex_path, "wb") as f:
                f.write(task_result.result)

            # FileResponseを使ってHEXファイルをクライアントに提供
            return FileResponse(tmp_hex_path, media_type="application/octet-stream", filename=f"microbitv2.hex", status_code=200)
        else:
            # HEXファイルが空の場合は，エラー内容を返す
            data["title"] = "コンパイルエラー"
            data["trace_back"] = task_result.trace_back
            return templates.TemplateResponse("error_template.html", {"request": request, "data": data})
            return HTMLResponse(content=html, media_type="text/html", status_code=200)
    else:
        # タスクが完了していない場合は、再度，リロードするようにメッセージを返すHTTPレスポンスを返す
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    data = {"title": "mdd compiler", "body": "MDD compiler for micro:bit v2"}
    return templates.TemplateResponse("index_template.html", {"request": request, "data": data})