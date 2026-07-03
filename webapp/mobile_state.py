import threading

_lock = threading.Lock()
_state = {
    "running": False,
    "checked": 0,
    "target": 0,
    "found": 0,
    "done": False,
    "summary": None,
    "error": None,
}


def try_start():
    with _lock:
        if _state["running"]:
            return False
        _state.update(
            running=True, checked=0, target=0, found=0,
            done=False, summary=None, error=None,
        )
        return True


def update_progress(checked, target, found):
    with _lock:
        if not _state["running"]:
            return
        _state.update(checked=checked, target=target, found=found)


def finish(summary=None, error=None):
    with _lock:
        _state["running"] = False
        _state["done"] = True
        _state["summary"] = summary
        _state["error"] = error


def get_state():
    with _lock:
        return dict(_state)
