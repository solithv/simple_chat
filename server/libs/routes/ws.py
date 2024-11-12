from flask import json, jsonify, request, session
from flask_socketio import SocketIO, emit, join_room, rooms, send
from libs.storage import conn, cursor


def register_socket_routes(socketio: SocketIO):
    @socketio.on("ping")
    def handle_ping(data=None):
        return data or "pong"

    @socketio.on("connect")
    def handle_connect(data):
        socket_id = request.sid
        cursor.execute(
            "INSERT INTO users (name, socket_id) VALUES (?, ?)",
            (data["name"], socket_id),
        )
        client = cursor.execute(
            "SELECT * FROM users WHERE socket_id=?", (socket_id)
        ).fetchone()
        available_rooms = cursor.execute(
            """
            SELECT r.id, r.name, COUNT(j.id) as join_count
            FROM rooms r
            LEFT JOIN joins j ON r.id = j.room_id
            WHERE r.is_active = true
            GROUP BY r.id, r.name
            ORDER BY r.id
            """
        ).fetchall()
        available_rooms = [
            {"name": room.name, "count": room.join_count} for room in available_rooms
        ]
        return jsonify(
            {
                "status": "connected",
                "rooms": available_rooms,
                "info": {
                    "client_id": client.id,
                    "client_socket_id": socket_id,
                },
            }
        )

    @socketio.on("disconnect")
    def handle_disconnect():
        client = cursor.execute(
            "SELECT * FROM users WHERE socket_id=?", (request.sid)
        ).fetchone()
        cursor.execute("DELETE FROM joins WHERE user_id=?", client.id)
        cursor.execute(
            "UPDATE users SET is_active=false WHERE socket_id=?", (request.sid)
        )

    @socketio.on("join")
    def handle_join(data):
        room_id = cursor.execute(
            "SELECT id from rooms where name=?", (data["room"])
        ).fetchone()
        client = cursor.execute(
            "SELECT * FROM users WHERE socket_id=?", (request.sid)
        ).fetchone()
        if not room_id:
            cursor.execute("INSERT INTO rooms (name) VALUES (?)", (data["room"]))
            room_id = cursor.execute(
                "SELECT id from rooms where name=?", (data["room"])
            ).fetchone()
        room = str(room_id)
        join_room(room)
        cursor.execute(
            "INSERT INTO joins (room_id, user_id) VALUES (?, ?)", (room_id, client.id)
        )
        emit(
            "message",
            {"user": "system", "message": f"{client.name} has entered the room."},
            to=room,
        )

    @socketio.on("leave")
    def handle_leave():
        client = cursor.execute(
            "SELECT * FROM users WHERE socket_id=?", (request.sid)
        ).fetchone()
        room = cursor.execute(
            """
            SELECT r.id as room_id, r.name as room_name, COUNT(j.id) as join_count
            FROM rooms r
            INNER JOIN joins j ON r.id = j.room_id
            INNER JOIN users u ON j.user_id = u.id
            WHERE u.socket_id = ? AND r.is_active = true
            """,
            (request.sid),
        ).fetchone()
        if room.join_count <= 1:
            cursor.execute(
                "UPDATE rooms SET is_active=false WHERE id=?", (room.room_id)
            )
        cursor.execute("DELETE FROM joins WHERE user_id=?", (client.id))

    @socketio.on("message")
    def handle_message(data):
        client = cursor.execute(
            "SELECT * FROM users WHERE socket_id=?", (request.sid)
        ).fetchone()
        room = cursor.execute(
            """
            SELECT r.id as room_id
            FROM rooms r
            INNER JOIN joins j ON r.id = j.room_id
            INNER JOIN users u ON j.user_id = u.id
            WHERE u.socket_id = ? AND r.is_active = true
            """,
            (request.sid),
        ).fetchone()
        cursor.execute(
            "INSERT messages INTO (room_id, user_id, message) VALUES (?, ?, ?)",
            (room.id, client.id, data),
        )
        emit("message", {"user": client.name, "message": data}, to=str(room.id))
