from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from libs import config, storage
from libs.args import args
from libs.routes.http import http_module
from libs.routes.ws import register_socket_routes


def create_app():
    """flask初期化"""
    app = Flask(__name__)

    CORS(app, resources={"/*": {"origins": "*"}})
    app.config.from_object(config.AppConfig)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    socketio = SocketIO(
        app, cors_allowed_origins="*", max_http_buffer_size=config.MAX_BUFFER_SIZE
    )

    app.register_blueprint(http_module)
    register_socket_routes(socketio)

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    storage.init()
    socketio.run(
        app,
        host="0.0.0.0" if args.host else None,
        port=args.port,
        debug=args.debug,
        allow_unsafe_werkzeug=True,
    )
