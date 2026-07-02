import shutil
import sqlite3
from datetime import date, datetime

import config


def get_db():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    try:
        with open(config.SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def backup_if_needed():
    """Timestamped backup copy of the DB, once per calendar day, run on app start."""
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    if not config.DB_PATH.exists():
        return None

    conn = get_db()
    try:
        row = conn.execute("SELECT last_backup_date FROM settings WHERE id=1").fetchone()
        today = date.today().isoformat()
        if row and row["last_backup_date"] == today:
            return None

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = config.BACKUPS_DIR / f"madlan_crm_{stamp}.db"
        conn.execute("VACUUM INTO ?", (str(dest),))
        conn.execute(
            "UPDATE settings SET last_backup_date=?, updated_at=? WHERE id=1",
            (today, now_iso()),
        )
        conn.commit()
        return dest
    finally:
        conn.close()
