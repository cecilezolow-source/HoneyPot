"""
HoneyPot - Die Imker-Community
===============================
WICHTIG / ACHTUNG - NUR FÜR LEHRZWECKE:
Diese Anwendung ist ABSICHTLICH unsicher programmiert, um SQL-Injection-Angriffe
in einem kontrollierten Kursumfeld zu üben. NIEMALS so in Produktion einsetzen!

Bekannte, absichtliche Schwachstellen (für die Trainer-Dokumentation, siehe README.md):
  1. /login       -> klassischer Auth-Bypass via String-Concatenation
  2. /dashboard    -> Suchfeld (?q=) erlaubt UNION-based Injection
  3. /honigtopf/<id> -> ID wird ungeprüft in die Query eingebaut (Error-/UNION-based)
  4. /register    -> Prüf-Query auf existierenden Usernamen ist ebenfalls verwundbar
  5. Passwörter werden im Klartext gespeichert (keine Hashes)
  6. DB-Fehlermeldungen werden dem Nutzer direkt angezeigt (Information Disclosure)
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "honeypot_dev_secret"  # auch das ist absichtlich schwach gewählt

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "honeypot"),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# REGISTRIERUNG
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            flash("Bitte Benutzername und Passwort angeben.")
            return render_template("register.html")

        if password != password2:
            flash("Die Passwörter stimmen nicht überein.")
            return render_template("register.html")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # !!! SCHWACHSTELLE 4: String-Concatenation statt Prepared Statement !!!
        check_query = f"SELECT * FROM users WHERE username = '{username}'"
        cursor.execute(check_query)
        existing = cursor.fetchone()

        if existing:
            flash("Dieser Benutzername ist bereits vergeben.")
            cursor.close()
            db.close()
            return render_template("register.html")

        # !!! SCHWACHSTELLE: auch das INSERT ist per String-Concatenation gebaut !!!
        insert_query = (
            f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
        )
        try:
            cursor.execute(insert_query)
            db.commit()
            flash("Registrierung erfolgreich! Du kannst dich jetzt anmelden.")
            cursor.close()
            db.close()
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            # !!! SCHWACHSTELLE 6: DB-Fehler wird direkt an den Nutzer durchgereicht !!!
            flash(f"Datenbankfehler bei der Registrierung: {err}")
            cursor.close()
            db.close()
            return render_template("register.html")

    return render_template("register.html")


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # !!! SCHWACHSTELLE 1: Klassische SQL-Injection-Lücke im Login !!!
        # Beispiel-Payload für Benutzername:  admin' -- 
        # -> überschreibt die Passwortprüfung komplett
        query = (
            f"SELECT * FROM users WHERE username = '{username}' "
            f"AND password = '{password}'"
        )

        try:
            cursor.execute(query)
            user = cursor.fetchone()
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler beim Login: {err}")
            user = None

        cursor.close()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            flash("Login fehlgeschlagen. Benutzername oder Passwort falsch.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# DASHBOARD / ÜBERSICHT DER HONIGTÖPFE
# ---------------------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("q", "")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if search:
        # !!! SCHWACHSTELLE 2: Suchfeld erlaubt UNION-based SQL-Injection !!!
        # Beispiel-Payload: ' UNION SELECT id, username, password, 1 FROM users -- 
        query = (
            f"SELECT id, title, created_at FROM honigtoepfe "
            f"WHERE title LIKE '%{search}%' ORDER BY created_at DESC"
        )
    else:
        query = "SELECT id, title, created_at FROM honigtoepfe ORDER BY created_at DESC"

    try:
        cursor.execute(query)
        honigtoepfe = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Datenbankfehler bei der Suche: {err}")
        honigtoepfe = []

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        honigtoepfe=honigtoepfe,
        username=session.get("username"),
        search=search,
    )


# ---------------------------------------------------------------------------
# EINZELNEN HONIGTOPF ANSEHEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/<topf_id>")
def honigtopf_detail(topf_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # !!! SCHWACHSTELLE 3: ID wird nicht validiert/gecastet, sondern direkt eingebaut !!!
    # Beispiel-Payload: 1 UNION SELECT id, username, password, NOW() FROM users -- 
    query = (
        f"SELECT honigtoepfe.id, honigtoepfe.title, honigtoepfe.content, "
        f"honigtoepfe.created_at, users.username "
        f"FROM honigtoepfe JOIN users ON honigtoepfe.author_id = users.id "
        f"WHERE honigtoepfe.id = {topf_id}"
    )

    try:
        cursor.execute(query)
        topf = cursor.fetchone()
    except mysql.connector.Error as err:
        flash(f"Datenbankfehler: {err}")
        topf = None

    cursor.close()
    db.close()

    if not topf:
        flash("Honigtopf nicht gefunden.")
        return redirect(url_for("dashboard"))

    return render_template("honigtopf_detail.html", topf=topf)


# ---------------------------------------------------------------------------
# NEUEN HONIGTOPF ANLEGEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/neu", methods=["GET", "POST"])
def new_honigtopf():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")

        if not title or not content:
            flash("Bitte Titel und Inhalt ausfüllen.")
            return render_template("new_honigtopf.html")

        db = get_db()
        cursor = db.cursor()

        query = (
            f"INSERT INTO honigtoepfe (title, content, author_id) "
            f"VALUES ('{title}', '{content}', {session['user_id']})"
        )
        try:
            cursor.execute(query)
            db.commit()
            flash("Honigtopf erfolgreich angelegt!")
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler: {err}")
        finally:
            cursor.close()
            db.close()

        return redirect(url_for("dashboard"))

    return render_template("new_honigtopf.html")


if __name__ == "__main__":
    # debug=True NUR für die Übungsumgebung! Niemals in Produktion.
    app.run(debug=True, host="0.0.0.0", port=5000)
