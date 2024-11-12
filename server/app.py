from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from libs import config
from libs.args import args
from libs.routes.http import http_module
from libs.routes.ws import register_socket_routes
from libs import storage


def create_app():
    app = Flask(__name__)

    CORS(app, resources={"/*": {"origins": "*"}})
    app.config.from_object(config.AppConfig)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    socketio = SocketIO(app, cors_allowed_origins="*")

    app.register_blueprint(http_module)
    register_socket_routes(socketio)

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    storage.init_db()
    socketio.run(
        app, host="0.0.0.0" if args.host else None, port=args.port, debug=args.debug
    )
