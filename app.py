import os
import hashlib
import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fic-render-2026")

# In-memory store: session_id -> baseline dict
BASELINES = {}

ALGOS = {"md5", "sha1", "sha256", "sha512"}


def hash_bytes(data: bytes, algo: str) -> str:
    h = hashlib.new(algo)
    h.update(data)
    return h.hexdigest()


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


@app.route("/", methods=["GET", "HEAD"])
def index():
    return render_template("index.html")


@app.route("/api/baseline", methods=["POST"])
def api_baseline():
    algo       = request.form.get("algo", "sha256").lower()
    session_id = request.form.get("session_id", "")
    files      = request.files.getlist("files")

    if algo not in ALGOS:
        return jsonify({"error": "Invalid algorithm."}), 400
    if not session_id:
        return jsonify({"error": "Missing session ID."}), 400
    if not files or files[0].filename == "":
        return jsonify({"error": "No files uploaded."}), 400

    baseline = {
        "created_at": now_iso(),
        "algorithm":  algo,
        "files":      {},
    }

    for f in files:
        data = f.read()
        baseline["files"][f.filename] = {
            "hash": hash_bytes(data, algo),
            "size": len(data),
        }

    BASELINES[session_id] = baseline

    return jsonify({
        "ok":         True,
        "count":      len(baseline["files"]),
        "algo":       algo.upper(),
        "created_at": baseline["created_at"],
        "files":      list(baseline["files"].keys()),
    })


@app.route("/api/verify", methods=["POST"])
def api_verify():
    session_id = request.form.get("session_id", "")
    files      = request.files.getlist("files")

    baseline = BASELINES.get(session_id)
    if not baseline:
        return jsonify({"error": "No baseline found. Please create a baseline first."}), 400
    if not files or files[0].filename == "":
        return jsonify({"error": "No files uploaded."}), 400

    algo    = baseline["algorithm"]
    saved   = baseline["files"]

    uploaded = {}
    for f in files:
        data = f.read()
        uploaded[f.filename] = {"hash": hash_bytes(data, algo), "size": len(data)}

    unchanged = []
    modified  = []
    missing   = []
    new_files = []

    for name, record in saved.items():
        if name not in uploaded:
            missing.append(name)
        elif uploaded[name]["hash"] != record["hash"]:
            modified.append({
                "name":     name,
                "expected": record["hash"][:20] + "...",
                "actual":   uploaded[name]["hash"][:20] + "...",
                "old_size": record["size"],
                "new_size": uploaded[name]["size"],
            })
        else:
            unchanged.append(name)

    for name in uploaded:
        if name not in saved:
            new_files.append(name)

    status = "COMPROMISED" if (modified or missing) else "CLEAN"

    return jsonify({
        "status":         status,
        "algo":           algo.upper(),
        "verified_at":    now_iso(),
        "unchanged":      len(unchanged),
        "modified":       len(modified),
        "missing":        len(missing),
        "new_files":      len(new_files),
        "modified_list":  modified,
        "missing_list":   missing,
        "new_files_list": new_files,
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id", "")
        BASELINES.pop(session_id, None)
    except Exception:
        pass
    return jsonify({"ok": True})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
