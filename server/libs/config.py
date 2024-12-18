from ast import literal_eval
import os

import dotenv

dotenv.load_dotenv()


class AppConfig:
    """flaskの設定"""

    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    JSON_AS_ASCII = False


SYSTEM_USER = "system"
SYSTEM_LOBBY = "sys_lobby"

DATABASE = os.getenv("DATABASE", "storage.db")
MAX_BUFFER_SIZE = os.getenv("MAX_BUFFER_SIZE", 1024**2 * 10)
JOIN_MESSAGES = os.getenv("JOIN_MESSAGES", 10)
MAX_FILES = os.getenv("MAX_FILES", 20)
LOG_SYSTEM = literal_eval(os.getenv("LOG_SYSTEM", "False").capitalize())
FILE_FOLDER = os.getenv("FILE_FOLDER", "files")
