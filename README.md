# MDD コンパイルサーバー
MDD コンパイルサーバーは、MDDコンパイラにより生成されたプログラミングコードを実行形式にするためのサーバーです。
現在は，CODALに対応しています。

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

#### CODAL

POSTを送信する際には，`file`パラメータにコンパイル対象のZipファイルを指定します。Zipファイルは，`main.cpp`をルートディレクトリに含む必要があります。 `user_id`パラメータには，コンパイル対象のユーザーIDを指定します。

```bash
curl -X 'POST' \
  'http://localhost:8000/api/compile/codal?user_id=hoge' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip'
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

### コンパイルタスクの一覧の取得

`/api/compile/list`にGETリクエストを送信することで，コンパイルタスクの一覧を最新から100件を取得することができます。

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/list' \
  -H 'accept: application/json'
```



