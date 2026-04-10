from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
import sqlite3
import smtplib
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uschat_secret_key_123")

DATABASE = "database.db"

# HIER DEINE ECHTE GMAIL UND APP-PASSWORT EINTRAGEN
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "deinegmailadresse@gmail.com")
SENDER_APP_PASSWORD = os.environ.get("SENDER_APP_PASSWORD", "dein_google_app_passwort")

# Temporäre Reset-Codes
reset_codes = {}


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# WICHTIG: Tabelle direkt beim Start erstellen
init_db()


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or not password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            conn.commit()
            conn.close()

            flash("Registrierung erfolgreich. Bitte einloggen.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Diese E-Mail ist bereits registriert.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Erfolgreich eingeloggt.")
            return redirect(url_for("chat"))
        else:
            flash("E-Mail oder Passwort ist falsch.")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/chat")
def chat():
    if "user_id" not in session:
        flash("Bitte zuerst einloggen.")
        return redirect(url_for("login"))

    return render_template("chat.html", username=session["username"])


@app.route("/logout")
def logout():
    session.clear()
    flash("Du wurdest ausgeloggt.")
    return redirect(url_for("login"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if not user:
            flash("Diese E-Mail wurde nicht gefunden.")
            return redirect(url_for("forgot_password"))

        code = str(random.randint(100000, 999999))
        reset_codes[email] = code

        msg = EmailMessage()
        msg["Subject"] = "UsChat Passwort zurücksetzen"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        msg.set_content(
            f"Hallo {user['username']},\n\n"
            f"dein UsChat Code zum Zurücksetzen des Passworts lautet: {code}\n\n"
            f"Wenn du das nicht angefordert hast, ignoriere diese E-Mail.\n\n"
            f"UsChat"
        )

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
                smtp.send_message(msg)

            flash("Der Code wurde an deine E-Mail gesendet.")
            return redirect(url_for("reset_password", email=email))

        except Exception as e:
            flash(f"E-Mail konnte nicht gesendet werden: {e}")
            return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<email>", methods=["GET", "POST"])
def reset_password(email):
    if request.method == "POST":
        code = request.form["code"].strip()
        new_password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not code or not new_password or not confirm_password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("reset_password", email=email))

        if new_password != confirm_password:
            flash("Die Passwörter stimmen nicht überein.")
            return redirect(url_for("reset_password", email=email))

        if email in reset_codes and reset_codes[email] == code:
            hashed_password = generate_password_hash(new_password)

            conn = get_db_connection()
            conn.execute(
                "UPDATE users SET password = ? WHERE email = ?",
                (hashed_password, email)
            )
            conn.commit()
            conn.close()

            reset_codes.pop(email, None)

            flash("Passwort erfolgreich geändert. Bitte einloggen.")
            return redirect(url_for("login"))
        else:
            flash("Falscher Code.")
            return redirect(url_for("reset_password", email=email))

    return render_template("reset_password.html", email=email)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)