from flask import Blueprint, redirect, render_template, request, session, url_for

import config

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == config.DASHBOARD_PASSWORD:
            session["authenticated"] = True
            session.permanent = True
            return redirect(url_for("pages.index"))
        error = "Wrong password."
    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
