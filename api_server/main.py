from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.orm import Session
from shared.database import SessionLocal, engine
from shared import models
from celery_app import app as celery_app
import base64
from io import BytesIO
from urllib.parse import urljoin

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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


@app.get("/api/compile/list/range/{start}/{end}")
async def get_task_list(request: Request, start:str, end:str ,db: Session = Depends(get_db)):
    """
    タスクの一覧を期間で取得する
    startおよびendは，YYYY-MM-DDの形式で指定する
    """
    base_url = request.url._url
    # task_idとuser_idとコンパイル時間，結果取得用のURLを取得する
    
    task_results = db.query(models.TaskResult.task_id,
                            models.TaskResult.user_id,
                            models.TaskResult.created_at,
                            models.TaskResult.modified_at).filter(models.TaskResult.created_at >= start).filter(models.TaskResult.created_at <= end).order_by(models.TaskResult.created_at.desc()).all()
    tasks = [dict(task_id=task_result[0], user_id=task_result[1], 
                  result_url=_get_result_url(base_url, task_result[0]),
                  created_at=task_result[2], modified_at=task_result[3],
                  time_to_compile=_get_time_to_compile(task_result[3], task_result[2])
                  ) for task_result in task_results]
    return {"tasks": tasks}


@app.get("/api/compile/{task_id}/info")
async def get_info(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ タスクの詳細を取得する
     
    Args: task_id (str): タスクID
    Returns: HTMLResponse: タスクの詳細を表示するHTML
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    data = {"task_id": task_result.task_id,
            "user_id": task_result.user_id,
            "created_at": task_result.created_at,
            "modified_at": task_result.modified_at,
            "result_url": _get_result_url(request.url._url, task_result.task_id),
            "time_to_compile": _get_time_to_compile(task_result.modified_at, task_result.created_at),
            "trace_back": task_result.trace_back,
            }
    return templates.TemplateResponse("task_info_template.html", {"request": request, "data": data})


@app.get("/api/compile/{task_id}/result")
async def get_result(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ タスクの実行結果を取得する
     
    Args: task_id (str): タスクID
    Returns: StreamingResponse: HEXファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    data = {"title": "コンパイル中", }
    if task_result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result is not None:
        if task_result.result != b"":
            result_bin = BytesIO(task_result.result)
            result_bin.seek(0)
            # StreamingResponseを使ってHEXファイルをクライアントに提供
            return StreamingResponse(result_bin, media_type="application/octet-stream", 
                                     headers={'Content-Disposition': 'attachment; filename="microbitv2.hex"' },
                                     status_code=200)
        else:
            # HEXファイルが空の場合は，エラー内容を返す
            data["title"] = "コンパイルエラー"
            data["trace_back"] = task_result.trace_back
            return templates.TemplateResponse("error_template.html", {"request": request, "data": data})
    else:
        # タスクが完了していない場合は、再度，リロードするようにメッセージを返すHTTPレスポンスを返す
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})


@app.get("/api/compile/{task_id}/webusb")
async def get_result_webusb(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ タスクの実行結果をWebUSBdeviceに送信する
     
    Args: task_id (str): タスクID
    Returns: WebResponse: HEXファイル送信用のHTML
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    
    data = {"title": "Web USB転送", 
            "file_url": _get_result_url(request.url._url, task_result.task_id),
            }
    
    return templates.TemplateResponse("webusb_template.html", {"request": request, "data": data})


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    """
    ルートディレクトリにアクセスしたときに表示するページ
    """
    data = {"title": "mdd compiler", "body": "MDD compiler for micro:bit v2"}
    return templates.TemplateResponse("index_template.html", {"request": request, "data": data})