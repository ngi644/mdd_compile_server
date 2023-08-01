# task.py (compile_worker)
from celery import Celery
import docker
from docker.errors import NotFound
from datetime import datetime
from shared import models
from shared.database import SessionLocal, engine
import base64
from shared.celery_config import broker_url, result_backend

import io
import tarfile

app = Celery("tasks", broker=broker_url, backend=result_backend)
app.config_from_object("shared.celery_config")
# app.conf.CELERY_ACKS_LATE = True
# app.conf.CELERYD_PREFETCH_MULTIPLIER = 1


def create_tar_archive(zip_data: bytes, task_id: str) -> io.BytesIO:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        file_data = io.BytesIO(zip_data)
        tarinfo = tarfile.TarInfo(name=f"{task_id}.zip")
        tarinfo.size = len(zip_data)
        tar.addfile(tarinfo, file_data)
    tar_buffer.seek(0)
    return tar_buffer


def create_result(task_id: str, user_id: str):
    """ コンパイル結果を DB に保存する

    Args:
        task_id (str): タスクID
        user_id (str): ユーザーID
    """
    session = SessionLocal()
    task_result = models.TaskResult(task_id=task_id, user_id=user_id)
    task_result.created_at = datetime.utcnow()
    task_result.modified_at = datetime.utcnow()
    session.add(task_result)
    session.commit()


def save_result(task_id: str, trace_back:str, result: bytes):
    """ コンパイル結果を DB に保存する

    Args:
        task_id (str): タスクID
        trace_back (str): エラー内容
        result (bytes): HEXファイル
    """
    session = SessionLocal()
    
    task_result = session.query(models.TaskResult).filter(models.TaskResult.task_id == task_id).first()

    # task_result が None の場合、検索された task_id が存在しないことを示します
    if task_result is not None:
        task_result.trace_back = trace_back
        task_result.result = result
        task_result.modified_at = datetime.utcnow()
        session.commit()
    else:
        print(f"TaskResult not found for task_id: {task_id}")


@app.task(bind=True, name="compile_worker.tasks.compile_codal")
def compile_codal(self, source_code: str, user_id: str = None):
    """ C++ のソースコードをコンパイルして HEX ファイルを生成する
    """
    create_result(self.request.id, user_id)
    docker_client = docker.from_env()
    # コンテナを作成
    container = docker_client.containers.run("mdd_compile_server-codal_env", detach=True, name=f"codal_{self.request.id}")
    # 環境変数を設定
    source_code_bytes = base64.b64decode(source_code.encode('utf-8'))
    tar_buffer = create_tar_archive(source_code_bytes, self.request.id)

    # ファイルをコンテナにコピー
    container.put_archive('/microbit-v2-samples', tar_buffer)

    env = {
        "ZIP_FILE": f"/microbit-v2-samples/{self.request.id}.zip",
        "OUTPUT_PATH": f"/tmp/{self.request.id}.hex"
    }

    # シェルスクリプトを実行
    compile_result = container.exec_run("bash compile_codal.sh", environment=env, workdir="/microbit-v2-samples")
    trace_back = compile_result.output.decode('utf-8')

    # コンパイル結果（HEXファイル）を取得
    try:
        hex_file_stream, stats = container.get_archive(f"/tmp/{self.request.id}.hex")

        byte_stream = io.BytesIO()
        for chunk in hex_file_stream:
            byte_stream.write(chunk)
        byte_stream.seek(0) 
        with tarfile.open(fileobj=byte_stream) as tar_file:
            hex_file = tar_file.extractfile(f'{self.request.id}.hex')
            # コンパイル結果を DB に保存
            save_result(self.request.id, trace_back, hex_file.read())
    except docker.errors.APIError:
        # コンパイルに失敗した場合、HEXファイルが存在しないため、APIError が発生します
        # その場合は、空のバイト列を返します
        save_result(self.request.id, trace_back, b"")

    # コンテナを削除
    container.stop(timeout=0)
    container.remove()

    return compile_result.exit_code
