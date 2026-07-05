import threading

from flask import Blueprint, jsonify, request

import config
from db.database import get_db
from scraper.pipeline import scrape_next_mobile_leads
from webapp import scrape_state

bp = Blueprint("scrape", __name__, url_prefix="/api/scrape")


def _run_scrape(city):
    def cb(new_saved, target, rejected_count, credits_used):
        scrape_state.update_progress(new_saved, target, rejected_count, credits_used)

    try:
        summary = scrape_next_mobile_leads(city, progress_callback=cb)
        scrape_state.finish(summary={
            "new_saved": summary.new_saved,
            "rejected_count": summary.rejected_count,
            "credits_used": summary.credits_used,
            "failed_count": summary.failed_count,
            "city_exhausted": summary.city_exhausted,
        })
    except Exception as e:
        scrape_state.finish(error=str(e))


@bp.route("/start", methods=["POST"])
def start():
    body = request.get_json(force=True) or {}
    city = body.get("city")
    if city not in config.CITIES:
        return jsonify({"error": "invalid city"}), 400

    started = scrape_state.try_start(city, config.SCRAPE_BATCH_TARGET)
    if not started:
        return jsonify({"error": "already_running"}), 409

    t = threading.Thread(target=_run_scrape, args=(city,), daemon=True)
    t.start()
    return jsonify({"ok": True})


@bp.route("/progress", methods=["GET"])
def progress():
    return jsonify(scrape_state.get_state())


@bp.route("/failed_urls", methods=["GET"])
def failed_urls():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM failed_urls ORDER BY attempted_at DESC LIMIT 200"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()
