from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
import random

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("E-Mail oder Passwort ist falsch.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("chat.dashboard"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Diese E-Mail ist schon registriert.", "danger")
            return redirect(url_for("auth.register"))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Registrierung erfolgreich. Bitte einloggen.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("E-Mail nicht gefunden.", "danger")
            return redirect(url_for("auth.forgot_password"))

        code = str(random.randint(100000, 999999))
        session["reset_email"] = email
        session["reset_code"] = code

        print("CODE:", code)

        flash("Code wurde erstellt. Schau im Terminal/Render-Log.", "success")
        return redirect(url_for("auth.verify_code"))

    return render_template("forgot_password.html")


@auth_bp.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        code = request.form.get("code")

        if code == session.get("reset_code"):
            return redirect(url_for("auth.reset_password"))

        flash("Falscher Code.", "danger")
        return redirect(url_for("auth.verify_code"))

    return render_template("verify_code.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")

    if not email:
        flash("Bitte zuerst E-Mail eingeben.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        pw = request.form.get("password")
        pw2 = request.form.get("password_confirm")

        if pw != pw2:
            flash("Passwörter stimmen nicht überein.", "danger")
            return redirect(url_for("auth.reset_password"))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Benutzer nicht gefunden.", "danger")
            return redirect(url_for("auth.forgot_password"))

        user.set_password(pw)
        db.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_code", None)

        flash("Passwort wurde geändert.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")