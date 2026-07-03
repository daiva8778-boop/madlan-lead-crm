from flask import Blueprint, jsonify, request

import config
from db.database import get_db, now_iso
from messaging import render_template, choose_template_key, build_wa_url
from scraper.phone_utils import normalize_il_phone
from webapp.agency_view import serialize_agency, is_follow_up_due, STATUSES

bp = Blueprint("agencies", __name__, url_prefix="/api/agencies")


def _apply_filters(rows, filter_key, city):
    def keep(row):
        if city and city != "all" and row["city"] != city:
            return False
        if filter_key == "all":
            return True
        if row["status"] == "DO_NOT_CONTACT":
            return False  # excluded from every outreach filter, per spec
        if filter_key == "new":
            return row["status"] == "NEW"
        if filter_key == "sent":
            return row["status"] == "SENT" and not is_follow_up_due(row)
        if filter_key == "followup_due":
            return row["status"] == "SENT" and is_follow_up_due(row)
        if filter_key == "replied":
            return row["status"] == "REPLIED"
        if filter_key == "no_site":
            return not row["has_website"]
        if filter_key == "mobile":
            return row["phone_source"] == "direct_mobile"
        return True

    return [r for r in rows if keep(r)]


@bp.route("", methods=["GET"])
def list_agencies():
    filter_key = request.args.get("filter", "all")
    city = request.args.get("city", "all")
    sort = request.args.get("sort", "newest")

    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM agencies").fetchall()
    finally:
        conn.close()

    filtered = _apply_filters(rows, filter_key, city)

    if sort == "deals":
        filtered.sort(key=lambda r: (r["deals_count"] or 0), reverse=True)
    else:
        filtered.sort(key=lambda r: r["scraped_at"] or "", reverse=True)

    city_scoped = [r for r in rows if city == "all" or r["city"] == city]
    counters = {
        "total": len(city_scoped),
        "new": sum(1 for r in city_scoped if r["status"] == "NEW"),
        "sent": sum(1 for r in city_scoped if r["status"] == "SENT"),
        "replied": sum(1 for r in city_scoped if r["status"] == "REPLIED"),
    }

    return jsonify({
        "agencies": [serialize_agency(r) for r in filtered],
        "counters": counters,
        "cities": [{"key": k, "label": v["label"]} for k, v in config.CITIES.items()],
    })


@bp.route("/<int:agency_id>/status", methods=["POST"])
def update_status(agency_id):
    body = request.get_json(force=True) or {}
    new_status = body.get("status")
    confirm = body.get("confirm", False)
    if new_status not in STATUSES:
        return jsonify({"error": "invalid status"}), 400

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        if row["status"] == "DO_NOT_CONTACT" and new_status != "DO_NOT_CONTACT" and not confirm:
            return jsonify({"error": "protected", "message": "This agency is DO NOT CONTACT. Pass confirm=true to override."}), 409

        ts = now_iso()
        extra_sets, extra_params = "", []
        if new_status == "REPLIED" and row["status"] != "REPLIED":
            extra_sets = ", replied_at=?"
            extra_params = [ts]

        conn.execute(
            f"UPDATE agencies SET status=?, updated_at=?{extra_sets} WHERE id=?",
            [new_status, ts, *extra_params, agency_id],
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        return jsonify(serialize_agency(updated))
    finally:
        conn.close()


@bp.route("/<int:agency_id>/notes", methods=["POST"])
def update_notes(agency_id):
    body = request.get_json(force=True) or {}
    notes = body.get("notes", "")
    conn = get_db()
    try:
        conn.execute(
            "UPDATE agencies SET notes=?, updated_at=? WHERE id=?",
            (notes, now_iso(), agency_id),
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/<int:agency_id>/phone", methods=["POST"])
def update_phone(agency_id):
    """Manual fallback: paste in a phone number you looked up yourself (e.g. by
    opening the agency's Madlan profile link in your own browser) when the
    automated scraper couldn't get one."""
    body = request.get_json(force=True) or {}
    raw = (body.get("phone") or "").strip()

    conn = get_db()
    try:
        if not raw:
            conn.execute(
                "UPDATE agencies SET phone_used=NULL, phone_source='none', updated_at=? WHERE id=?",
                (now_iso(), agency_id),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
            return jsonify(serialize_agency(updated))

        normalized = normalize_il_phone(raw)
        if not normalized:
            return jsonify({"error": "invalid_phone", "message": "Could not recognize that as an Israeli phone number."}), 400

        conn.execute(
            "UPDATE agencies SET phone_used=?, phone_source='manual', updated_at=? WHERE id=?",
            (normalized, now_iso(), agency_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        return jsonify(serialize_agency(updated))
    finally:
        conn.close()


@bp.route("/<int:agency_id>/whatsapp_click", methods=["POST"])
def whatsapp_click(agency_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        if row["status"] == "DO_NOT_CONTACT":
            return jsonify({"error": "protected", "message": "This agency is DO NOT CONTACT."}), 409
        if not row["phone_used"]:
            return jsonify({"error": "no_phone", "message": "No usable phone number for this agency."}), 400

        follow_up = is_follow_up_due(row)
        template_key = choose_template_key(bool(row["has_website"]), follow_up)
        message_text, template_version = render_template(template_key, row["name"], row["deals_count"])
        wa_url = build_wa_url(row["phone_used"], message_text)

        ts = now_iso()
        conn.execute(
            """INSERT INTO message_log (agency_id, template_key, template_version, message_text,
               triggered_by, sent_at) VALUES (?,?,?,?, 'manual_click', ?)""",
            (agency_id, template_key, template_version, message_text, ts),
        )
        conn.execute(
            "UPDATE agencies SET status='SENT', sent_at=?, updated_at=? WHERE id=?",
            (ts, ts, agency_id),
        )
        conn.commit()
        return jsonify({"wa_url": wa_url, "template_key": template_key, "template_version": template_version})
    finally:
        conn.close()


@bp.route("/<int:agency_id>/whatsapp_toggle_sent", methods=["POST"])
def whatsapp_toggle_sent(agency_id):
    """Manual misclick correction — flips SENT on/off without deleting message_log history."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        if row["status"] == "DO_NOT_CONTACT":
            return jsonify({"error": "protected"}), 409

        ts = now_iso()
        if row["status"] == "SENT":
            conn.execute("UPDATE agencies SET status='NEW', sent_at=NULL, updated_at=? WHERE id=?", (ts, agency_id))
            conn.execute(
                """UPDATE message_log SET voided=1 WHERE id = (
                    SELECT id FROM message_log WHERE agency_id=? AND voided=0
                    ORDER BY sent_at DESC LIMIT 1)""",
                (agency_id,),
            )
        else:
            conn.execute("UPDATE agencies SET status='SENT', sent_at=?, updated_at=? WHERE id=?", (ts, ts, agency_id))
        conn.commit()
        updated = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        return jsonify(serialize_agency(updated))
    finally:
        conn.close()
