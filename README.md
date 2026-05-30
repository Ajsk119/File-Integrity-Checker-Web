# File Integrity Checker

A lightweight web tool to detect whether files have been modified, deleted, or added — by comparing cryptographic hashes against a saved baseline snapshot.

Built with **Python + Flask**, deployable to Render as a Web Service.

---

## What it does

1. **Baseline** — Upload a set of files. The server hashes each one and stores the fingerprints in memory.
2. **Verify** — Re-upload the same files later. The tool compares new hashes against the baseline and reports exactly what changed.
3. **Results** — Files are classified as Unchanged, Modified, Missing, or New, with truncated hash diffs shown for anything that changed.

No files are written to disk. Everything lives in memory and is cleared when the session resets or the tab closes.

> ⚠️ **Note:** Baselines are in-memory only. If the server restarts (e.g. Render free tier sleeps after inactivity), saved baselines are lost. This tool is best suited for same-session use.

---

## Algorithms supported

| Algorithm | Output length | Notes |
|-----------|--------------|-------|
| SHA-256   | 64 chars     | Default — fast, secure, no known vulnerabilities |
| SHA-512   | 128 chars    | Extra assurance, slightly slower |
| SHA-1     | 40 chars     | Legacy use only |
| MD5       | 32 chars     | Avoid for security-sensitive work (collision attacks) |

---

## Project structure

```
fic_public/
├── app.py               # Flask app — routes, hashing logic, in-memory store
├── Procfile             # Gunicorn entry point for Render
├── requirements.txt     # flask + gunicorn
└── templates/
    └── index.html       # Single-page UI (HTML + CSS + vanilla JS)
```

---

## Running locally

```bash
# 1. Unzip and enter the project
cd fic_public

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the dev server
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Deploying to Render

1. Push the contents of `fic_public/` to a **GitHub repository** (make sure `app.py` is at the root, not inside a subfolder).
2. Go to [Render](https://render.com) → **New Web Service** → connect your repo.
3. Set the following:

| Setting | Value |
|---------|-------|
| **Environment** | Python |
| **Build command** | `pip install -r requirements.txt` |
| **Start command** | *(leave blank — Render uses the Procfile automatically)* |

4. Under **Environment Variables**, add:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | any long random string |

5. Click **Deploy**. That's it.

The `Procfile` handles the rest:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60
```

---

## API reference

All endpoints except file uploads use JSON. File uploads use `multipart/form-data`.

### `POST /api/baseline`

Save a baseline snapshot for a session.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Client-generated ID (persists across steps) |
| `algo` | string | `sha256`, `sha512`, `sha1`, or `md5` |
| `files` | files | One or more files (multipart) |

**Response**
```json
{
  "ok": true,
  "count": 3,
  "algo": "SHA256",
  "created_at": "2026-05-30T18:00:00Z",
  "files": ["report.pdf", "config.json", "data.csv"]
}
```

---

### `POST /api/verify`

Compare uploaded files against the saved baseline.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Same ID used in `/api/baseline` |
| `files` | files | Files to verify (multipart) |

**Response**
```json
{
  "status": "COMPROMISED",
  "algo": "SHA256",
  "verified_at": "2026-05-30T18:05:00Z",
  "unchanged": 2,
  "modified": 1,
  "missing": 0,
  "new_files": 0,
  "modified_list": [
    {
      "name": "config.json",
      "expected": "a3f1c9d823b0e4...",
      "actual":   "99de10ca71f832...",
      "old_size": 1024,
      "new_size": 1089
    }
  ],
  "missing_list": [],
  "new_files_list": []
}
```

`status` is `"CLEAN"` when nothing was modified or missing, `"COMPROMISED"` otherwise.

---

### `POST /api/reset`

Clear the baseline for a session.

```json
{ "session_id": "s_abc123" }
```

---

## Limitations

- **In-memory only** — no database, baselines don't survive a server restart.
- **No authentication** — session IDs are client-generated; don't use this for sensitive files.
- **Folder support** — zip the folder first, upload the archive, use the same zip for both steps.
- **Not for high-security use** — convenience tool only, not a hardened integrity system.

---

## Tech stack

- [Flask 3.0](https://flask.palletsprojects.com/) — Python web framework
- [Gunicorn 22](https://gunicorn.org/) — WSGI production server
- Vanilla HTML / CSS / JS — no frontend build step
