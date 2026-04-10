from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

DATABASE = "database.db"


# ==============================
# DATABASE VERBINDUNG
# ==============================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==============================
# DATABASE ERSTELLEN (nur 1x)
# ==============================
def init_db():
    conn = get_db()

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
        sender TEXT,
        message TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# ==============================
# STARTSEITE
# ==============================
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("chat"))
    return redirect(url_for("login"))


# ==============================
# REGISTRIEREN
# ==============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            flash("Bitte alle Felder ausfüllen")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)

        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                         (username, hashed_pw))
            conn.commit()
            conn.close()

            flash("Registrierung erfolgreich!")
            return redirect(url_for("login"))

        except:
            flash("Benutzer existiert bereits!")
            return redirect(url_for("register"))

    return render_template("register.html")


# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?",
                            (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            return redirect(url_for("chat"))
        else:
            flash("Login fehlgeschlagen!")
            return redirect(url_for("login"))

    return render_template("login.html")


# ==============================
# CHAT
# ==============================
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":
        message = request.form["message"]

        if message:
            conn.execute("""
            INSERT INTO messages (sender, message, created_at)
            VALUES (?, ?, ?)
            """, (session["user"], message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    messages = conn.execute("""
    SELECT * FROM messages ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template("chat.html", messages=messages, user=session["user"])


# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==============================
# START
# ==============================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)