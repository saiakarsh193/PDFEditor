import os
import shutil
import threading
import time
import uuid

from flask import Flask, jsonify, render_template, request, Response

import pdf_engine
import session_store

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# ---------------------------------------------------------------------------
# Background session cleanup
# ---------------------------------------------------------------------------

def _cleanup_loop():
    while True:
        time.sleep(600)
        for sid in session_store.stale_sessions(max_age_seconds=7200):
            upload_dir = session_store.delete_session(sid)
            if upload_dir:
                shutil.rmtree(upload_dir, ignore_errors=True)


threading.Thread(target=_cleanup_loop, daemon=True).start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_id() -> str | None:
    return request.headers.get("X-Session-ID") or request.args.get("sid")


def _ensure_session(sid: str) -> dict:
    sess = session_store.get_session(sid)
    if sess is None:
        upload_dir = os.path.join(UPLOAD_ROOT, sid)
        os.makedirs(upload_dir, exist_ok=True)
        session_store.create_session_with_id(sid, upload_dir)
        sess = session_store.get_session(sid)
    return sess


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    _ensure_session(sid)
    upload_dir = session_store.get_session(sid)["upload_dir"]

    files = request.files.getlist("files[]")
    if not files:
        return jsonify(error="No files provided"), 400

    added_files = []
    for f in files:
        original_name = f.filename or "upload"
        ext = os.path.splitext(original_name)[1].lower()

        if ext not in pdf_engine.ALLOWED_EXTENSIONS:
            return jsonify(error=f"Unsupported file type: {ext}"), 422

        file_id = str(uuid.uuid4())
        saved_path = os.path.join(upload_dir, file_id + ext)
        f.save(saved_path)

        try:
            pdf_path = pdf_engine.to_pdf(saved_path, original_name)
        except Exception as e:
            return jsonify(error=str(e)), 422

        count = pdf_engine.page_count(pdf_path)
        file_entry = session_store.add_file(sid, file_id, original_name, pdf_path, count)

        added_files.append({
            "file_id": file_entry["file_id"],
            "original_name": file_entry["original_name"],
            "pages": [
                {
                    "page_id": p["page_id"],
                    "source_page_idx": p["source_page_idx"],
                    "rotation": p["rotation"],
                }
                for p in file_entry["pages"]
            ],
        })

    return jsonify(added_files=added_files)


@app.route("/api/state", methods=["GET"])
def get_state():
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    sess = session_store.get_session(sid)
    if sess is None:
        return jsonify(files=[])

    result = []
    for f in sess["files"]:
        result.append({
            "file_id": f["file_id"],
            "original_name": f["original_name"],
            "pages": [
                {"page_id": p["page_id"], "source_page_idx": p["source_page_idx"], "rotation": p["rotation"]}
                for p in f["pages"]
            ],
        })
    return jsonify(files=result)


@app.route("/api/state", methods=["PUT"])
def put_state():
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    data = request.get_json(force=True)
    if not data or "files" not in data:
        return jsonify(error="Invalid payload"), 400

    try:
        session_store.apply_arrangement(sid, data["files"])
    except KeyError as e:
        return jsonify(error=str(e)), 404

    return jsonify(ok=True)


@app.route("/api/thumbnail/<page_id>")
def thumbnail(page_id: str):
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    file_entry, page_entry = session_store.find_page(sid, page_id)
    if page_entry is None:
        return jsonify(error="Page not found"), 404

    width = int(request.args.get("size", 220))
    try:
        png = pdf_engine.render_thumbnail(
            page_entry["source_path"],
            page_entry["source_page_idx"],
            page_entry["rotation"],
            width_px=width,
        )
    except Exception as e:
        return jsonify(error=str(e)), 500

    return Response(png, mimetype="image/png")


@app.route("/api/rotate/<page_id>", methods=["POST"])
def rotate_page(page_id: str):
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    data = request.get_json(force=True) or {}
    direction = data.get("direction", "cw")

    _, page_entry = session_store.find_page(sid, page_id)
    if page_entry is None:
        return jsonify(error="Page not found"), 404

    delta = 90 if direction == "cw" else -90
    page_entry["rotation"] = (page_entry["rotation"] + delta) % 360

    return jsonify(page_id=page_id, rotation=page_entry["rotation"])


@app.route("/api/download")
def download():
    sid = _session_id()
    if not sid:
        return jsonify(error="Missing X-Session-ID header"), 400

    sess = session_store.get_session(sid)
    if sess is None:
        return jsonify(error="Session not found"), 404

    page_specs = []
    for f in sess["files"]:
        for p in f["pages"]:
            page_specs.append({
                "source_path": p["source_path"],
                "page_idx": p["source_page_idx"],
                "rotation": p["rotation"],
            })

    if not page_specs:
        return jsonify(error="No pages to export"), 400

    try:
        pdf_bytes = pdf_engine.assemble_pdf(page_specs)
    except Exception as e:
        return jsonify(error=str(e)), 500

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=edited.pdf"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
