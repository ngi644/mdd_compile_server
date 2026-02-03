# MDD コンパイルサーバー
MDD コンパイルサーバーは、MDDコンパイラにより生成されたプログラミングコードを実行形式にするためのサーバーです。

## 対応ターゲット

| ターゲット | デバイス | 出力形式 | 書き込み方式 |
|-----------|---------|---------|-------------|
| CODAL | micro:bit v2 | .hex | WebUSB |
| PlatformIO | M5Stack系 (AtomS3, Core2, CoreS3等) | .bin | WebSerial |

## セットアップ，起動

docker-composeを用いてサーバーを起動します。

### リポジトリのクローン

```bash
$ git clone　https://github.com/ngi644/mdd_compile_server.git
```

### リポジトリの移動

```bash
$ cd mdd_compile_server
```

### サーバーのビルド

```bash
$ docker-compose build
```

### サーバーの起動

```bash
$ docker-compose up -d
```

## APIの使い方

FastAPIを用いてAPIを実装しています。`http://localhost:8000/docs`にアクセスすることで，APIの仕様を確認することができます。
docsページでは，APIの実行も行うことができます。

### コンパイルの要求

`/api/compile/{target}`にPOSTリクエストを送信することで，コンパイルを要求することができます。
`target`には，コンパイル対象のプログラミング言語を指定します。

#### CODAL (micro:bit v2)

POSTを送信する際には，`file`パラメータにコンパイル対象のZipファイルを指定します。Zipファイルは，`main.cpp`をルートディレクトリに含む必要があります。 `user_id`パラメータには，コンパイル対象のユーザーIDを指定します。

```bash
curl -X 'POST' \
  'http://localhost:8000/api/compile/codal?user_id=hoge' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip'
```

**レスポンス例:**

```json
{
  "task_id": "abc123-...",
  "url": "//localhost:8000/api/compile/abc123-.../webusb"
}
```

#### PlatformIO (M5Stack系)

M5Stack系デバイス向けのコンパイルを行います。`file`パラメータにコンパイル対象のZipファイル（`main.cpp`を含む）を指定します。`board`パラメータでターゲットボードを指定します。

**対応ボード:**

| ボード名 | デバイス | チップ |
|---------|---------|--------|
| `m5stack-atoms3` | M5AtomS3 | ESP32-S3 |
| `m5stack-atoms3-lite` | M5AtomS3 Lite | ESP32-S3 |
| `m5stack-core2` | M5Stack Core2 | ESP32 |
| `m5stack-cores3` | M5Stack CoreS3 | ESP32-S3 |
| `m5stick-c-plus2` | M5StickC Plus2 | ESP32 |

**サポートボード一覧の取得:**

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/platformio/boards' \
  -H 'accept: application/json'
```

**コンパイルリクエスト:**

`board`パラメータはURLクエリパラメータで指定します。省略時は`m5stack-atoms3`がデフォルトです。

```bash
curl -X 'POST' \
  'http://localhost:8000/api/compile/platformio?board=m5stack-atoms3' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip' \
  -F 'user_id=hoge'
```

**ボード指定なし（デフォルト: m5stack-atoms3）:**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/compile/platformio' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip' \
  -F 'user_id=hoge'
```

**レスポンス例:**

```json
{
  "task_id": "abc123-...",
  "url": "//localhost:8000/api/compile/abc123-.../webserial?board=m5stack-atoms3"
}
```

**サンプルコード (main.cpp):**

```cpp
#include <M5Unified.h>

void setup() {
    M5.begin();
    M5.Display.println("Hello, M5Stack!");
}

void loop() {
    M5.update();
}
```

### タスクの詳細の取得

`/api/compile/{task_id}/info`にGETリクエストを送信することで，コンパイルタスクの詳細を取得することができます。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/{task_id}/info' \
  -H 'accept: text/html'
```

### コンパイル結果の取得

`/api/compile/{task_id}/result`にGETリクエストを送信することで，コンパイル結果を取得することができます。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/{task_id}/result' \
  -H 'accept: application/json'
```

### WebUSB書き込み (micro:bit v2)

micro:bit v2向けに、ブラウザから直接HEXファイルを書き込むことができます。DAPjs ライブラリを使用してCMSIS-DAP経由で書き込みます。

**対応ブラウザ:** Chrome, Edge（WebUSB対応ブラウザ）

`/api/compile/{task_id}/webusb`にアクセスすると、WebUSB書き込みページが表示されます。

```
http://localhost:8000/api/compile/{task_id}/webusb
```

**使い方:**

1. 上記URLにブラウザでアクセス
2. micro:bit v2をUSBケーブルで接続
3. 「WebUSBで書き込む」ボタンをクリック
4. ポップアップでmicro:bitデバイスを選択
5. 自動的に書き込みが開始され、完了後micro:bitが再起動します

**代替方法:**

WebUSBがうまくいかない場合は、「HEXをダウンロード」ボタンでファイルを保存し、MICROBITドライブに手動でコピーすることもできます。

**技術詳細:**
- 使用ライブラリ: [DAPjs](https://github.com/ArmMbed/dapjs) v2.3.0
- プロトコル: CMSIS-DAP over WebUSB
- VendorID: 0x0d28, ProductID: 0x0204

### WebSerial書き込み (M5Stack系)

M5Stack系デバイス（ESP32）向けに、ブラウザから直接ファームウェアを書き込むことができます。ESP Web Toolsを使用しています。

**対応ブラウザ:** Chrome, Edge（WebSerial対応ブラウザ）

`/api/compile/{task_id}/webserial`にアクセスすると、WebSerial書き込みページが表示されます。

```
http://localhost:8000/api/compile/{task_id}/webserial?board=m5stack-atoms3
```

**使い方:**

1. 上記URLにブラウザでアクセス
2. M5StackデバイスをUSBで接続
3. 「デバイスに書き込む」ボタンをクリック
4. シリアルポートを選択して書き込み開始

**ESP32フラッシュ構造:**

ESP Web Toolsは、以下の3つのバイナリを正しいオフセットに書き込みます：

| ファイル | オフセット (ESP32-S3) | オフセット (ESP32) | 説明 |
|---------|---------------------|-------------------|------|
| bootloader.bin | 0x0000 | 0x1000 | ブートローダー |
| partitions.bin | 0x8000 | 0x8000 | パーティションテーブル |
| firmware.bin | 0x10000 | 0x10000 | アプリケーション |

### 個別バイナリの取得 (PlatformIO)

PlatformIOでコンパイルした場合、以下のエンドポイントで個別のバイナリを取得できます：

```bash
# ファームウェア
curl -O http://localhost:8000/api/compile/{task_id}/firmware.bin

# ブートローダー
curl -O http://localhost:8000/api/compile/{task_id}/bootloader.bin

# パーティションテーブル
curl -O http://localhost:8000/api/compile/{task_id}/partitions.bin
```

### ESP Web Tools マニフェスト

ESP Web Tools用のマニフェストファイルを取得できます：

```bash
curl http://localhost:8000/api/compile/{task_id}/manifest.json?board=m5stack-atoms3
```

**レスポンス例:**

```json
{
  "name": "MDD Firmware (M5AtomS3)",
  "version": "1.0.0",
  "builds": [
    {
      "chipFamily": "ESP32-S3",
      "parts": [
        {"path": "http://localhost:8000/api/compile/{task_id}/bootloader.bin", "offset": 0},
        {"path": "http://localhost:8000/api/compile/{task_id}/partitions.bin", "offset": 32768},
        {"path": "http://localhost:8000/api/compile/{task_id}/firmware.bin", "offset": 65536}
      ]
    }
  ]
}
```

### コンパイルタスクの一覧の取得

`/api/compile/list`にGETリクエストを送信することで，コンパイルタスクの一覧を最新から100件を取得することができます。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/list' \
  -H 'accept: application/json'
```

### 期間指定でのタスク一覧取得

`/api/compile/list/range/{start}/{end}`で期間を指定してタスク一覧を取得できます。日付は`YYYY-MM-DD`形式で指定します。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/list/range/2024-01-01/2024-12-31' \
  -H 'accept: application/json'
```

## アーキテクチャ

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Server │────▶│    Redis    │◀────│   Celery    │
│  (FastAPI)  │     │  (Broker)   │     │  (Worker)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
       │                                       │
       │                                       ▼
       │                              ┌─────────────────┐
       │                              │ Docker Containers│
       ▼                              │  - codal_env    │
┌─────────────┐                       │  - platformio_env│
│ PostgreSQL  │                       └─────────────────┘
│ (Results)   │
└─────────────┘
```

## Changelog

### v1.1.0 (2026-02)

**新機能:**
- WebUSB書き込み機能追加 (micro:bit v2向け、DAPjs使用)
- WebSerial書き込み機能追加 (M5Stack系向け、ESP Web Tools使用)
- トップページの改善（対応ターゲット一覧、ボード情報表示）
- 期間指定でのタスク一覧取得API (`/api/compile/list/range/{start}/{end}`)

**改善:**
- PlatformIO APIの`board`パラメータをURLクエリパラメータに変更
- CODALビルドキャッシュ問題の修正（ユーザーコードのみ再コンパイル）
- コンパイルワーカーのデバッグログ追加
- Mixed Content問題の修正（プロトコル相対URL対応）

**技術詳細:**
- DAPjs v2.3.0によるCMSIS-DAP経由のWebUSB書き込み
- ESP Web Tools v10によるWebSerial書き込み
- Ninjaビルドシステムのキャッシュ最適化

### v1.0.0 (初期リリース)

- CODAL (micro:bit v2) コンパイル機能
- PlatformIO (M5Stack系) コンパイル機能
- Celery/Redisによる非同期タスク処理
- PostgreSQLによる結果保存

## ライセンス

MIT License
