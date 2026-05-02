from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, db

import smtplib
from email.message import EmailMessage

auth_bp = Blueprint("auth", __name__)

# =========================
# EMAIL SENDEN (FIXED)
# =========================
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
    except Exception as e:
        print("Email Fehler:", e)


# =========================
# HOME
# =========================
@auth_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


# =========================
# REGISTER
# =========================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("E-Mail existiert bereits")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            email=email,
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        # OPTIONAL Email
        send_email(email, "Willkommen!", "Dein Account wurde erstellt.")

        flash("Registrierung erfolgreich")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# =========================
# LOGIN
# =========================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Login fehlgeschlagen")

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================
@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# =========================
# LOGOUT
# =========================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# =========================
# PASSWORT RESET
# =========================
@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()

        if user:
            send_email(email, "Passwort Reset", "Du hast einen Reset angefordert.")
            flash("Email gesendet")

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")