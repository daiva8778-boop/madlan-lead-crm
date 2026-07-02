import threading

_lock = threading.Lock()
_state = {
    "running": False,
    "city": None,
    "scraped": 0,
    "target": 0,
    "no_website_count": 0,
    "credits_used": 0,
    "done": False,
    "summary": None,
    "error": None,
}


def try_start(city, target):
    with _lock:
        if _state["running"]:
            return False
        _state.update(
            running=True, city=city, scraped=0, target=target,
            no_website_count=0, credits_used=0, done=False, summary=None, error=None,
        )
        return True


def update_progress(scraped, target, no_website_count, credits_used):
    with _lock:
        if not _state["running"]:
            return
        _state.update(
            scraped=scraped, target=target,
            no_website_count=no_website_count, credits_used=credits_used,
        )


def finish(summary=None, error=None):
    with _lock:
        _state["running"] = False
        _state["done"] = True
        _state["summary"] = summary
        _state["error"] = error


def get_state():
    with _lock:
        return dict(_state)
