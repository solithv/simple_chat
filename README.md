# Simple Chat
コンピュータネットワークⅡ 2024</br>
サーバ・クライアントアプリ作成課題 F班

## 機能
- websocket通信によるリアルタイムチャット
- 画像送受信機能
- ファイル送受信機能

## HOW TO USE
### Server
serverフォルダ下の`requirements.txt`のライブラリをインストールしてapp.pyを実行
```bash
$ cd server
$ pip install -r requirements.txt
$ python app.py
```

各種オプションは`.env_sample`および以下のコマンドライン引数ヘルプを参照
```bash
$ python app.py -h
```

### TUI Client
client_tuiフォルダ下の`requirements.txt`のライブラリをインストールしてclient.pyを実行
```bash
$ cd client_tui
$ pip install -r requirements.txt
$ python client.py
```

各種オプションは以下のコマンドライン引数ヘルプを参照
```bash
$ python client.py -h
```