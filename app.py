import os
import threading
import webbrowser

import config
from db.database import init_db, backup_if_needed
from webapp import create_app

app = create_app()


def _open_browser():
    webbrowser.open(f"http://127.0.0.1:{config.FLASK_PORT}/")


if __name__ == "__main__":
    init_db()
    backup_if_needed()

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.0, _open_browser).start()

    app.run(host="127.0.0.1", port=config.FLASK_PORT, debug=False)
