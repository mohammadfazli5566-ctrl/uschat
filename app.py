from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uschat_super_secret_key_123")

DATABASE = "database.db"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "doc", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==============================
# DATABASE
# ==============================
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT,
            message TEXT,
            file_name TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Render / Gunicorn startet __main__ nicht.
# Deshalb Datenbank hier direkt initialisieren.
init_db()


# ==============================
# HILFSFUNKTIONEN
# ==============================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files():
    """
    Löscht Upload-Dateien älter als 24 Stunden,
    wenn sie in messages.file_name gespeichert sind.
    """
    limit_time = datetime.now() - timedelta(hours=24)
    limit_time_str = limit_time.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    old_files = conn.execute(
        "SELECT file_name FROM messages WHERE created_at < ? AND file_name IS NOT NULL AND file_name != ''",
        (limit_time_str,)
    ).fetchall()

    for row in old_files:
        file_name = row["file_name"]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    conn.close()


# ==============================
# ROUTES
# ==============================
@app.route("/")
def home():
    cleanup_old_files()

    if "user" in session:
        return redirect(url_for("chat"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Bitte alle Felder ausfüllen.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            conn.close()

            flash("Registrierung erfolgreich. Bitte einloggen.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Benutzername existiert bereits.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            flash("Login erfolgreich.")
            return redirect(url_for("chat"))
        else:
            flash("Falscher Benutzername oder Passwort.")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return redirect(url_for("login"))

    cleanup_old_files()

    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        uploaded_file = request.files.get("file")
        saved_filename = None

        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename):
                original_filename = secure_filename(uploaded_file.filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                saved_filename = f"{timestamp}_{original_filename}"
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_filename)
                uploaded_file.save(file_path)
            else:
                flash("Dateityp nicht erlaubt.")
                return redirect(url_for("chat"))

        if not message_text and not saved_filename:
            flash("Bitte Nachricht schreiben oder Datei auswählen.")
            return redirect(url_for("chat"))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO messages (sender, receiver, message, file_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user"],
            None,
            message_text,
            saved_filename,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("chat"))

    conn = get_db_connection()
    messages = conn.execute("""
        SELECT * FROM messages
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return render_template("chat.html", messages=messages, user=session["user"])


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/logout")
def logout():
    session.clear()
    flash("Du wurdest ausgeloggt.")
    return redirect(url_for("login"))


# ==============================
# START
# ==============================
if __name__ == "__main__":
    app.run(debug=True)