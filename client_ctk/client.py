import base64
from io import BytesIO
import os
import customtkinter
import tkextrafont
from PIL import Image
from customtkinter import filedialog
from alert import Alert
import ws
import time
import requests
import re

URL = "https://chat.solithv7247.duckdns.org/"
# URL = "http://127.0.0.1:5000"

"""基底クラス"""


class App(customtkinter.CTk):

    activeWidgets = []

    username = None
    isRoomUpdated = True
    rooms = []

    isConnected = False

    """初期化"""

    def __init__(self):
        super().__init__()

        """画像読み込み"""
        self.roomImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "room.png")),
            size=(100, 100),
        )
        self.addRoomImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "addRoom.png")),
            size=(30, 30),
        )
        self.quitImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "quit.png")),
            size=(30, 30),
        )
        self.attachImageImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "attachImage.png")),
            size=(30, 30),
        )
        self.attachFileImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "attachFile.png")),
            size=(30, 30),
        )
        self.attachImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "attach.png")),
            size=(30, 30),
        )
        self.submitImage = customtkinter.CTkImage(
            Image.open(os.path.join(os.path.dirname(__file__), "submit.png")),
            size=(30, 30),
        )

        """CTKのテーマ"""
        customtkinter.set_appearance_mode("system")
        customtkinter.set_default_color_theme("green")

        """ウィンドウのあれこれ"""
        self.geometry("960x540")
        self.title("simple chat")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.onWindowClose)

        """フォント読み込み"""
        tkextrafont.Font(file=os.path.dirname(__file__))
        self.font = customtkinter.CTkFont(family="APJapanesefont", size=30)

        """socketio初期化"""
        self.wsManager = ws.SimpleChatWSManager()
        self.wsManager.onDisconnect(self.onDisconnect)
        self.wsManager.onRooms(self.onRooms)
        self.wsManager.onError(self.onError)

        """名前決めさせる画面表示"""
        self.FirstContact(master=self)

    """画面を閉じたとき"""

    def onWindowClose(self):

        self.wsManager.offDisconnect()
        if self.isConnected:
            self.wsManager.disconnect()
            self.isConnected = False

        """画面閉じる"""
        self.destroy()

    def onDisconnect(self):
        self.isConnected = False

        for widget in self.activeWidgets:
            widget.destroy()
        self.activeWidgets.clear()

        alert = Alert(text="接続が切断されました", title="Error", font=self.font)
        alert.wait()

        """名前決めさせる画面表示"""
        self.FirstContact(master=self)

    def onError(self, message):
        self.wsManager.offDisconnect()

        for widget in self.activeWidgets:
            widget.destroy()
        self.activeWidgets.clear()

        alert = Alert(
            text=f"エラーが発生しました\ncode: {message["code"]}\nmessage: {message["message"]}",
            title="Error",
            font=self.font,
        )
        alert.wait()

        self.isConnected = False
        self.wsManager.disconnect()
        self.wsManager.onDisconnect(self.onDisconnect)

        """名前決めさせる画面表示"""
        self.FirstContact(master=self)

    """部屋一覧を受け取ったとき"""

    def onRooms(self, rooms):

        self.rooms = rooms
        self.isRoomUpdated = True

    """名前決める画面"""

    class FirstContact(customtkinter.CTkFrame):
        """初期化"""

        def __init__(self, master, **kwargs):
            super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)

            """ウィジェット配置"""
            self.grid_columnconfigure(0, weight=1)

            label = customtkinter.CTkLabel(
                master=self,
                text="あなたの名前を入力してください。",
                fg_color="transparent",
                font=master.font,
            )
            label.grid(row=0, column=0, padx=20, pady=20)

            self.inputName = customtkinter.CTkEntry(
                master=self, placeholder_text="名前", width=220, font=master.font
            )
            self.inputName.bind("<Return>", lambda event: self.onSubmit())
            self.inputName.grid(row=1, column=0, padx=20, pady=20)

            submit = customtkinter.CTkButton(
                master=self,
                text="決定",
                width=220,
                command=self.onSubmit,
                font=master.font,
            )
            submit.grid(row=2, column=0, padx=20, pady=20)

            self.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            self.master.activeWidgets.append(self)

        """決定ボタンを押したとき"""

        def onSubmit(self):
            """名前を取得"""
            self.master.username = self.inputName.get()

            if self.master.username == "":
                return

            """サーバに接続"""
            try:
                self.master.wsManager.connect(URL, self.master.username)
            except Exception as e:
                print(e)
                alert = Alert(
                    text="接続ができませんでした", title="Error", font=self.master.font
                )
                alert.wait()
                return

            self.master.isConnected = True

            """画面を消す"""
            self.destroy()
            self.master.activeWidgets.remove(self)

            """部屋選択画面表示"""
            self.master.RoomSelect(master=self.master)

    """部屋選択画面"""

    class RoomSelect(customtkinter.CTkFrame):

        isDestroyed = False

        """部屋のウィジェットの配列"""
        roomButtons = []

        """初期化"""

        def __init__(self, master, **kwargs):
            super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)

            """ウィジェット配置"""
            self.grid_rowconfigure(1, weight=1)
            self.grid_columnconfigure(0, weight=1)

            navContainer = customtkinter.CTkFrame(master=self, corner_radius=0)
            navContainer.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            navContainer.grid_columnconfigure((1,), weight=1)

            addRoomButton = customtkinter.CTkButton(
                master=navContainer,
                text="",
                fg_color="transparent",
                image=master.addRoomImage,
                width=50,
                height=50,
                command=self.onClickAddRoom,
            )
            addRoomButton.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            label = customtkinter.CTkLabel(
                master=navContainer,
                text="アクティブなルーム一覧",
                fg_color="transparent",
                font=master.font,
            )
            label.grid(row=0, column=1, padx=5, pady=5)

            space = customtkinter.CTkFrame(
                master=navContainer,
                corner_radius=0,
                fg_color="transparent",
                width=50,
                height=50,
            )
            space.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

            self.roomContainer = customtkinter.CTkScrollableFrame(
                master=self, corner_radius=0, fg_color="transparent"
            )
            self.roomContainer.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
            self.roomContainer.grid_columnconfigure((0, 1, 2), weight=1)

            self.updateRoom()

            self.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            self.master.activeWidgets.append(self)

        """部屋が更新されてるか確認"""

        def updateRoom(self):
            """部屋が更新されたか"""
            if self.isDestroyed:
                return

            if self.master.isRoomUpdated:

                """部屋の更新状態を止める"""
                self.master.isRoomUpdated = False

                """古いウィジェットを削除"""
                for roomButton in self.roomButtons:
                    roomButton.destroy()
                self.roomButtons.clear()

                """新しいウィジェットを配置"""
                for i, room in enumerate(self.master.rooms):
                    roomButton = (
                        lambda roomname: customtkinter.CTkButton(
                            master=self.roomContainer,
                            text=roomname,
                            font=self.master.font,
                            image=self.master.roomImage,
                            compound="top",
                            command=lambda: self.onSubmit(roomname),
                        )
                    )(room["name"])
                    roomButton.grid(
                        row=int(i / 3), column=i % 3, padx=5, pady=5, sticky="ew"
                    )
                    self.roomButtons.append(roomButton)

            """100ms後に同じことをする"""
            self.master.after(100, self.updateRoom)

        """部屋決定したとき"""

        def onSubmit(self, roomname):
            """部屋情報のイベントハンドラ削除"""
            self.master.wsManager.offRooms()

            self.joinRoom(roomname)

        """部屋追加ボタンを押したとき"""

        def onClickAddRoom(self):
            dialog = customtkinter.CTkInputDialog(
                text="ルーム名", title="add/join room", font=self.master.font
            )
            roomname = dialog.get_input()

            """キャンセル"""
            if roomname == None:
                return

            self.joinRoom(roomname)

        def joinRoom(self, roomname):
            """部屋加入"""
            self.master.wsManager.join(roomname)

            """画面を消す"""
            self.destroy()
            self.master.activeWidgets.remove(self)
            self.isDestroyed = True

            """部屋一覧の情報を常に更新状態に"""
            self.master.isRoomUpdated = True

            """チャット画面表示"""
            self.master.Room(master=self.master)

    """チャット画面"""

    class Room(customtkinter.CTkFrame):

        isDestroyed = False

        """メッセージの配列"""
        messages = []
        images = []

        addedMessages = []

        """初期化"""

        def __init__(self, master, **kwargs):
            super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)

            """メッセージのイベントハンドラ登録"""
            master.wsManager.onMessage(self.onMessage)

            """ウィジェット配置"""
            self.grid_rowconfigure(1, weight=1)
            self.grid_columnconfigure(0, weight=1)

            navContainer = customtkinter.CTkFrame(master=self, corner_radius=0)
            navContainer.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            navContainer.grid_columnconfigure((1,), weight=1)

            quitButton = customtkinter.CTkButton(
                master=navContainer,
                text="",
                fg_color="transparent",
                image=master.quitImage,
                width=50,
                height=50,
                command=self.onQuit,
            )
            quitButton.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            label = customtkinter.CTkLabel(
                master=navContainer,
                text="ルーム",
                fg_color="transparent",
                font=master.font,
            )
            label.grid(row=0, column=1, padx=5, pady=5, columnspan=2)

            space = customtkinter.CTkFrame(
                master=navContainer,
                corner_radius=0,
                fg_color="transparent",
                width=50,
                height=50,
            )
            space.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

            self.messageContainer = customtkinter.CTkScrollableFrame(
                master=self, corner_radius=0, fg_color="transparent"
            )
            self.messageContainer.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
            self.messageContainer.grid_columnconfigure((0, 1, 2), weight=1)

            formContainer = customtkinter.CTkFrame(master=self, corner_radius=0)
            formContainer.grid(row=2, column=0, padx=0, pady=0, sticky="nsew")
            formContainer.grid_columnconfigure((1,), weight=1)

            attachButton = customtkinter.CTkButton(
                master=formContainer,
                text="",
                fg_color="transparent",
                image=master.attachImage,
                width=50,
                height=50,
                command=self.onClickAttach,
            )
            attachButton.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            self.inputMessage = customtkinter.CTkEntry(
                master=formContainer,
                placeholder_text="ここにメッセージを入力してください",
                font=master.font,
            )
            self.inputMessage.bind("<Return>", lambda event: self.onSubmit())
            self.inputMessage.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

            submitButton = customtkinter.CTkButton(
                master=formContainer,
                text="",
                fg_color="transparent",
                image=master.submitImage,
                width=50,
                height=50,
                command=self.onSubmit,
            )
            submitButton.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

            self.updateMessages()

            self.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            self.master.activeWidgets.append(self)

        def onMessage(self, message):
            self.addedMessages.append(message)

        def updateMessages(self):
            """画面が変わったら"""
            if self.isDestroyed:
                return

            for message in self.addedMessages:

                isMineMessage = message["user"] == self.master.username
                messageIndex = len(self.messages)
                self.messages.append(message)

                if message.get("message"):

                    if isMineMessage:
                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="light green",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=1,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=100,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=message["message"],
                            fg_color="light green",
                            hover_color="green",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=1,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                    else:
                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="white",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=message["message"],
                            fg_color="white",
                            hover_color="gray",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=100,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                elif message.get("image"):

                    image = Image.open(BytesIO(base64.b64decode(message["image"])))
                    self.images.append(image)
                    ctkImage = customtkinter.CTkImage(
                        Image.open(BytesIO(base64.b64decode(message["image"]))),
                        size=(300, 300 * image.height / image.width),
                    )

                    if isMineMessage:
                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="light green",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=1,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=200,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text="",
                            image=ctkImage,
                            fg_color="transparent",
                            hover_color="green",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=1,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                    else:
                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="white",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text="",
                            image=ctkImage,
                            fg_color="transparent",
                            hover_color="gray",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=200,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                elif message.get("filename") and message.get("link"):

                    if isMineMessage:
                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="light green",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=1,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=100,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=message["filename"],
                            image=self.master.attachFileImage,
                            compound="top",
                            fg_color="light green",
                            hover_color="green",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=1,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                    else:
                        nameWidget = customtkinter.CTkLabel(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=f"{message["user"]} : {message["timestamp"]}",
                            fg_color="white",
                            text_color="black",
                            font=self.master.font,
                        )
                        nameWidget.grid(
                            row=messageIndex * 2,
                            column=0,
                            padx=5,
                            pady=(5, 1.25),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=50,
                        )
                        space.grid(
                            row=messageIndex * 2,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

                        messageWidget = customtkinter.CTkButton(
                            master=self.messageContainer,
                            corner_radius=10,
                            text=message["filename"],
                            image=self.master.attachFileImage,
                            compound="top",
                            fg_color="white",
                            hover_color="gray",
                            text_color="black",
                            font=self.master.font,
                            command=(
                                lambda messageIndex: lambda: self.onClickMessage(
                                    messageIndex
                                )
                            )(messageIndex),
                        )
                        messageWidget.grid(
                            row=messageIndex * 2 + 1,
                            column=0,
                            padx=5,
                            pady=(1.25, 5),
                            columnspan=2,
                            sticky="nsew",
                        )

                        space = customtkinter.CTkFrame(
                            master=self.messageContainer,
                            corner_radius=0,
                            fg_color="transparent",
                            height=100,
                        )
                        space.grid(
                            row=messageIndex * 2 + 1,
                            column=2,
                            padx=0,
                            pady=0,
                            sticky="nsew",
                        )

            self.addedMessages.clear()

            """100ms後に同じことをする"""
            self.master.after(100, self.updateMessages)

        def onQuit(self):

            self.master.wsManager.leave()
            self.master.wsManager.offMessage()

            self.destroy()
            self.master.activeWidgets.remove(self)
            self.isDestroyed = True

            for image in self.images:
                image.close()

            self.master.RoomSelect(master=self.master)

        def onClickAttach(self):
            self.master.Attach(master=self.master)

        def onClickMessage(self, messageIndex):
            message = self.messages[messageIndex]

            if message.get("message"):
                pass

            elif message.get("image"):
                file = filedialog.asksaveasfile(
                    mode="wb",
                    title="Save As",
                    initialfile=f"{message["timestamp"]}.png",
                )

                if not file:
                    return

                fileByteData = base64.b64decode(message["image"])
                file.write(fileByteData)
                file.close()

            elif message.get("filename") and message.get("link"):
                file = filedialog.asksaveasfile(
                    mode="wb",
                    title="Save As",
                    initialfile=message["filename"],
                )

                if not file:
                    return

                link = re.sub("^[/\\\\]", "", message["link"])
                link = os.path.join(URL, link)
                fileByteData = requests.get(link).content
                file.write(fileByteData)
                file.close()

        def onSubmit(self):
            message = self.inputMessage.get()

            if message == "":
                return

            self.inputMessage.delete(0, len(message))
            self.master.wsManager.sendText(message)

    class Attach(customtkinter.CTkFrame):
        def __init__(self, master, **kwargs):
            super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)

            self.grid_rowconfigure((0, 1, 2), weight=1)
            self.grid_columnconfigure(0, weight=1)

            self.quit = customtkinter.CTkButton(
                master=self,
                text="",
                image=master.quitImage,
                command=self.onQuit,
                font=master.font,
            )
            self.quit.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            self.attachImage = customtkinter.CTkButton(
                master=self,
                text="画像添付",
                image=master.attachImageImage,
                compound="left",
                command=self.onAttachImage,
                font=master.font,
            )
            self.attachImage.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

            self.attachFile = customtkinter.CTkButton(
                master=self,
                text="ファイル添付",
                image=master.attachFileImage,
                compound="left",
                command=self.onAttachFile,
                font=master.font,
            )
            self.attachFile.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

            self.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
            self.master.activeWidgets.append(self)

        def onQuit(self):
            self.destroy()
            self.master.activeWidgets.remove(self)

        def onAttachImage(self):
            self.destroy()
            self.master.activeWidgets.remove(self)

            files = filedialog.askopenfiles(
                mode="rb",
                title="Open",
                filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff")],
            )

            if files == ():
                return

            for file in files:
                image = Image.open(file)
                imageBuffer = BytesIO()
                image.save(imageBuffer, format="PNG")
                file.close()
                fileData = base64.b64encode(imageBuffer.getvalue())
                self.master.wsManager.sendImage(fileData)

        def onAttachFile(self):
            self.destroy()
            self.master.activeWidgets.remove(self)

            files = filedialog.askopenfiles(
                mode="rb",
                title="Open",
            )

            if files == ():
                return

            for file in files:
                fileByteData = base64.b64encode(file.read())
                filename = file.name
                file.close()
                fileData = fileByteData.decode("utf-8")
                self.master.wsManager.sendFile(fileData, os.path.basename(filename))


if __name__ == "__main__":
    app = App()
    app.mainloop()
