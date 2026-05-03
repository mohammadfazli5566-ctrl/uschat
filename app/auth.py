import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Diese E-Mail-Adresse wurde nicht gefunden.", "danger")
            return redirect(url_for("auth.forgot_password"))

        code = str(random.randint(100000, 999999))

        session["reset_email"] = email
        session["reset_code"] = code

        print("PASSWORT RESET CODE:", code)

        flash("Ein Bestätigungscode wurde erstellt. Schaue in die Konsole.", "success")
        return redirect(url_for("auth.verify_code"))

    return render_template("forgot_password.html")


@auth_bp.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        entered_code = request.form.get("code")
        saved_code = session.get("reset_code")

        if entered_code == saved_code:
            flash("Code richtig. Bitte neues Passwort eingeben.", "success")
            return redirect(url_for("auth.reset_password"))
        else:
            flash("Der Code ist falsch.", "danger")
            return redirect(url_for("auth.verify_code"))

    return render_template("verify_code.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")

    if not email:
        flash("Bitte zuerst deine E-Mail-Adresse eingeben.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if password != password_confirm:
            flash("Die Passwörter stimmen nicht überein.", "danger")
            return redirect(url_for("auth.reset_password"))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Benutzer nicht gefunden.", "danger")
            return redirect(url_for("auth.forgot_password"))

        user.password = generate_password_hash(password)
        db.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_code", None)

        flash("Passwort wurde erfolgreich geändert.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")