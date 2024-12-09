import sqlite3

from flask import Blueprint, abort, jsonify, render_template, send_file
from libs.storage import transact

from libs.config import PREFIX

http_module = Blueprint("http_routes", __name__)


@http_module.route(f"{PREFIX}/")
def main():
    return jsonify({"status": "http online"})


@http_module.route(f"{PREFIX}/test")
def test_client():
    return render_template("index.html")


@http_module.get(f"{PREFIX}/files/<int:id>/<filename>")
@transact
def get_file(conn: sqlite3.Connection, id: int, filename: str):
    """ファイルダウンロード"""
    file = conn.execute(
        "SELECT * FROM files WHERE id = ? AND filename = ?", (id, filename)
    ).fetchone()
    if file is None:
        abort(404)
    file_path = file["save_name"]

    return send_file(file_path, download_name=file["filename"])
