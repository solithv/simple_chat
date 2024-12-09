import base64
from pathlib import Path

import socketio
import socketio.exceptions

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}


class SimpleChatWSManager:
    def __init__(self, url: str = "http://127.0.0.1:5000", username: str = None):
        self.sio = socketio.Client()
        self.url = url
        self.username = username

        self.setup_socket_handlers()

    def setup_socket_handlers(self):
        """受信イベント定義"""
        # TODO: クライアントの仕様に合わせて変更

        @self.sio.on("disconnect")
        def on_disconnect():
            raise socketio.exceptions.DisconnectedError("Disconnected from server.")

        @self.sio.on("rooms")
        def on_rooms(data):
            return [room["name"] for room in data]

        # @self.sio.on("message")
        # def on_message(data):

        #     return data

    def connect(self):
        """接続処理"""
        self.sio.connect(f"{self.url}?name={self.username}")

    def disconnect(self):
        """終了処理"""
        self.sio.emit("disconnect")
        self.sio.disconnect()

    def join(self, room: str):
        """ルームに参加"""
        self.sio.emit("join", {"room": room})

    def leave(self):
        """ルームから退出"""
        self.sio.emit("leave")

    def send_message(self, message: str):
        """メッセージの送信"""
        if Path(message).exists():
            file = Path(message)
            with file.open("rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            if file.suffix in IMAGE_SUFFIXES:
                message_data = {"image": data}
            else:
                message_data = {"filename": file.name, "file_data": data}
        else:
            message_data = {"message": message}
        self.sio.emit("message", message_data)

    def __del__(self):
        self.disconnect()


class TK:
    def __init__(self):
        self.manager = SimpleChatWSManager()

    def setup(self):
        @self.manager.sio.on("some")
        def on_some(data):
            self.data = data
