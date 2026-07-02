from flask import Blueprint, jsonify

from db.database import get_db

bp = Blueprint("templates_stats", __name__, url_prefix="/api/templates")

REPLIED_OR_BETTER = ("REPLIED", "MEETING", "CLIENT")


@bp.route("/stats", methods=["GET"])
def stats():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT ml.template_version, ml.agency_id, a.status
               FROM message_log ml
               JOIN agencies a ON a.id = ml.agency_id
               WHERE ml.voided=0 AND ml.template_key != 'auto_reply'"""
        ).fetchall()
    finally:
        conn.close()

    by_version = {}
    for r in rows:
        v = by_version.setdefault(r["template_version"], {"sent": 0, "replied_or_better": set()})
        v["sent"] += 1
        if r["status"] in REPLIED_OR_BETTER:
            v["replied_or_better"].add(r["agency_id"])

    result = []
    for version, data in by_version.items():
        sent = data["sent"]
        replied = len(data["replied_or_better"])
        result.append({
            "template_version": version,
            "sent": sent,
            "replied_or_better": replied,
            "reply_rate": round(replied / sent * 100, 1) if sent else 0,
        })
    result.sort(key=lambda x: x["sent"], reverse=True)
    return jsonify(result)
