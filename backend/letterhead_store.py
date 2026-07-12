"""Letterhead store — manages uploaded letterhead/logo images and active selection per type."""

import json
import uuid
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).parent.parent
_LH_DIR = _BASE / "static" / "letterheads"
_META_FILE = _LH_DIR / "metadata.json"

_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
TYPES = ("letterhead", "logo")


def _ensure_dir():
    _LH_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    _ensure_dir()
    if _META_FILE.exists():
        try:
            data = json.loads(_META_FILE.read_text(encoding="utf-8"))
            # Migrate old format (single active_id → per-type active)
            if "active_id" in data and "active_letterhead_id" not in data:
                data["active_letterhead_id"] = data.pop("active_id")
                data.setdefault("active_logo_id", None)
                # Tag all existing entries as letterhead if no type set
                for lh in data.get("letterheads", []):
                    lh.setdefault("type", "letterhead")
                _save(data)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"letterheads": [], "active_letterhead_id": None, "active_logo_id": None}


def _save(data: dict):
    _ensure_dir()
    _META_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _active_key(lh_type: str) -> str:
    return "active_logo_id" if lh_type == "logo" else "active_letterhead_id"


def list_letterheads(lh_type: str | None = None) -> list[dict]:
    items = _load()["letterheads"]
    if lh_type:
        items = [lh for lh in items if lh.get("type", "letterhead") == lh_type]
    return items


def get_active_by_type(lh_type: str) -> dict | None:
    data = _load()
    active_id = data.get(_active_key(lh_type))
    if not active_id:
        return None
    for lh in data["letterheads"]:
        if lh["id"] == active_id and lh.get("type", "letterhead") == lh_type:
            if (_LH_DIR / lh["filename"]).exists():
                return lh
    return None


def get_active_path_by_type(lh_type: str) -> Path | None:
    lh = get_active_by_type(lh_type)
    if not lh:
        return None
    p = _LH_DIR / lh["filename"]
    return p if p.exists() else None


def add_letterhead(file_bytes: bytes, original_name: str, label: str = "", lh_type: str = "letterhead") -> dict:
    _ensure_dir()
    if lh_type not in TYPES:
        lh_type = "letterhead"
    ext = Path(original_name).suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError(f"Format fail tidak disokong: {ext}")

    lh_id = "lh_" + uuid.uuid4().hex[:8]
    filename = lh_id + ext
    (_LH_DIR / filename).write_bytes(file_bytes)

    entry = {
        "id": lh_id,
        "name": label or Path(original_name).stem,
        "filename": filename,
        "original_name": original_name,
        "type": lh_type,
        "uploaded": datetime.now().isoformat(),
    }

    data = _load()
    data["letterheads"].append(entry)
    # Auto-activate if first of this type
    if not data.get(_active_key(lh_type)):
        data[_active_key(lh_type)] = lh_id
    _save(data)
    return entry


def set_active(lh_id: str, lh_type: str = "letterhead") -> bool:
    data = _load()
    ids = {lh["id"] for lh in data["letterheads"] if lh.get("type", "letterhead") == lh_type}
    if lh_id not in ids:
        return False
    data[_active_key(lh_type)] = lh_id
    _save(data)
    return True


def delete_letterhead(lh_id: str) -> bool:
    data = _load()
    entry = next((lh for lh in data["letterheads"] if lh["id"] == lh_id), None)
    if not entry:
        return False

    p = _LH_DIR / entry["filename"]
    if p.exists():
        p.unlink()

    lh_type = entry.get("type", "letterhead")
    data["letterheads"] = [lh for lh in data["letterheads"] if lh["id"] != lh_id]

    # Auto-select next of same type if deleted was active
    if data.get(_active_key(lh_type)) == lh_id:
        remaining = [lh for lh in data["letterheads"] if lh.get("type", "letterhead") == lh_type]
        data[_active_key(lh_type)] = remaining[0]["id"] if remaining else None

    _save(data)
    return True


def update_name(lh_id: str, name: str) -> bool:
    data = _load()
    for lh in data["letterheads"]:
        if lh["id"] == lh_id:
            lh["name"] = name
            _save(data)
            return True
    return False
