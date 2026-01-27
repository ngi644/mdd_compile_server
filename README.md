# MDD コンパイルサーバー
MDD コンパイルサーバーは、MDDコンパイラにより生成されたプログラミングコードを実行形式にするためのサーバーです。

## 対応ターゲット

| ターゲット | デバイス | 出力形式 |
|-----------|---------|---------|
| CODAL | micro:bit v2 | .hex |
| PlatformIO | M5Stack系 (AtomS3, Core2, CoreS3等) | .bin |

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

#### PlatformIO (M5Stack系)

M5Stack系デバイス向けのコンパイルを行います。`file`パラメータにコンパイル対象のZipファイル（`main.cpp`を含む）を指定します。`board`パラメータでターゲットボードを指定します。

**対応ボード:**

| ボード名 | デバイス |
|---------|---------|
| `m5stack-atoms3` | M5AtomS3 |
| `m5stack-atoms3-lite` | M5AtomS3 Lite |
| `m5stack-core2` | M5Stack Core2 |
| `m5stack-cores3` | M5Stack CoreS3 |
| `m5stick-c-plus2` | M5StickC Plus2 |

**サポートボード一覧の取得:**

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/platformio/boards' \
  -H 'accept: application/json'
```

**コンパイルリクエスト:**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/compile/platformio' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip' \
  -F 'board=m5stack-atoms3' \
  -F 'user_id=hoge'
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

### コンパイルタスクの一覧の取得

`/api/compile/list`にGETリクエストを送信することで，コンパイルタスクの一覧を最新から100件を取得することができます。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/list' \
  -H 'accept: application/json'
```



