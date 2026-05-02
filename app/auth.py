from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, db

# 🔥 SENDGRID
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

auth_bp = Blueprint("auth", __name__)


# =========================
# EMAIL SENDEN (SENDGRID)
# =========================
def send_email(to_email, subject, body):
    try:
        message = Mail(
            from_email=current_app.config.get("MAIL_DEFAULT_SENDER"),
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )

        sg = SendGridAPIClient(current_app.config.get("SENDGRID_API_KEY"))
        sg.send(message)

        return True
    except Exception as e:
        print("SendGrid Fehler:", e)
        return False


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

        # prüfen ob existiert
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Diese E-Mail ist bereits registriert.")
            return redirect(url_for("auth.register"))

        # 🔥 USER ERSTELLEN (RICHTIG)
        new_user = User(
    email=email,
    username=username,
    is_verified=True   # 🔥 DAS HIER HINZUFÜGEN
    )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # 🔥 EMAIL SENDEN
        send_email(
            email,
            "Willkommen bei UsChat",
            f"Hallo {username}, dein Account wurde erfolgreich erstellt!"
        )

        flash("Registrierung erfolgreich. Du kannst dich jetzt einloggen.")
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

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("auth.dashboard"))

        flash("Login fehlgeschlagen.")

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
# PASSWORT RESET (EINFACH)
# =========================
@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()

        if user:
            send_email(
                email,
                "Passwort Reset",
                "Du hast einen Passwort-Reset angefordert."
            )
            flash("E-Mail wurde gesendet.")

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")