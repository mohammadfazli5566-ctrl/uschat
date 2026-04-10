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

MAX_CONTENT_LENGTH = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "webm", "mov"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DB =================
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT,
            file_name TEXT,
            file_type TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def migrate_db():
    conn = get_db_connection()

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN file_name TEXT")
    except:
        pass

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN file_type TEXT")
    except:
        pass

    try:
        conn.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")
    except:
        pass

    conn.commit()
    conn.close()


def ensure_db():
    init_db()
    migrate_db()


# 🔥 WICHTIG für Render
ensure_db()

# ================= FILE =================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    if ext in {"png", "jpg", "jpeg", "gif"}:
        return "image"
    if ext in {"mp4", "webm", "mov"}:
        return "video"
    return None


# ================= CLEANUP =================
def delete_old_messages():
    ensure_db()

    conn = get_db_connection()

    limit = datetime.now() - timedelta(hours=48)
    limit = limit.strftime("%Y-%m-%d %H:%M:%S")

    rows = conn.execute(
        "SELECT file_name FROM messages WHERE created_at IS NOT NULL AND created_at < ?",
        (limit,)
    ).fetchall()

    for r in rows:
        if r["file_name"]:
            path = os.path.join(app.config["UPLOAD_FOLDER"], r["file_name"])
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

    conn.execute(
        "DELETE FROM messages WHERE created_at IS NOT NULL AND created_at < ?",
        (limit,)
    )
    conn.commit()
    conn.close()


@app.before_request
def auto_cleanup():
    try:
        delete_old_messages()
    except:
        pass


# ================= AUTH =================
def is_logged_in():
    return "user" in session


# ================= ROUTES =================
@app.route("/")
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        e = request.form["email"]
        p = request.form["password"]

        if not u or not e or not p:
            flash("Alles ausfüllen")
            return redirect(url_for("register"))

        h = generate_password_hash(p)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username,email,password) VALUES (?,?,?)",
                (u, e, h)
            )
            conn.commit()
            flash("Registriert")
            return redirect(url_for("login"))
        except:
            flash("User existiert")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        e = request.form["email"]
        p = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (e,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], p):
            session["user"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Falsch")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    conn = get_db_connection()
    users = conn.execute(
        "SELECT username FROM users WHERE username != ?",
        (session["user"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", users=users, current_user=session["user"])


@app.route("/chat/<username>")
def chat(username):
    if not is_logged_in():
        return redirect(url_for("login"))

    conn = get_db_connection()
    msgs = conn.execute("""
        SELECT * FROM messages
        WHERE (sender=? AND receiver=?)
        OR (sender=? AND receiver=?)
        ORDER BY created_at
    """, (session["user"], username, username, session["user"])).fetchall()
    conn.close()

    return render_template("chat.html", messages=msgs,
                           chat_partner=username,
                           current_user=session["user"])


@app.route("/send_message/<username>", methods=["POST"])
def send_message(username):
    if not is_logged_in():
        return redirect(url_for("login"))

    msg = request.form.get("message")
    file = request.files.get("file")

    fname = None
    ftype = None

    if file and file.filename:
        if allowed_file(file.filename):
            name = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{name}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
            file.save(path)

            fname = unique
            ftype = get_file_type(unique)

    if not msg and not fname:
        return redirect(url_for("chat", username=username))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO messages (sender,receiver,message,file_name,file_type,created_at)
        VALUES (?,?,?,?,?,?)
    """, (session["user"], username, msg, fname, ftype, now))
    conn.commit()
    conn.close()

    return redirect(url_for("chat", username=username))


@app.route("/media/<filename>")
def media(filename):
    if not is_logged_in():
        return redirect(url_for("login"))

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ================= START =================
if __name__ == "__main__":
    app.run(debug=True)