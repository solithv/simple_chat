import sqlite3
from functools import wraps

from libs.config import DATABASE


def get_db():
    """DB接続"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def transact(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    return wrapper


@transact
def init_db(conn: sqlite3.Connection):
    """DB初期化"""
    # ルームテーブル
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime'))
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    # ユーザテーブル
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            socket_id TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime'))
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    # ルーム参加テーブル
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS joins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    # メッセージテーブル
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    # 画像テーブル
    conn.execute(
        # imageはbase64エンコードされた画像
        """
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            image TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    # ファイルテーブル
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            file TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trigger_rooms_updated_at AFTER UPDATE ON rooms
        BEGIN
            UPDATE rooms SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
        END
        """
    )

    conn.execute("DELETE FROM joins")
    conn.execute("UPDATE rooms SET is_active = false")
    conn.execute("UPDATE users SET is_active = false")
    conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", ("system",))
    conn.commit()
