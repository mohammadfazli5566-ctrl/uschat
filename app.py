from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import sqlite3
import os
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uschat_secret_2026")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "private_uploads")
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "webm", "mov"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# DB Verbindung
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# DB erstellen
def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT,
            file_name TEXT,
            file_type TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# Migration für alte DB
def migrate_db():
    conn = get_db_connection()

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN file_name TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN file_type TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def ensure_db():
    init_db()
    migrate_db()


# WICHTIG für Render
ensure_db()


# Datei prüfen
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Typ bestimmen
def get_file_type(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    if ext in {"png", "jpg", "jpeg", "gif"}:
        return "image"
    if ext in {"mp4", "webm", "mov"}:
        return "video"
    return None


# Alte Nachrichten löschen
def delete_old_messages():
    ensure_db()
    conn = get_db_connection()

    limit_time = datetime.now() - timedelta(hours=48)
    limit_time_str = limit_time.strftime("%Y-%m-%d %H:%M:%S")

    old_messages = conn.execute(
        "SELECT file_name FROM messages WHERE created_at IS NOT NULL AND created_at < ?",
        (limit_time_str,)
    ).fetchall()

    for msg in old_messages:
        if msg["file_name"]:
            path = os.path.join(app.config["UPLOAD_FOLDER"], msg["file_name"])
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    conn.execute(
        "DELETE FROM messages WHERE created_at IS NOT NULL AND created_at < ?",
        (limit_time_str,)
    )
    conn.commit()
    conn.close()


# Login prüfen
def is_logged_in():
    return "user" in session


@app.before_request
def auto_cleanup():
    try:
        delete_old_messages()
    except Exception:
        pass


# Home
@app.route("/")
def home():
    ensure_db()
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    ensure_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("Alle Felder ausfüllen")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Passwort zu kurz")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            conn.commit()
            flash("Registriert")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("User oder E-Mail existiert schon")
        finally:
            conn.close()

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_db()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Falsche Daten")

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Dashboard
@app.route("/dashboard")
def dashboard():
    ensure_db()

    if not is_logged_in():
        return redirect(url_for("login"))

    conn = get_db_connection()
    users = conn.execute(
        "SELECT username FROM users WHERE username != ? ORDER BY username ASC",
        (session["user"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", users=users, current_user=session["user"])


# Chat
@app.route("/chat/<username>")
def chat(username):
    ensure_db()

    if not is_logged_in():
        return redirect(url_for("login"))

    conn = get_db_connection()

    partner = conn.execute(
        "SELECT username FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not partner:
        conn.close()
        flash("Benutzer nicht gefunden")
        return redirect(url_for("dashboard"))

    messages = conn.execute("""
        SELECT * FROM messages
        WHERE (sender = ? AND receiver = ?)
           OR (sender = ? AND receiver = ?)
        ORDER BY created_at ASC, id ASC
    """, (session["user"], username, username, session["user"])).fetchall()
    conn.close()

    return render_template(
        "chat.html",
        messages=messages,
        chat_partner=username,
        current_user=session["user"]
    )


# Send Message
@app.route("/send_message/<username>", methods=["POST"])
def send_message(username):
    ensure_db()

    if not is_logged_in():
        return redirect(url_for("login"))

    message = request.form.get("message", "").strip()
    file = request.files.get("file")

    file_name = None
    file_type = None

    if file and file.filename != "":
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
            file.save(path)

            file_name = unique
            file_type = get_file_type(unique)
        else:
            flash("Datei nicht erlaubt")
            return redirect(url_for("chat", username=username))

    if not message and not file_name:
        flash("Leer")
        return redirect(url_for("chat", username=username))

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO messages (sender, receiver, message, file_name, file_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user"], username, message, file_name, file_type, created_at))
    conn.commit()
    conn.close()

    return redirect(url_for("chat", username=username))


# Protected Media
@app.route("/media/<filename>")
def media(filename):
    ensure_db()

    if not is_logged_in():
        return redirect(url_for("login"))

    conn = get_db_connection()
    file = conn.execute("""
        SELECT * FROM messages
        WHERE file_name = ?
        AND (sender = ? OR receiver = ?)
    """, (filename, session["user"], session["user"])).fetchone()
    conn.close()

    if not file:
        abort(403)

    mime, _ = mimetypes.guess_type(filename)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, mimetype=mime)


# Datei zu groß
@app.errorhandler(413)
def too_large(e):
    flash("Datei zu groß")
    return redirect(url_for("dashboard"))


# PWA
@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")


@app.route("/sw.js")
def sw():
    return send_from_directory("static", "sw.js")


# Start
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)