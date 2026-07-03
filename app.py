import os
import threading
import webbrowser

import config
from db.database import init_db, backup_if_needed
from webapp import create_app

app = create_app()


def _open_browser():
    webbrowser.open(f"http://127.0.0.1:{config.FLASK_PORT}/")


init_db()
backup_if_needed()

if __name__ == "__main__":
    if not config.IS_CLOUD and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.0, _open_browser).start()

    # 127.0.0.1 for local-only use; 0.0.0.0 in the cloud so the platform's
    # load balancer/proxy can actually reach the app.
    host = "0.0.0.0" if config.IS_CLOUD else "127.0.0.1"
    app.run(host=host, port=config.FLASK_PORT, debug=False)
