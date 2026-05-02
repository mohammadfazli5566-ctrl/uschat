from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, db

import smtplib
import random
from email.message import EmailMessage

auth_bp = Blueprint("auth", __name__)


def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config.get("MAIL_DEFAULT_SENDER")
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(
                current_app.config.get("MAIL_USERNAME"),
                current_app.config.get("MAIL_PASSWORD")
            )
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("Email Fehler:", e)
        return False


@auth_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Diese E-Mail ist bereits registriert.")
            return redirect(url_for("auth.register"))

        code = str(random.randint(100000, 999999))

        session["pending_email"] = email
        session["pending_username"] = username
        session["pending_password"] = generate_password_hash(password)
        session["verify_code"] = code

        email_sent = send_email(
            email,
            "Dein UsChatSecure Bestätigungscode",
            f"Dein Bestätigungscode lautet: {code}"
        )

        if not email_sent:
            flash("E-Mail konnte nicht gesendet werden. Bitte später erneut versuchen.")
            return redirect(url_for("auth.register"))

        flash("Wir haben dir einen Bestätigungscode per E-Mail gesendet.")
        return redirect(url_for("auth.verify_code"))

    return render_template("register.html")


@auth_bp.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        entered_code = request.form.get("code")

        if entered_code == session.get("verify_code"):
            new_user = User(
                email=session.get("pending_email"),
                username=session.get("pending_username"),
                password=session.get("pending_password")
            )

            db.session.add(new_user)
            db.session.commit()

            session.pop("pending_email", None)
            session.pop("pending_username", None)
            session.pop("pending_password", None)
            session.pop("verify_code", None)

            flash("Registrierung erfolgreich. Du kannst dich jetzt einloggen.")
            return redirect(url_for("auth.login"))

        flash("Der Code ist falsch.")
        return redirect(url_for("auth.verify_code"))

    return render_template("verify_code.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("auth.dashboard"))

        flash("Login fehlgeschlagen.")

    return render_template("login.html")


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            send_email(email, "Passwort Reset", "Du hast einen Reset angefordert.")
            flash("E-Mail gesendet.")

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")