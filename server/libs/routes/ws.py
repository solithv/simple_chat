import sqlite3

from flask import request
from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room
from libs.config import JOIN_MESSAGES, LOG_SYSTEM, SYSTEM_LOBBY, SYSTEM_USER
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
    @transact
    def handle_connect(conn: sqlite3.Connection):
        """接続処理"""
        name = request.args.get("name")
        if name is None:
            emit("error", {"message": "name is required."})
            disconnect()
        client = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
        if client:
            # DBに同一ユーザ名の登録がある
            if client["is_active"]:
                # すでに接続されているユーザ名の時は切断
                emit(
                    "error",
                    {"message": f"username {name} is already used."},
                )
                disconnect()
                return
            conn.execute(
                "UPDATE users SET socket_id = ?, is_active = true WHERE name = ?",
                (request.sid, name),
            )
        else:
            # ユーザ新規登録
            conn.execute(
                "INSERT INTO users (name, socket_id) VALUES (?, ?)",
                (name, request.sid),
            )

        available_rooms = get_available_rooms()
        join_room(SYSTEM_LOBBY)  # ロビー
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
                    "SELECT id FROM users WHERE name = ?", (SYSTEM_USER,)
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
                {
                    "user": SYSTEM_USER,
                    "message": f"{client['name']} has leaved the room.",
                },
                to=str(room["id"]),
            )
            conn.commit()
            available_rooms = get_available_rooms()
            emit("rooms", available_rooms, to=SYSTEM_LOBBY)

        leave_room(SYSTEM_LOBBY)
        conn.execute(
            "UPDATE users SET is_active = false WHERE socket_id = ?", (request.sid,)
        )

    @socketio.on("join")
    @transact
    def handle_join(conn: sqlite3.Connection, data):
        """部屋に参加"""
        if data["room"] == SYSTEM_LOBBY:
            emit("error", {"message": f"{SYSTEM_LOBBY} is used by system."})
            disconnect()
        client = conn.execute(
            "SELECT * FROM users WHERE socket_id = ?", (request.sid,)
        ).fetchone()
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
                "SELECT id FROM users WHERE name = ?", (SYSTEM_USER,)
            ).fetchone()
            conn.execute(
                "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                (room["id"], sys_user["id"], f"{client['name']} has entered the room."),
            )
        messages = conn.execute(
            """
            WITH combined_data AS (
                SELECT
                    u.name AS user,
                    m.message,
                    NULL AS image,
                    NULL AS filename,
                    NULL AS link,
                    m.updated_at
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.room_id = ?

                UNION ALL

                SELECT
                    u.name AS user,
                    NULL AS message,
                    i.image,
                    NULL AS filename,
                    NULL AS link,
                    i.updated_at
                FROM images i
                JOIN users u ON i.user_id = u.id
                WHERE i.room_id = ?

                UNION ALL

                SELECT
                    u.name AS user,
                    NULL AS message,
                    NULL AS image,
                    f.filename,
                    f.link,
                    f.updated_at
                FROM files f
                JOIN users u ON f.user_id = u.id
                WHERE f.room_id = ?
            )
            SELECT user, message, image, filename, link
            FROM combined_data
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (room["id"], room["id"], room["id"], JOIN_MESSAGES),
        ).fetchall()
        conn.commit()

        leave_room(SYSTEM_LOBBY)
        join_room(str(room["id"]))
        [emit("message", dict(m)) for m in messages[::-1]]
        emit(
            "message",
            {"user": SYSTEM_USER, "message": f"{client['name']} has entered the room."},
            to=str(room["id"]),
        )
        conn.commit()
        available_rooms = get_available_rooms()
        emit("rooms", available_rooms, to=SYSTEM_LOBBY)

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
                "SELECT id FROM users WHERE name = ?", (SYSTEM_USER,)
            ).fetchone()
            conn.execute(
                "INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)",
                (room["id"], sys_user["id"], f"{client['name']} has leaved the room."),
            )

        leave_room(str(room["id"]))
        join_room(SYSTEM_LOBBY)
        emit(
            "message",
            {"user": SYSTEM_USER, "message": f"{client['name']} has leaved the room."},
            to=str(room["id"]),
        )
        conn.commit()
        available_rooms = get_available_rooms()
        emit("rooms", available_rooms, to=SYSTEM_LOBBY)

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

            cur.execute(
                "INSERT INTO files (room_id, user_id, filename) VALUES (?, ?, ?)",
                (room["id"], client["id"], data["filename"]),
            )
            file_id = cur.lastrowid
            file_path = decode_file(data["file_data"], data["filename"], file_id)
            link = f"/files/{file_id}/{data['filename']}"
            cur.execute(
                "UPDATE files SET save_name = ?, link = ? WHERE id = ?",
                (file_path, link, file_id),
            )
            emit(
                "message",
                {"user": client["name"], "filename": data["filename"], "link": link},
                to=str(room["id"]),
            )

        cur.close()
