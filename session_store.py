import time
import uuid

SESSIONS = {}


def create_session(upload_dir: str) -> str:
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {
        "created_at": time.time(),
        "upload_dir": upload_dir,
        "files": [],
    }
    return sid


def create_session_with_id(sid: str, upload_dir: str):
    SESSIONS[sid] = {
        "created_at": time.time(),
        "upload_dir": upload_dir,
        "files": [],
    }


def get_session(sid: str) -> dict | None:
    return SESSIONS.get(sid)


def require_session(sid: str) -> dict:
    sess = SESSIONS.get(sid)
    if sess is None:
        raise KeyError(f"Session {sid!r} not found")
    return sess


def add_file(sid: str, file_id: str, original_name: str, source_path: str, page_count: int):
    sess = require_session(sid)
    pages = [
        {
            "page_id": str(uuid.uuid4()),
            "source_file_id": file_id,
            "source_page_idx": i,
            "source_path": source_path,  # stored per-page so moves between groups work
            "rotation": 0,
        }
        for i in range(page_count)
    ]
    file_entry = {
        "file_id": file_id,
        "original_name": original_name,
        "source_path": source_path,
        "pages": pages,
    }
    sess["files"].append(file_entry)
    return file_entry


def find_page(sid: str, page_id: str) -> tuple[dict, dict] | tuple[None, None]:
    """Return (file_entry, page_entry) or (None, None)."""
    sess = SESSIONS.get(sid)
    if not sess:
        return None, None
    for f in sess["files"]:
        for p in f["pages"]:
            if p["page_id"] == page_id:
                return f, p
    return None, None


def apply_arrangement(sid: str, arrangement: list[dict]):
    """
    Replace session file/page ordering from the client's arrangement payload.

    arrangement = [
        {"file_id": "...", "pages": [{"page_id": "...", "rotation": 90}, ...]},
        ...
    ]
    """
    sess = require_session(sid)

    # Build lookup maps from existing state
    file_map = {f["file_id"]: f for f in sess["files"]}
    page_map: dict[str, dict] = {}
    for f in sess["files"]:
        for p in f["pages"]:
            page_map[p["page_id"]] = p

    new_files = []
    for file_item in arrangement:
        fid = file_item["file_id"]
        if fid not in file_map:
            continue
        orig_file = file_map[fid]
        new_pages = []
        for page_item in file_item.get("pages", []):
            pid = page_item["page_id"]
            if pid not in page_map:
                continue
            orig_page = page_map[pid]
            new_pages.append({
                "page_id": pid,
                "source_file_id": orig_page["source_file_id"],
                "source_page_idx": orig_page["source_page_idx"],
                "source_path": orig_page["source_path"],
                "rotation": page_item.get("rotation", orig_page["rotation"]),
            })
        new_files.append({
            "file_id": fid,
            "original_name": orig_file["original_name"],
            "source_path": orig_file["source_path"],
            "pages": new_pages,
        })

    sess["files"] = new_files


def stale_sessions(max_age_seconds: float = 7200) -> list[str]:
    now = time.time()
    return [sid for sid, s in SESSIONS.items() if now - s["created_at"] > max_age_seconds]


def delete_session(sid: str) -> str | None:
    sess = SESSIONS.pop(sid, None)
    return sess["upload_dir"] if sess else None
