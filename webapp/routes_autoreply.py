from flask import Blueprint, jsonify, request

from db.database import get_db, now_iso

bp = Blueprint("autoreply", __name__, url_prefix="/api/settings/autoreply")


@bp.route("", methods=["GET"])
def get_autoreply():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT autoreply_enabled, autoreply_connection_status FROM settings WHERE id=1"
        ).fetchone()
        return jsonify(dict(row))
    finally:
        conn.close()


@bp.route("/toggle", methods=["POST"])
def toggle_autoreply():
    body = request.get_json(force=True) or {}
    enabled = 1 if body.get("enabled") else 0
    conn = get_db()
    try:
        conn.execute(
            "UPDATE settings SET autoreply_enabled=?, updated_at=? WHERE id=1",
            (enabled, now_iso()),
        )
        conn.commit()
        return jsonify({"ok": True, "enabled": bool(enabled)})
    finally:
        conn.close()
