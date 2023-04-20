# MDD コンパイルサーバー
MDD コンパイルサーバーは、MDDコンパイラにより生成されたプログラミングコードを実行形式にするためのサーバーです。
現在は，CODALに対応しています。

## 使い方

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

### コンパイルの要求

`/compile/{target}`にPOSTリクエストを送信することで，コンパイルを要求することができます。
`target`には，コンパイル対象のプログラミング言語を指定します。

#### CODAL

POSTを送信する際には，`file`パラメータにコンパイル対象のZipファイルを指定します。Zipファイルは，`main.cpp`をルートディレクトリに含む必要があります。 `user_id`パラメータには，コンパイル対象のユーザーIDを指定します。

```bash
$ curl -X 'POST' \
  'http://localhost:8000/api/compile/codal?user_id=hoge' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@main.zip;type=application/zip'
```

### コンパイル結果の取得

```bash
curl -X 'GET' \
  'http://localhost:8000/api/compile/{task_id}/result' \
  -H 'accept: application/json'
```

