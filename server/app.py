import os
from flask import Flask
from dotenv import load_dotenv
from flask_socketio import SocketIO
from libs.args import args

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24))

socketio = SocketIO(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=args.port, debug=args.debug)
