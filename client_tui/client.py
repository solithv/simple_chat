import argparse
import base64
import io
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import socketio
from PIL import Image
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.message import Message as TextualMessage
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Input, Label, Select, Static

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}


class ImageClickMessage(TextualMessage):
    """画像クリック時のメッセージ"""

    def __init__(self, image_data: str) -> None:
        self.image_data = image_data
        super().__init__()


class ImageDisplay(Static):
    """クリック可能な画像表示ウィジェット"""

    def __init__(self, image_text: Text, image_data: str):
        super().__init__()
        self.image_text = image_text
        self.image_data = image_data

    def compose(self) -> ComposeResult:
        yield Label(self.image_text)

    def on_click(self) -> None:
        self.post_message(ImageClickMessage(self.image_data))


class Hyperlink(Static):
    """クリック可能なハイパーリンクウィジェット"""

    DEFAULT_CSS = """
    Hyperlink {
        padding-left: 2;
    }
    """

    def __init__(self, text: str, url: str):
        super().__init__()
        self.text = text
        self.url = url

    def compose(self) -> ComposeResult:
        text = Text("File: ")
        text.append(self.text, style=Style(color="royal_blue1", underline=True))
        yield Label(text)

    def on_click(self) -> None:
        """リンクをクリックしたときの処理"""
        try:
            webbrowser.open(self.url)
        except Exception as e:
            self.notify(f"リンクを開けませんでした: {str(e)}", severity="error")


class LoginScreen(Screen):
    """ログイン画面"""

    def compose(self) -> ComposeResult:
        yield Container(
            Label("ユーザー名を入力してください:"),
            Input(id="username-input", placeholder="ユーザー名"),
            id="login-container",
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.app.username = event.value
            await self.app.connect_to_server()


class Message(Static):
    """メッセージを表示するウィジェット"""

    def __init__(
        self,
        user: str,
        timestamp: str,
        content: Optional[str] = None,
        image_data: Optional[str] = None,
        file_info: Optional[tuple[str, str]] = None,
    ):
        super().__init__()
        self.user = user
        self.timestamp = timestamp
        self.content = content
        self.image_data = image_data
        self.file_info = file_info

    def compose(self) -> ComposeResult:
        time = datetime.fromisoformat(self.timestamp).strftime("%H:%M")
        yield Label(f"[{time}] {self.user}:")
        if self.content:
            yield Label(f"  {self.content}")
        elif self.image_data:
            for text in self.convert_image_to_color_blocks(self.image_data):
                yield ImageDisplay(text, self.image_data)
        elif self.file_info:
            filename, link = self.file_info
            yield Hyperlink(filename, link)

    def convert_image_to_color_blocks(
        self, image_data: str, max_width: int = 40, max_height: int = 20
    ) -> list[Text]:
        """
        画像データをカラーブロック文字に変換する関数
        Returns: 表示用の文字列のリスト
        """
        try:
            # Base64デコード
            image_data = image_data.split(",")[-1]
            image_bytes = base64.b64decode(image_data + "=" * (-len(image_data) % 4))
            image = Image.open(io.BytesIO(image_bytes))

            # 画像のリサイズ
            width, height = image.size
            aspect_ratio = height / width
            new_width = min(max_width, width)
            new_height = int(new_width * aspect_ratio)

            if new_height > max_height:
                new_height = max_height
                new_width = int(new_height / aspect_ratio)

            image = image.resize((new_width, new_height))

            # 画像を文字列に変換
            lines = []
            for y in range(0, new_height, 2):
                line = Text()
                for x in range(new_width):
                    upper_pixel = image.getpixel((x, y))
                    lower_pixel = image.getpixel((x, min(y + 1, new_height - 1)))

                    # ピクセル値の取得
                    r1, g1, b1 = upper_pixel[:3]
                    r2, g2, b2 = lower_pixel[:3]

                    # Textualのスタイルを使用してカラー設定
                    style = Style(
                        color=f"rgb({r1},{g1},{b1})", bgcolor=f"rgb({r2},{g2},{b2})"
                    )
                    line.append("▀", style)
                lines.append(line)

            return lines
        except Exception as e:
            return [f"[画像の変換に失敗しました: {str(e)}]"]


class RoomSelector(Screen):
    """ルーム選択画面"""

    rooms = reactive([])

    def compose(self) -> ComposeResult:
        yield Container(
            Label("チャットルームを選択するか、新しいルーム名を入力してください:"),
            Select(
                ((room["name"], room["name"]) for room in self.rooms), id="room-select"
            ),
            Input(placeholder="新しいルーム名", id="new-room"),
            id="room-selector-container",
        )

    async def on_select_changed(self, event: Select.Changed) -> None:
        await self.app.join_room(event.value)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.app.join_room(event.value)


class ChatRoom(Screen):
    """チャットルーム画面"""

    def compose(self) -> ComposeResult:
        yield Container(
            Label("", id="room-name"),
            ScrollableContainer(id="message-log"),
            Input(placeholder="メッセージを入力...", id="message-input"),
        )

    def clear_messages(self) -> None:
        """メッセージログをクリアする"""
        message_log = self.query_one("#message-log")
        message_log.remove_children()

    def save_image(self, image_data: str) -> None:
        """画像データを保存する"""
        try:
            # Base64デコード
            image_data = image_data.split(",")[-1]
            image_bytes = base64.b64decode(image_data + "=" * (-len(image_data) % 4))
            image = Image.open(io.BytesIO(image_bytes))

            # 保存先のディレクトリを作成
            save_dir = Path("downloaded_images")
            save_dir.mkdir(exist_ok=True)

            # タイムスタンプを含むファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = save_dir / f"image_{timestamp}.png"

            # 画像を保存
            image.save(file_path)
            self.notify(f"画像を保存しました: {file_path}", timeout=3)
        except Exception as e:
            self.notify(f"画像の保存に失敗しました: {str(e)}", severity="error")

    async def on_image_click_message(self, message: ImageClickMessage) -> None:
        """画像クリック時の処理"""
        self.save_image(message.image_data)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            await self.app.send_message(event.value)
            self.query_one("#message-input").value = ""

    async def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            await self.app.leave_room()


class ChatApp(App):
    """メインアプリケーション"""

    CSS = """
    #login-container {
        height: 100%;
        align: center middle;
        padding: 1;
    }
    #room-selector-container {
        height: 100%;
        align: center middle;
        padding: 1;
    }
    Container {
        width: 100%;
    }
    #message-log {
        height: 1fr;
        border: solid green;
        padding: 1;
        overflow-y: auto;
        border-bottom: none;
    }
    #room-name {
        dock: top;
        width: 100%;
        padding: 1;
        background: blue;
        color: white;
        text-align: center;
        border-bottom: solid green;
    }
    #input-container {
        dock: bottom;
        width: 100%;
        height: auto;
        background: $surface;
        border: solid green;
    }
    #input-preview {
        padding: 0 1;
        color: $text-disabled;
        min-height: 1;
    }
    #message-input {
        dock: bottom;
        margin: 0 1 1 1;
        background: $surface-lighten-2;
        border: tall $primary;
    }
    Label {
        width: 100%;
    }
    """

    SCREENS = {
        "login": LoginScreen,
        "room_selector": RoomSelector,
        "chat": ChatRoom,
    }

    def __init__(self, url: str = "http://localhost:5000", username: str = None):
        super().__init__()
        self.sio = socketio.AsyncClient()
        self.url = url
        self.username = username
        self.current_room = None
        self.setup_socket_handlers()

    def setup_socket_handlers(self):
        @self.sio.on("rooms")
        async def on_rooms(data):
            if hasattr(self, "current_room") and self.current_room is None:
                room_selector = self.get_screen("room_selector")
                room_selector.rooms = data
                self.refresh()

        @self.sio.on("message")
        async def on_message(data):
            if self.current_room is not None:
                chat_screen = self.get_screen("chat")
                message_log = chat_screen.query_one("#message-log")
                if data.get("message"):
                    message = Message(
                        data["user"], data["timestamp"], content=data["message"]
                    )
                elif data.get("image"):
                    message = Message(
                        data["user"], data["timestamp"], image_data=data["image"]
                    )
                elif data.get("filename") and data.get("link"):
                    message = Message(
                        data["user"],
                        data["timestamp"],
                        file_info=(data["filename"], f'{self.url}{data["link"]}'),
                    )
                message_log.mount(message)
                message_log.scroll_end(animate=False)

    async def connect_to_server(self):
        """サーバーへの接続"""
        try:
            await self.sio.connect(f"{self.url}?name={self.username}")
            await self.push_screen("room_selector")
        except Exception as e:
            self.notify(f"接続エラー: {str(e)}", severity="error")

    async def join_room(self, room_name: str):
        """ルームへの参加"""
        try:
            self.current_room = room_name
            await self.sio.emit("join", {"room": room_name})
            await self.push_screen("chat")
            self.get_screen("chat").query_one("#room-name").update(f"Room: {room_name}")
        except Exception as e:
            self.notify(f"ルーム参加エラー: {str(e)}", severity="error")

    async def send_message(self, message: str):
        """メッセージの送信"""
        try:
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
            await self.sio.emit("message", message_data)
        except Exception as e:
            self.notify(f"メッセージ送信エラー: {str(e)}", severity="error")

    async def leave_room(self):
        """ルームからの退出"""
        if self.current_room:
            try:
                await self.sio.emit("leave")
                self.current_room = None
                # メッセージログをクリアしてから画面を切り替える
                chat_screen = self.get_screen("chat")
                chat_screen.clear_messages()
                await self.pop_screen()
                room_selector = self.get_screen("room_selector")
                room_selector.rooms = []
            except Exception as e:
                self.notify(f"ルーム退出エラー: {str(e)}", severity="error")

    async def handle_key(self, event) -> None:
        """キー入力ハンドラ"""
        if event.key == "escape":
            await self.leave_room()

    async def on_mount(self) -> None:
        """アプリケーション起動時の処理"""
        if not self.username:
            await self.push_screen("login")
        else:
            await self.connect_to_server()
            await self.push_screen("room_selector")

    async def on_unmount(self) -> None:
        """アプリケーション終了時の処理"""
        if self.sio.connected:
            try:
                await self.sio.emit("disconnect")
                await self.sio.disconnect()
            except Exception as e:
                self.notify(f"切断エラー: {str(e)}", severity="error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", default="http://localhost:5000")
    parser.add_argument("-n", "--name")
    args = parser.parse_args()

    app = ChatApp(url=args.url, username=args.name)
    app.run()


if __name__ == "__main__":
    main()
