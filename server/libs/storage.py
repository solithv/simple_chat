import sqlite3
from libs.config import DATABASE
from contextlib import contextmanager
from functools import wraps


@contextmanager
def transaction():
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def transactional(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if conn.in_transaction:
            return func(*args, **kwargs)
        else:
            try:
                result = func(*args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                raise e

    return decorator


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.autocommit
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    return conn, cursor


conn, cursor = get_db()


def init_db():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            socket_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS joins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER UNIQUE NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            file TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
