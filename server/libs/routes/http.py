from flask import Blueprint, jsonify, send_file
from libs.storage import get_db


http_module = Blueprint("http_routes", __name__)


@http_module.route("/")
def main():
    return jsonify({"status": "http online"})


@http_module.get("/files/<int:id>")
def get_file(id: int):
    """ファイルダウンロード"""
    conn = get_db()
    file = conn.execute("select * from files where id=?", (id)).fetchone()
    file_path = f"/files/{file['file']}"

    return send_file(file_path, download_name=file.file)
