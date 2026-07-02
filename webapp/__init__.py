from flask import Flask

import config


def create_app():
    app = Flask(
        __name__,
        template_folder=str(config.BASE_DIR / "templates"),
        static_folder=str(config.BASE_DIR / "static"),
    )

    from webapp import routes_pages, routes_scrape, routes_agencies, routes_export, routes_templates, routes_autoreply
    app.register_blueprint(routes_pages.bp)
    app.register_blueprint(routes_scrape.bp)
    app.register_blueprint(routes_agencies.bp)
    app.register_blueprint(routes_export.bp)
    app.register_blueprint(routes_templates.bp)
    app.register_blueprint(routes_autoreply.bp)

    return app
