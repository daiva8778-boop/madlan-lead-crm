from datetime import timedelta

from flask import Flask, redirect, request, session, url_for

import config


def create_app():
    app = Flask(
        __name__,
        template_folder=str(config.BASE_DIR / "templates"),
        static_folder=str(config.BASE_DIR / "static"),
    )
    app.secret_key = config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(days=30)

    from webapp import (
        routes_pages, routes_scrape, routes_agencies, routes_export,
        routes_templates, routes_autoreply, routes_auth, routes_mobile,
    )
    app.register_blueprint(routes_pages.bp)
    app.register_blueprint(routes_scrape.bp)
    app.register_blueprint(routes_agencies.bp)
    app.register_blueprint(routes_export.bp)
    app.register_blueprint(routes_templates.bp)
    app.register_blueprint(routes_autoreply.bp)
    app.register_blueprint(routes_auth.bp)
    app.register_blueprint(routes_mobile.bp)

    @app.before_request
    def require_login():
        # No password configured (e.g. plain local use) -> auth is a no-op,
        # matching the original local-only design.
        if not config.DASHBOARD_PASSWORD:
            return
        if request.endpoint in ("auth.login", "static"):
            return
        if not session.get("authenticated"):
            return redirect(url_for("auth.login"))

    return app
