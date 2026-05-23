#!/usr/bin/env python3
"""
Repeatable, idempotent migration: repoint template `file_path` rows to in-repo masters.

Why: legacy DB rows for the built-in styles point at absolute paths inside the OLD
repo (`ppt-agent-poc/...`). That makes runtime generation depend on another repo
existing on disk. This script rewrites any t5/t6 style row whose `file_path` does not
already resolve inside THIS repo to the in-repo master under `templates_storage/`.

- Does NOT redesign the schema.
- Does NOT delete duplicate rows.
- Safe to run multiple times (only updates rows that need it).

Usage:
    .venv_huang/bin/python scripts/migrate_template_paths.py        # apply
    .venv_huang/bin/python scripts/migrate_template_paths.py --dry  # preview only
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.db import get_connection  # noqa: E402

# style master basename -> in-repo master path
MASTERS = {
    "t5.pptx": BASE_DIR / "templates_storage" / "t5.pptx",
    "t6.pptx": BASE_DIR / "templates_storage" / "t6.pptx",
}


def desired_path(file_path: str) -> str | None:
    """Return the in-repo target path if this row should be repointed, else None."""
    if not file_path:
        return None
    base = file_path.replace("\\", "/").rstrip("/").split("/")[-1]
    master = MASTERS.get(base)
    if not master:
        return None  # not a t5/t6 row
    target = str(master)
    # Already correct?
    if Path(file_path) == master:
        return None
    return target


def main(dry: bool = False) -> int:
    # sanity: masters must exist before we point rows at them
    missing = [str(p) for p in MASTERS.values() if not p.exists()]
    if missing:
        print("ERROR: in-repo master(s) missing, aborting:")
        for m in missing:
            print("  -", m)
        return 2

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, file_path FROM templates")
    rows = cur.fetchall()

    updates = []
    for r in rows:
        tgt = desired_path(r.get("file_path") or "")
        if tgt:
            updates.append((r["id"], r["name"], r["file_path"], tgt))

    if not updates:
        print("Nothing to migrate: all t5/t6 rows already point to in-repo masters.")
        cur.close(); conn.close()
        return 0

    print(f"{'[DRY] ' if dry else ''}Repointing {len(updates)} row(s):")
    for tid, name, old, new in updates:
        print(f"  id={tid} name={name!r}\n    old: {old}\n    new: {new}")

    if not dry:
        wcur = conn.cursor()
        for tid, _name, _old, new in updates:
            wcur.execute("UPDATE templates SET file_path = %s WHERE id = %s", (new, tid))
        conn.commit()
        wcur.close()
        print(f"Applied {len(updates)} update(s).")

    cur.close(); conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(dry="--dry" in sys.argv))
