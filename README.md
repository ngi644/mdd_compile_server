# MDD コンパイルサーバー
MDD コンパイルサーバーは、MDDコンパイラにより生成されたプログラミングコードを実行形式にするためのサーバーです。
現在は，CODALに対応しています。

## 使い方

### サーバーの起動

```bash 
$ docker-compose up -d
```

### コンパイル

```bash
$ curl -X POST -F "file=@./sample.cpp" http://localhost:8000/api/compile/codal
```

### コンパイル結果の取得

```bash
$ curl http://localhost:8000/api/compile/{task_id}/result
```

