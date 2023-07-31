# ベースイメージを選択
FROM python:3.9

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をインストール
COPY api_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY shared /app/shared
COPY api_server/__init__.py .
COPY api_server/main.py .
COPY api_server/celery_app.py .
COPY api_server/static /app/static
COPY api_server/templates /app/templates


# UvicornでFastAPIアプリケーションを実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]