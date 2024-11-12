import os

import dotenv

dotenv.load_dotenv()


class AppConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    JSON_AS_ASCII = False


DATABASE = os.getenv("DATABASE", "storage.db")
