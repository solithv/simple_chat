import sqlite3

from flask import request
from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room
from libs.config import JOIN_MESSAGES, LOG_SYSTEM
from libs.routes.http import generate_link
from libs.storage import cursor_transact, decode_file, transact


@transact
def get_available_rooms(conn: sqlite3.Connection):
    """部屋一覧を取得"""
    available_rooms = conn.execute(
        """
        SELECT r.name, COUNT(j.id) as count
        FROM rooms r
        INNER JOIN joins j ON r.id = j.room_id
        WHERE r.is_active = true
        GROUP BY r.name
        ORDER BY count DESC
        """
    ).fetchall()
    available_rooms = [dict(room) for room in available_rooms]
    return available_rooms


def register_socket_routes(socketio: SocketIO):
    @socketio.on("connect")
    def handle_connect():
        """接続処理"""
        available_rooms = get_available_rooms()
        join_room("sys_lobby")  # ロビー
        emit("rooms", available_rooms)

    @socketio.on("disconnect")
    @transact
    def handle_disconnect(conn: sqlite3.Connection):
        """切断処理"""
        client = conn.execute(
            "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
        ).fetchone()
        room = conn.execute(
            """
            SELECT r.id, r.name, COUNT(j.id) as join_count
            FROM rooms r
            INNER JOIN joins j ON r.id = j.room_id
            INNER JOIN users u ON u.id = j.user_id
            WHERE r.id IN (
                SELECT r.id
                FROM joins
                JOIN users ON joins.user_id = users.id
                WHERE users.socket_id = ?
            )
            GROUP BY r.id
            """,
            (request.sid,),
        ).fetchone()

        if room and room["id"]:
            # leave が未処理
            print(f"disconnect {client and dict(client)}")
            if room["join_count"] <= 1:
                conn.execute(
                    "UPDATE rooms SET is_active = false WHERE id = ?", (room["id"],)
                )
            conn.execute("DELETE FROM joins WHERE user_id = ?", (client["id"],))
            if LOG_SYSTEM:
                sys_user = conn.execute(
                    "SELECT id FROM users WHERE name = ?", ("system",)
                ).fetchone()
                conn.execute(
                    "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                    (
                        room["id"],
                        sys_user["id"],
                        f"{client['name']} has leaved the room.",
                    ),
                )
            emit(
                "message",
                {"user": "system", "message": f"{client['name']} has leaved the room."},
                to=str(room["id"]),
            )
            conn.commit()
            available_rooms = get_available_rooms()
            emit("rooms", available_rooms, to="sys_lobby")

        leave_room("sys_lobby")
        conn.execute(
            "UPDATE users SET is_active = false WHERE socket_id = ?", (request.sid,)
        )

    @socketio.on("join")
    @transact
    def handle_join(conn: sqlite3.Connection, data):
        """部屋に参加"""
        client = conn.execute(
            "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
        ).fetchone()
        if not client:
            # 新規接続
            print("not client")
            client = conn.execute(
                "SELECT * FROM users WHERE name = ?", (data["name"],)
            ).fetchone()
            if client:
                # DBに同一ユーザ名の登録がある
                if client["is_active"]:
                    # すでに接続されているユーザ名の時は切断
                    emit(
                        "error",
                        {"message": f"username {data['name']} is already used."},
                    )
                    disconnect()
                    return
                conn.execute(
                    "UPDATE users SET socket_id = ?, is_active = true WHERE name = ?",
                    (request.sid, data["name"]),
                )
            else:
                # ユーザ新規登録
                conn.execute(
                    "INSERT INTO users (name, socket_id) VALUES (?, ?)",
                    (data["name"], request.sid),
                )
                client = conn.execute(
                    "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
                ).fetchone()
        elif client["name"] != data["name"]:
            # ユーザ名変更
            print("change name")
            exists_client = conn.execute(
                "SELECT * FROM users WHERE name = ? AND is_active = true",
                (data["name"],),
            ).fetchone()
            if exists_client:
                emit("error", {"message": f"username {data['name']} is already used."})
                disconnect()
                return
            conn.execute(
                "UPDATE users SET is_active = false WHERE name = ?", (client["name"],)
            )
            conn.execute(
                "UPDATE users SET name = ?, is_active = true WHERE socket_id = ?",
                (data["name"], request.sid),
            )

        room = conn.execute(
            "SELECT id FROM rooms WHERE name = ?", (data["room"],)
        ).fetchone()
        if not room:
            # ルームを作成
            conn.execute("INSERT INTO rooms (name) VALUES (?)", (data["room"],))
            room = conn.execute(
                "SELECT id FROM rooms WHERE name = ?", (data["room"],)
            ).fetchone()

        conn.execute(
            "INSERT INTO joins (room_id, user_id) VALUES (?, ?)",
            (room["id"], client["id"]),
        )
        conn.execute("UPDATE rooms SET is_active = true WHERE id = ?", (room["id"],))
        if LOG_SYSTEM:
            sys_user = conn.execute(
                "SELECT id FROM users WHERE name = ?", ("system",)
            ).fetchone()
            conn.execute(
                "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                (room["id"], sys_user["id"], f"{client['name']} has entered the room."),
            )
        messages = conn.execute(
            """
            SELECT u.name as user, m.message, m.updated_at
            FROM messages m
            INNER JOIN rooms r ON m.room_id = r.id
            INNER JOIN users u ON m.user_id = u.id
            WHERE r.id = ?
            ORDER BY m.updated_at DESC
            LIMIT ?
            """,
            (room["id"], JOIN_MESSAGES),
        ).fetchall()

        leave_room("sys_lobby")
        join_room(str(room["id"]))
        emit(
            "joined",
            [dict(message) for message in messages[::-1]],
        )
        emit(
            "message",
            {"user": "system", "message": f"{client['name']} has entered the room."},
            to=str(room["id"]),
        )
        conn.commit()
        available_rooms = get_available_rooms()
        emit("rooms", available_rooms, to="sys_lobby")

    @socketio.on("leave")
    @transact
    def handle_leave(conn: sqlite3.Connection):
        """部屋から退出"""
        client = conn.execute(
            "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
        ).fetchone()
        room = conn.execute(
            """
            SELECT r.id, r.name, COUNT(j.id) as join_count
            FROM rooms r
            INNER JOIN joins j ON r.id = j.room_id
            INNER JOIN users u ON u.id = j.user_id
            WHERE r.id IN (
                SELECT r.id
                FROM joins
                JOIN users ON joins.user_id = users.id
                WHERE users.socket_id = ?
            )
            GROUP BY r.id
            """,
            (request.sid,),
        ).fetchone()
        if room["join_count"] <= 1:
            # 部屋が空になる
            conn.execute(
                "UPDATE rooms SET is_active = false WHERE id = ?", (room["id"],)
            )
        conn.execute("DELETE FROM joins WHERE user_id = ?", (client["id"],))
        if LOG_SYSTEM:
            sys_user = conn.execute(
                "SELECT id FROM users WHERE name = ?", ("system",)
            ).fetchone()
            conn.execute(
                "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                (room["id"], sys_user["id"], f"{client['name']} has leaved the room."),
            )

        leave_room(str(room["id"]))
        join_room("sys_lobby")
        emit(
            "message",
            {"user": "system", "message": f"{client['name']} has leaved the room."},
            to=str(room["id"]),
        )
        conn.commit()
        available_rooms = get_available_rooms()
        emit("rooms", available_rooms, to="sys_lobby")

    @socketio.on("message")
    @transact
    def handle_message(conn: sqlite3.Connection, data):
        """テキストメッセージ受信"""
        with cursor_transact(conn) as cur:
            client = cur.execute(
                "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
            ).fetchone()
            room = cur.execute(
                """
                SELECT r.id
                FROM rooms r
                INNER JOIN joins j ON r.id = j.room_id
                INNER JOIN users u ON j.user_id = u.id
                WHERE u.socket_id = ? AND r.is_active = true
                """,
                (request.sid,),
            ).fetchone()
            cur.execute(
                "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                (room["id"], client["id"], data["message"]),
            )
            emit(
                "message",
                {"user": client["name"], "message": data["message"]},
                to=str(room["id"]),
            )

    @socketio.on("image")
    @transact
    def handle_image(conn: sqlite3.Connection, data):
        """画像受信"""
        with cursor_transact(conn) as cur:
            client = cur.execute(
                "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
            ).fetchone()
            room = cur.execute(
                """
                SELECT r.id
                FROM rooms r
                INNER JOIN joins j ON r.id = j.room_id
                INNER JOIN users u ON j.user_id = u.id
                WHERE u.socket_id = ? AND r.is_active = true
                """,
                (request.sid,),
            ).fetchone()
            cur.execute(
                "INSERT INTO images (room_id, user_id, image) VALUES (?, ?, ?)",
                (room["id"], client["id"], data["image"]),
            )
            emit(
                "message",
                {"user": client["name"], "image": data["image"]},
                to=str(room["id"]),
            )

    @socketio.on("file")
    @transact
    def handle_file(conn: sqlite3.Connection, data):
        """ファイル受信"""
        with cursor_transact(conn) as cur:
            client = cur.execute(
                "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
            ).fetchone()
            room = cur.execute(
                """
                SELECT r.id
                FROM rooms r
                INNER JOIN joins j ON r.id = j.room_id
                INNER JOIN users u ON j.user_id = u.id
                WHERE u.socket_id = ? AND r.is_active = true
                """,
                (request.sid,),
            ).fetchone()

            file_id = cur.lastrowid
            file_path = decode_file(data["file_data"], data["filename"], file_id)
            cur.execute(
                "INSERT INTO files (room_id, user_id, filename, save_name) VALUES (?, ?, ?, ?)",
                (room["id"], client["id"], data["filename"], file_path),
            )
            link = generate_link(file_path)
            emit(
                "message",
                {"user": client["name"], "filename": data["filename"], "link": link},
                to=str(room["id"]),
            )

        cur.close()
