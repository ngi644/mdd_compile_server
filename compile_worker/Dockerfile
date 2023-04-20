# compile_worker/Dockerfile
FROM python:3.9

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 必要なパッケージをインストールします
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ワーキングディレクトリを設定
WORKDIR /app

# Python関連の依存関係をインストール
COPY compile_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY shared /app/shared
COPY compile_worker/__init__.py .
COPY compile_worker/task.py .

# コマンドを指定
CMD ["celery", "-A", "task", "worker", "--loglevel=info"]
