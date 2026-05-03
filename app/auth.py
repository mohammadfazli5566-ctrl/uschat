from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
import random

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def login():
    return render_template("login.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("E-Mail nicht gefunden", "danger")
            return redirect(url_for("auth.forgot_password"))

        code = str(random.randint(100000, 999999))

        session["reset_email"] = email
        session["reset_code"] = code

        print("CODE:", code)

        flash("Code wurde erstellt (siehe Terminal)", "success")
        return redirect(url_for("auth.verify_code"))

    return render_template("forgot_password.html")


@auth_bp.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        code = request.form.get("code")

        if code == session.get("reset_code"):
            return redirect(url_for("auth.reset_password"))
        else:
            flash("Falscher Code", "danger")

    return render_template("verify_code.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        pw = request.form.get("password")
        pw2 = request.form.get("password_confirm")

        if pw != pw2:
            flash("Passwörter stimmen nicht", "danger")
            return redirect(url_for("auth.reset_password"))

        user = User.query.filter_by(email=session.get("reset_email")).first()

        user.password = generate_password_hash(pw)
        db.session.commit()

        flash("Passwort geändert", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")