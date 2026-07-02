from flask import Blueprint, render_template

import config

bp = Blueprint("pages", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", cities=config.CITIES)
