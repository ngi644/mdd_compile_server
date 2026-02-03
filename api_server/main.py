from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, Form, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse, Response
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
import zipfile

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


def _extract_from_zip(zip_data: bytes, filename: str) -> Optional[bytes]:
    """ ZIPファイルから指定されたファイルを抽出する

    Args:
        zip_data (bytes): ZIPファイルのバイナリデータ
        filename (str): 抽出するファイル名
    Returns:
        Optional[bytes]: 抽出されたファイルのバイナリデータ、存在しない場合はNone
    """
    try:
        with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
            if filename in zf.namelist():
                return zf.read(filename)
    except zipfile.BadZipFile:
        pass
    return None


def _is_platformio_result(data: bytes) -> bool:
    """ PlatformIOの結果（ZIP）かどうかを判定する

    Args:
        data (bytes): バイナリデータ
    Returns:
        bool: ZIPファイルの場合True
    """
    # ZIPファイルのマジックナンバー: PK (0x50, 0x4B)
    return data[:2] == b'PK'


@app.post("/api/compile/codal")
async def compile_codal(request: Request, file: UploadFile = File(...), user_id: str = Form(None)):
    """ FastAPI から Celery にタスクを送信する

    Args: file (UploadFile): アップロードされたファイル
        user_id (Optional[str]): ユーザーID
    Returns: dict: タスクIDと結果取得用のURL（WebUSB書き込みページ）
    """
    source_code = await file.read()
    source_code_str = base64.b64encode(source_code).decode('utf-8')
    task = celery_app.send_task("compile_worker.tasks.compile_codal", args=[source_code_str, user_id])
    result_url = urljoin(request.url._url, f"/api/compile/{task.id}/webusb")
    return {"task_id": task.id,
             "url": _remove_protocol(result_url)}


# PlatformIO 対応ボード一覧
SUPPORTED_BOARDS = [
    "m5stack-atoms3",
    "m5stack-atoms3-lite",
    "m5stack-core2",
    "m5stack-cores3",
    "m5stick-c-plus2"
]


@app.get("/api/compile/platformio/boards")
async def get_supported_boards():
    """ サポートされているボードの一覧を取得する

    Returns: dict: サポートされているボードの一覧
    """
    return {"boards": SUPPORTED_BOARDS}


@app.post("/api/compile/platformio")
async def compile_platformio(request: Request, file: UploadFile = File(...), board: str = Query("m5stack-atoms3"), user_id: str = Form(None)):
    """ PlatformIO でコンパイルする

    Args: file (UploadFile): アップロードされたファイル (ZIP)
        board (str): ターゲットボード名
        user_id (Optional[str]): ユーザーID
    Returns: dict: タスクIDと結果取得用のURL（WebSerial書き込みページ）
    """
    if board not in SUPPORTED_BOARDS:
        raise HTTPException(status_code=400, detail=f"Unsupported board: {board}. Supported boards: {SUPPORTED_BOARDS}")

    source_code = await file.read()
    source_code_str = base64.b64encode(source_code).decode('utf-8')
    task = celery_app.send_task("compile_worker.tasks.compile_platformio", args=[source_code_str, board, user_id])
    result_url = urljoin(request.url._url, f"/api/compile/{task.id}/webserial?board={board}")
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
    Returns: StreamingResponse: HEX/BINファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    data = {"title": "コンパイル中", }
    if task_result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result is not None:
        if task_result.result != b"":
            result_bin = BytesIO(task_result.result)
            result_bin.seek(0)
            # ファイルの種類を判断（HEXファイルは":"で始まるASCIIテキスト）
            is_hex = task_result.result[:1] == b':'
            if is_hex:
                filename = "microbitv2.hex"
            else:
                filename = "firmware.bin"
            # StreamingResponseを使ってファイルをクライアントに提供
            return StreamingResponse(result_bin, media_type="application/octet-stream",
                                     headers={'Content-Disposition': f'attachment; filename="{filename}"' },
                                     status_code=200)
        else:
            # ファイルが空の場合は，エラー内容を返す
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
    data = {"title": "コンパイル中"}

    # タスクが存在しない、またはまだ完了していない場合は待機画面を表示
    if task_result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result == b"":
        # コンパイルエラーの場合
        data["title"] = "コンパイルエラー"
        data["trace_back"] = task_result.trace_back
        return templates.TemplateResponse("error_template.html", {"request": request, "data": data})

    data = {"title": "Web USB転送",
            "file_url": _get_result_url(request.url._url, task_result.task_id),
            }

    return templates.TemplateResponse("webusb_template.html", {"request": request, "data": data})


@app.get("/api/compile/{task_id}/webserial")
async def get_result_webserial(request: Request, task_id: str, board: str = "m5stack-atoms3", db: Session = Depends(get_db)):
    """ タスクの実行結果をWebSerial経由でESP32デバイスに書き込む

    Args: task_id (str): タスクID
        board (str): ターゲットボード名
    Returns: HTMLResponse: ESP Web Tools書き込みページ
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    data = {"title": "コンパイル中"}

    # タスクが存在しない、またはまだ完了していない場合は待機画面を表示
    if task_result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result is None:
        return templates.TemplateResponse("wait_template.html", {"request": request, "data": data})
    if task_result.result == b"":
        # コンパイルエラーの場合
        data["title"] = "コンパイルエラー"
        data["trace_back"] = task_result.trace_back
        return templates.TemplateResponse("error_template.html", {"request": request, "data": data})

    # /webserial を /manifest.json に置き換え（プロトコル相対URLを使用してMixed Content回避）
    manifest_url = _remove_protocol(urljoin(request.url._url, f"/api/compile/{task_id}/manifest.json?board={board}"))
    data = {
        "title": "WebSerial 書き込み",
        "task_id": task_id,
        "board": board,
        "file_url": _get_result_url(request.url._url, task_result.task_id),
        "manifest_url": manifest_url,
    }

    return templates.TemplateResponse("webserial_template.html", {"request": request, "data": data})


@app.get("/api/compile/{task_id}/firmware.bin")
async def get_firmware_bin(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ ESP Web Tools用のファームウェアバイナリを取得する

    Args: task_id (str): タスクID
    Returns: Response: BINファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if task_result.result is None or task_result.result == b"":
        raise HTTPException(status_code=404, detail="Firmware not ready")

    # PlatformIOの結果（ZIP）から firmware.bin を抽出
    if _is_platformio_result(task_result.result):
        firmware = _extract_from_zip(task_result.result, "firmware.bin")
        if firmware is None:
            raise HTTPException(status_code=404, detail="firmware.bin not found in archive")
        content = firmware
    else:
        content = task_result.result

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'inline; filename="firmware.bin"',
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/api/compile/{task_id}/bootloader.bin")
async def get_bootloader_bin(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ ESP Web Tools用のブートローダーバイナリを取得する

    Args: task_id (str): タスクID
    Returns: Response: BINファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if task_result.result is None or task_result.result == b"":
        raise HTTPException(status_code=404, detail="Firmware not ready")

    if not _is_platformio_result(task_result.result):
        raise HTTPException(status_code=404, detail="Not a PlatformIO build")

    bootloader = _extract_from_zip(task_result.result, "bootloader.bin")
    if bootloader is None:
        raise HTTPException(status_code=404, detail="bootloader.bin not found in archive")

    return Response(
        content=bootloader,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'inline; filename="bootloader.bin"',
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/api/compile/{task_id}/partitions.bin")
async def get_partitions_bin(request: Request, task_id: str, db: Session = Depends(get_db)):
    """ ESP Web Tools用のパーティションテーブルを取得する

    Args: task_id (str): タスクID
    Returns: Response: BINファイル
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if task_result.result is None or task_result.result == b"":
        raise HTTPException(status_code=404, detail="Firmware not ready")

    if not _is_platformio_result(task_result.result):
        raise HTTPException(status_code=404, detail="Not a PlatformIO build")

    partitions = _extract_from_zip(task_result.result, "partitions.bin")
    if partitions is None:
        raise HTTPException(status_code=404, detail="partitions.bin not found in archive")

    return Response(
        content=partitions,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'inline; filename="partitions.bin"',
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/api/compile/{task_id}/manifest.json")
async def get_webserial_manifest(request: Request, task_id: str, board: str = "m5stack-atoms3", db: Session = Depends(get_db)):
    """ ESP Web Tools用のマニフェストファイルを生成する

    Args: task_id (str): タスクID
        board (str): ターゲットボード名
    Returns: JSONResponse: マニフェストJSON
    """
    task_result = db.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()
    if task_result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if task_result.result is None or task_result.result == b"":
        raise HTTPException(status_code=404, detail="Firmware not ready")

    # ボード名から表示名を取得
    board_names = {
        "m5stack-atoms3": "M5AtomS3",
        "m5stack-atoms3-lite": "M5AtomS3 Lite",
        "m5stack-core2": "M5Stack Core2",
        "m5stack-cores3": "M5Stack CoreS3",
        "m5stick-c-plus2": "M5StickC Plus2",
    }
    board_display_name = board_names.get(board, board)

    # チップファミリーとオフセットを決定
    # ESP32-S3: bootloader=0x0, partitions=0x8000, app=0x10000
    # ESP32: bootloader=0x1000, partitions=0x8000, app=0x10000
    is_s3 = "s3" in board.lower()
    chip_family = "ESP32-S3" if is_s3 else "ESP32"
    bootloader_offset = 0 if is_s3 else 0x1000

    # ベースURLを生成（プロトコル相対URLを使用してMixed Content回避）
    base_url = _remove_protocol(urljoin(request.url._url, f"/api/compile/{task_result.task_id}"))

    # ZIPからファイルの存在を確認してパーツリストを構築
    parts = []
    if _is_platformio_result(task_result.result):
        # ブートローダーがあれば追加
        if _extract_from_zip(task_result.result, "bootloader.bin"):
            parts.append({"path": f"{base_url}/bootloader.bin", "offset": bootloader_offset})
        # パーティションテーブルがあれば追加
        if _extract_from_zip(task_result.result, "partitions.bin"):
            parts.append({"path": f"{base_url}/partitions.bin", "offset": 0x8000})
        # ファームウェア（必須）
        parts.append({"path": f"{base_url}/firmware.bin", "offset": 0x10000})
    else:
        # 旧形式（単一バイナリ）の場合
        parts.append({"path": f"{base_url}/firmware.bin", "offset": 0x10000})

    manifest = {
        "name": f"MDD Firmware ({board_display_name})",
        "version": "1.0.0",
        "builds": [
            {
                "chipFamily": chip_family,
                "parts": parts
            }
        ]
    }

    return JSONResponse(content=manifest)


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    """
    ルートディレクトリにアクセスしたときに表示するページ
    """
    data = {"title": "MDD Compile Server"}
    return templates.TemplateResponse("index_template.html", {"request": request, "data": data})