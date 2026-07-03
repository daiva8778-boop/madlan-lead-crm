"""
Modal deployment for the Madlan Lead CRM dashboard.

One-time setup (run these yourself from a terminal in this folder):
    pip install modal
    modal setup                      # opens a browser to link your Modal account
    modal secret create madlan-crm-secrets FIRECRAWL_API_KEY=... DASHBOARD_PASSWORD=... SECRET_KEY=...

Deploy (redeploy any time you push code changes):
    modal deploy modal_app.py

Modal prints a public https://....modal.run URL after deploying — that's your
dashboard's cloud address. The SQLite database lives on a Modal Volume
(madlan-crm-data), so it persists across redeploys instead of resetting.
"""
import os
import sys

import modal

app = modal.App("madlan-lead-crm")

IGNORE_PATTERNS = [
    ".git", ".git/**", ".claude", ".claude/**",
    "data", "data/**", "db/backups", "db/backups/**",
    "__pycache__", "**/__pycache__/**", "*.pyc",
    "autoreply/node_modules", "autoreply/node_modules/**",
    "tests", "tests/**",
    ".env",
]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/app", copy=True, ignore=IGNORE_PATTERNS)
)

volume = modal.Volume.from_name("madlan-crm-data", create_if_missing=True)
secrets = [modal.Secret.from_name("madlan-crm-secrets")]


@app.function(
    image=image,
    volumes={"/data": volume},
    secrets=secrets,
    min_containers=1,  # keep one instance warm so live scrape progress (in-memory) isn't lost between requests
    timeout=600,        # a "Scrape Next 50" run can take a few minutes
)
@modal.concurrent(max_inputs=20)
@modal.wsgi_app()
def flask_app():
    os.environ["DATA_DIR"] = "/data"
    os.environ["RAILWAY_ENVIRONMENT"] = "modal"  # reuses the same "IS_CLOUD" gate (no browser auto-open, binds 0.0.0.0)
    sys.path.insert(0, "/app")
    os.chdir("/app")
    from app import app as flask_application
    return flask_application
