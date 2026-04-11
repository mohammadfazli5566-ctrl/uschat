from datetime import datetime
import random
import smtplib
from email.message import EmailMessage

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, PasswordResetCode, EmailVerificationCode

auth_bp = Blueprint("auth", __name__)

TEST_MODE = True


def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            current_app.config["MAIL_USERNAME"],
            current_app.config["MAIL_PASSWORD"]
        )
        smtp.send_message(msg)


@auth_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("chat.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Diese E-Mail ist bereits registriert.")
            return redirect(url_for("auth.register"))

        user_count = User.query.count()

        user = User(
            username=username,
            email=email,
            is_verified=False,
            is_admin=(user_count == 0),
            is_active_user=True
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        EmailVerificationCode.query.filter_by(email=email).delete()

        code = str(random.randint(100000, 999999))
        verify_entry = EmailVerificationCode(email=email, code=code)
        db.session.add(verify_entry)
        db.session.commit()

        if TEST_MODE:
            print("\n" + "=" * 50, flush=True)
            print("REGISTRIERUNGS-CODE", flush=True)
            print("E-Mail:", email, flush=True)
            print("Code:", code, flush=True)
            print("=" * 50 + "\n", flush=True)
            flash("Testmodus: Bestätigungscode wurde im Terminal angezeigt.")
            if user.is_admin:
                flash("Der erste Benutzer wurde automatisch als Admin erstellt.")
            return redirect(url_for("auth.verify_email", email=email))

        try:
            send_email(
                email,
                "UsChat Secure - E-Mail bestätigen",
                (
                    f"Hallo {username},\n\n"
                    f"dein Bestätigungscode ist:\n\n"
                    f"{code}\n\n"
                    f"Der Code ist 10 Minuten gültig.\n\n"
                    f"UsChat Secure"
                )
            )
            flash("Bestätigungscode wurde per E-Mail gesendet.")
            if user.is_admin:
                flash("Der erste Benutzer wurde automatisch als Admin erstellt.")
            return redirect(url_for("auth.verify_email", email=email))
        except Exception as e:
            flash(f"E-Mail konnte nicht gesendet werden: {e}")
            return redirect(url_for("auth.register"))

    return render_template("register.html")


@auth_bp.route("/verify-email/<email>", methods=["GET", "POST"])
def verify_email(email):
    if request.method == "POST":
        code = request.form.get("code", "").strip()

        if not code:
            flash("Bitte Code eingeben.")
            return redirect(url_for("auth.verify_email", email=email))

        entry = EmailVerificationCode.query.filter_by(email=email, code=code).first()

        if not entry:
            flash("Falscher Code.")
            return redirect(url_for("auth.verify_email", email=email))

        if datetime.utcnow() > entry.expires_at:
            db.session.delete(entry)
            db.session.commit()
            flash("Code ist abgelaufen. Bitte neu registrieren.")
            return redirect(url_for("auth.register"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Benutzer nicht gefunden.")
            return redirect(url_for("auth.register"))

        user.is_verified = True
        db.session.delete(entry)
        db.session.commit()

        flash("E-Mail erfolgreich bestätigt. Jetzt einloggen.")
        return redirect(url_for("auth.login"))

    return render_template("verify_email.html", email=email)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("E-Mail oder Passwort ist falsch.")
            return redirect(url_for("auth.login"))

        if not user.is_verified:
            flash("Bitte zuerst deine E-Mail bestätigen.")
            return redirect(url_for("auth.verify_email", email=email))

        if not user.is_active_user:
            flash("Dein Konto wurde deaktiviert. Bitte Admin kontaktieren.")
            return redirect(url_for("auth.login"))

        login_user(user)
        user.is_online = True
        user.last_seen = datetime.utcnow()
        db.session.commit()

        flash("Erfolgreich eingeloggt.")
        return redirect(url_for("chat.dashboard"))

    return render_template("login.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Bitte E-Mail eingeben.")
            return redirect(url_for("auth.forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Diese E-Mail wurde nicht gefunden.")
            return redirect(url_for("auth.forgot_password"))

        PasswordResetCode.query.filter_by(email=email).delete()

        code = str(random.randint(100000, 999999))
        reset_code = PasswordResetCode(email=email, code=code)
        db.session.add(reset_code)
        db.session.commit()

        if TEST_MODE:
            print("\n" + "=" * 50, flush=True)
            print("PASSWORT-RESET-CODE", flush=True)
            print("E-Mail:", email, flush=True)
            print("Code:", code, flush=True)
            print("=" * 50 + "\n", flush=True)
            flash("Testmodus: Reset-Code wurde im Terminal angezeigt.")
            return redirect(url_for("auth.reset_password", email=email))

        try:
            send_email(
                to_email=email,
                subject="UsChat Secure - Passwort zurücksetzen",
                body=(
                    f"Hallo {user.username},\n\n"
                    f"dein neuer Passwort-Code lautet:\n\n"
                    f"{code}\n\n"
                    f"Der Code ist 10 Minuten gültig.\n\n"
                    f"UsChat Secure"
                )
            )
            flash("Ein neuer Code wurde an deine E-Mail gesendet.")
            return redirect(url_for("auth.reset_password", email=email))
        except Exception as e:
            flash(f"E-Mail konnte nicht gesendet werden: {e}")
            return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<email>", methods=["GET", "POST"])
def reset_password(email):
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not code or not password or not confirm_password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("auth.reset_password", email=email))

        if password != confirm_password:
            flash("Die Passwörter stimmen nicht überein.")
            return redirect(url_for("auth.reset_password", email=email))

        reset_entry = PasswordResetCode.query.filter_by(email=email, code=code).first()

        if not reset_entry:
            flash("Der Code ist falsch.")
            return redirect(url_for("auth.reset_password", email=email))

        if datetime.utcnow() > reset_entry.expires_at:
            db.session.delete(reset_entry)
            db.session.commit()
            flash("Der Code ist abgelaufen. Bitte neuen Code anfordern.")
            return redirect(url_for("auth.forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Benutzer nicht gefunden.")
            return redirect(url_for("auth.forgot_password"))

        user.set_password(password)
        db.session.delete(reset_entry)
        db.session.commit()

        flash("Passwort erfolgreich geändert. Bitte einloggen.")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email)


@auth_bp.route("/logout")
@login_required
def logout():
    current_user.is_online = False
    current_user.last_seen = datetime.utcnow()
    db.session.commit()

    logout_user()
    flash("Du wurdest ausgeloggt.")
    return redirect(url_for("auth.login"))

TEST_MODE = False