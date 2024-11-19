import sqlite3

from flask import Blueprint, jsonify, send_file
from libs.storage import transact

http_module = Blueprint("http_routes", __name__)


@http_module.route("/")
def main():
    return jsonify({"status": "http online"})


@http_module.get("/files/<int:id>")
@transact
def get_file(conn: sqlite3.Connection, id: int):
    """ファイルダウンロード"""
    file = conn.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    file_path = file["save_name"]

    return send_file(file_path, download_name=file.file)


def generate_link(file_path: str):
    # TODO: download link generate
    file_path
