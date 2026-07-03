import threading

from flask import Blueprint, jsonify

from scraper.pipeline import rescrape_mobile_batch
from webapp import mobile_state

bp = Blueprint("mobile", __name__, url_prefix="/api/mobile")


def _run_mobile_rescrape():
    def cb(checked, target, found):
        mobile_state.update_progress(checked, target, found)

    try:
        summary = rescrape_mobile_batch(progress_callback=cb)
        mobile_state.finish(summary={"checked": summary.checked, "found": summary.found})
    except Exception as e:
        mobile_state.finish(error=str(e))


@bp.route("/start", methods=["POST"])
def start():
    started = mobile_state.try_start()
    if not started:
        return jsonify({"error": "already_running"}), 409

    t = threading.Thread(target=_run_mobile_rescrape, daemon=True)
    t.start()
    return jsonify({"ok": True})


@bp.route("/progress", methods=["GET"])
def progress():
    return jsonify(mobile_state.get_state())
