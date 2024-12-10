import base64
from pathlib import Path

import socketio
import socketio.exceptions

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

def dummyFunc(*args, **kwargs):
    pass

class SimpleChatWSManager:

    def __init__(self):
        self.sio = socketio.Client()
        self.offDisconnect()
        self.offRooms()
        self.offMessage()
        
    def connect(self, url: str = "http://127.0.0.1:5000", username: str = None):
        """接続処理"""
        self.sio.connect(f"{url}?name={username}")

    def disconnect(self):
        """終了処理"""
        self.sio.emit("disconnect")
        self.sio.disconnect()

    def onDisconnect(self, handler):
        """終了通知"""
        self.sio.on("disconnect", handler)

    def offDisconnect(self):
        """終了通知解除"""
        self.sio.on("disconnect", dummyFunc)

    def onError(self, handler):
        """部屋一覧受け取り"""
        self.sio.on("error", handler)

    def offError(self):
        """部屋一覧受け取り解除"""
        self.sio.on("error", dummyFunc)

    def onRooms(self, handler):
        """部屋一覧受け取り"""
        self.sio.on("rooms", handler)

    def offRooms(self):
        """部屋一覧受け取り解除"""
        self.sio.on("rooms", dummyFunc)

    def onMessage(self, handler):
        """メッセージ受け取り"""
        self.sio.on("message", handler)

    def offMessage(self):
        """メッセージ解除"""
        self.sio.on("message", dummyFunc)

    def join(self, room: str):
        """ルームに参加"""
        self.sio.emit("join", {"room": room})

    def leave(self):
        """ルームから退出"""
        self.sio.emit("leave")

    def sendText(self, message: str):
        """テキストメッセージの送信"""
        self.sio.emit("message", {"message": message})

    def sendImage(self, imageData: str):
        """画像の送信"""
        self.sio.emit("message", {"image": imageData})

    def sendFile(self, fileData: str, fileName):
        """ファイルの送信"""
        self.sio.emit("message", {"file_data": fileData, "filename": fileName})