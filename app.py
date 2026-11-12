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
  7. /passwort-neu  -> Passwort-Reset mit vorhersagbarem Token (Account-Übernahme)
  8. /konto/wechseln -> "Anmelden als" ohne Rollenprüfung (Privilege Escalation)

Neu (Nummern wie in den Code-Kommentaren "SCHWACHSTELLE 13" usw.):
 13. /fotos         -> Unrestricted File Upload (HTML/SVG wird im App-Ursprung ausgeliefert)
 14. /dashboard?q=  -> Reflected XSS (Suchbegriff wird ungefiltert zurückgegeben)
 15. /etikett/designer -> Server-Side Template Injection (liest die App-Konfiguration aus)
 16. /fotos/import  -> SSRF (Server ruft beliebige URLs ab, auch interne Endpunkte)
"""

from flask import Flask, Response, render_template, request, redirect, url_for, g, send_from_directory
from itsdangerous import URLSafeTimedSerializer, BadSignature
from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment
import mysql.connector
import hashlib
import os
import urllib.error
import urllib.parse
import urllib.request

app = Flask(__name__)
# Schlüssel, mit dem die Cookies signiert werden – absichtlich schwach gewählt.
# Wer ihn kennt, kann sich ein eigenes "auth"-Cookie bauen und z. B. als admin auftreten.
SIGNING_KEY = "honeypot_dev_secret"
app.secret_key = SIGNING_KEY

# ---------------------------------------------------------------------------
# Eigene, signierte Cookies statt flask.session
# ---------------------------------------------------------------------------
# Wir nutzen KEINE flask.session, sondern setzen und prüfen die Cookies selbst.
# itsdangerous signiert die Werte, damit sie clientseitig nicht gefälscht werden
# können (solange der Schlüssel geheim bleibt – hier ist er es bewusst nicht).
_signer = URLSafeTimedSerializer(SIGNING_KEY, salt="honeypot-cookie")


def _sign(data):
    return _signer.dumps(data)


def _unsign(raw, max_age=None):
    if not raw:
        return None
    try:
        return _signer.loads(raw, max_age=max_age)
    except BadSignature:
        return None


def current_user():
    """Liest das signierte 'auth'-Cookie aus. Gibt {'user_id', 'username'} oder None."""
    if "current_user" not in g:
        g.current_user = _unsign(request.cookies.get("auth"))
    return g.current_user


def login_user(response, user):
    """Setzt das signierte Auth-Cookie auf der Response."""
    token = _sign({"user_id": user["id"], "username": user["username"]})
    # !!! SCHWACHSTELLE 8: Auth-Cookie OHNE HttpOnly !!!
    # Normalerweise verhindert httponly=True, dass JavaScript den Cookie liest.
    # Hier ist es bewusst abgeschaltet, damit per Stored-XSS (SCHWACHSTELLE 4)
    # document.cookie ausgelesen und der Auth-Cookie gestohlen werden kann.
    response.set_cookie("auth", token, httponly=False, samesite="Lax")
    return response


def logout_user(response):
    response.delete_cookie("auth")
    return response


def reset_token(username):
    """Erzeugt den 'Zurücksetz-Token' für ein Konto.

    !!! SCHWACHSTELLE 11: VORHERSAGBARER PASSWORT-RESET-TOKEN !!!
    Der Token hängt ausschließlich vom Benutzernamen und einem fest im Code
    stehenden "Salz" ab. Er ist damit für jede:n ausrechenbar, die/der den
    Benutzernamen kennt (z. B. aus SCHWACHSTELLE 2) und diesen Code sieht
    (z. B. über Path Traversal, SCHWACHSTELLE 10). Man braucht also GAR KEINE
    E-Mail, um das Passwort eines fremden Kontos zurückzusetzen.
    Richtig wäre: ein zufälliger, einmaliger, zeitlich begrenzter Token, der
    serverseitig gespeichert und nach Gebrauch entwertet wird.
    """
    return hashlib.md5(f"{username}:imkerglueck".encode()).hexdigest()[:8]


def flash(message):
    """Flash-Ersatz: sammelt Meldungen, die in after_request als Cookie gesetzt werden."""
    g.setdefault("flashes_out", [])
    g.flashes_out.append(message)


# ---------------------------------------------------------------------------
# SQL-TIPPS: Bei fehlgeschlagenen Injection-Versuchen die Abfrage zeigen
# ---------------------------------------------------------------------------
# Didaktische Hilfe: Wer eine SQL-Injection probiert und scheitert, bekommt
# die tatsächlich an die Datenbank geschickte Abfrage angezeigt. So sieht man,
# wo die eigene Eingabe landet und welche Logik man aushebeln muss.
SQLI_MERKMALE = ("'", '"', "--", "#", "/*", ";", " or ", " and ", "union", "select", "sleep(")


def sieht_nach_sqli_aus(*werte):
    """True, wenn eine der Eingaben typische SQL-Injection-Zeichen enthält."""
    for wert in werte:
        w = str(wert or "").lower()
        if any(m in w for m in SQLI_MERKMALE):
            return True
    return False


def sql_tipp(query):
    """Hängt einen Tipp mit der ausgeführten SQL-Abfrage an die Meldungen."""
    flash({"tipp": "Tipp – diese Abfrage wurde an die Datenbank geschickt:", "sql": query})


@app.before_request
def _load_flashes():
    # Meldungen aus dem vorherigen Request einlesen (und zum Löschen vormerken)
    g.flashes_in = _unsign(request.cookies.get("flash")) or []
    g.flashes_out = []


@app.after_request
def _store_cookies(response):
    # Wurden die Meldungen diesen Request schon angezeigt, altes Cookie löschen.
    # Wurden neue erzeugt, aber (z. B. bei einem Redirect) noch nicht angezeigt,
    # ins Cookie schreiben, damit sie beim nächsten Rendern erscheinen.
    out = g.get("flashes_out")
    shown = g.get("flashes_shown")
    if out and not shown:
        response.set_cookie("flash", _sign(out), httponly=True, samesite="Lax")
    elif shown and request.cookies.get("flash"):
        response.delete_cookie("flash")
    return response


@app.context_processor
def inject_auth():
    def get_flashed_messages(*args, **kwargs):
        # Meldungen aus dem letzten Request plus die dieses Requests anzeigen
        g.flashes_shown = True
        return g.get("flashes_in", []) + g.get("flashes_out", [])
    return {"current_user": current_user(), "get_flashed_messages": get_flashed_messages}

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "honeypot"),
    # Verbindung fest auf UTF-8 (utf8mb4), damit Umlaute (ä, ö, ü, ß) korrekt
    # gespeichert und gelesen werden – sonst entsteht Mojibake wie "FrÃ¼hjahr".
    "charset": "utf8mb4",
}


def get_db():
    # buffered=True: Ergebnisse werden komplett geladen. So stürzt fetchone() nicht ab,
    # wenn eine Injection wie ' OR 1=1 -- mehrere Zeilen zurückliefert.
    return mysql.connector.connect(**DB_CONFIG, buffered=True)


# Honigsorten (bestimmen die Farbe des Glases) und Kategorien der Honigtöpfe
SORTEN = {
    "akazie": {"name": "Akazienhonig", "farbe": "#f5df7a"},
    "raps":   {"name": "Rapshonig",    "farbe": "#f0d48f"},
    "bluete": {"name": "Blütenhonig",  "farbe": "#f0a21a"},
    "linde":  {"name": "Lindenhonig",  "farbe": "#d9b23a"},
    "heide":  {"name": "Heidehonig",   "farbe": "#b4521c"},
    "wald":   {"name": "Waldhonig",    "farbe": "#6b3410"},
}

KATEGORIEN = {
    "rezept":    {"name": "Rezept"},
    "tipp":      {"name": "Tipp"},
    "anleitung": {"name": "Anleitung"},
    "wissen":    {"name": "Wissen"},
    "frage":     {"name": "Frage"},
}


@app.context_processor
def inject_honig():
    return {"SORTEN": SORTEN, "KATEGORIEN": KATEGORIEN}


def attach_details(db, rows):
    """Hängt Sorte und Kategorie an die Zeilen.

    Läuft bewusst als eigene, parametrisierte Query, damit die verwundbaren
    Queries (und damit die UNION-Übungen) unverändert bleiben. Zeilen, die per
    Injection eingeschleust wurden, bekommen einfach Standardwerte.
    """
    ids = [r["id"] for r in rows if isinstance(r.get("id"), int)]
    details = {}
    if ids:
        try:
            cursor = db.cursor(dictionary=True)
            placeholders = ", ".join(["%s"] * len(ids))
            cursor.execute(
                "SELECT topf_id, kategorie, sorte FROM honigtopf_details "
                f"WHERE topf_id IN ({placeholders})",
                ids,
            )
            details = {d["topf_id"]: d for d in cursor.fetchall()}
            cursor.close()
        except mysql.connector.Error:
            details = {}

    for r in rows:
        d = details.get(r.get("id"), {})
        r["sorte"] = d.get("sorte") if d.get("sorte") in SORTEN else "bluete"
        r["kategorie"] = d.get("kategorie") if d.get("kategorie") in KATEGORIEN else "wissen"
    return rows


@app.route("/")
def index():
    if current_user():
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
        try:
            cursor.execute(check_query)
            existing = cursor.fetchone()
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler bei der Registrierung: {err}")
            sql_tipp(check_query)
            cursor.close()
            db.close()
            return render_template("register.html")

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
            sql_tipp(insert_query)
            cursor.close()
            db.close()
            return render_template("register.html")

    return render_template("register.html")


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # !!! SCHWACHSTELLE 9: Open Redirect ueber ?next= !!!
    # Nach erfolgreichem Login wird ungeprueft auf das Ziel aus ?next=
    # weitergeleitet. Ein praeparierter Link wie
    #   /login?next=https://boese-seite.example/phish
    # schickt die Person nach dem Login auf eine fremde Seite (Phishing).
    # Richtig waere: nur auf eigene, relative Pfade weiterleiten.
    next_url = request.values.get("next", "")
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
            sql_tipp(query)
            user = None
        else:
            if not user and sieht_nach_sqli_aus(username, password):
                sql_tipp(query)

        cursor.close()
        db.close()

        if user:
            # Auth-Zustand als signiertes Cookie auf der Antwort setzen
            # Open Redirect: Ziel kommt ungeprueft aus ?next= / dem Formular.
            ziel = next_url or url_for("dashboard")
            return login_user(redirect(ziel), user)
        else:
            # Allgemeine Meldung vor dem Tipp anzeigen
            g.flashes_out.insert(0, "Login fehlgeschlagen. Benutzername oder Passwort falsch.")

    return render_template("login.html", next=next_url)


@app.route("/logout")
def logout():
    return logout_user(redirect(url_for("login")))


# ---------------------------------------------------------------------------
# PASSWORT VERGESSEN / ZURÜCKSETZEN
# ---------------------------------------------------------------------------
@app.route("/passwort-vergessen", methods=["GET", "POST"])
def passwort_vergessen():
    """Schritt 1: Nutzer gibt seinen Benutzernamen ein.

    Aus "Datenschutzgründen" wird bewusst nicht verraten, ob das Konto
    existiert. Das nützt hier aber wenig: Der Reset-Token (siehe reset_token)
    ist ohnehin ratbar, man muss ihn gar nicht per Mail zugeschickt bekommen.
    """
    if request.method == "POST":
        request.form.get("username", "")
        flash("Falls dieses Konto existiert, haben wir einen Zurücksetz-Link erzeugt.")
        return redirect(url_for("login"))
    return render_template("passwort_vergessen.html")


@app.route("/passwort-neu", methods=["GET", "POST"])
def passwort_neu():
    """Schritt 2: Mit ?user=<name>&token=<token> ein neues Passwort setzen.

    Der Token wird mit reset_token() geprüft – und der ist vorhersagbar
    (SCHWACHSTELLE 11). Wer den Benutzernamen kennt und den Algorithmus sieht,
    kann das Passwort JEDES Kontos neu setzen und sich danach einloggen.
    """
    benutzer = request.values.get("user", "")
    token = request.values.get("token", "")

    if not benutzer or token != reset_token(benutzer):
        return Response(
            "Ungültiger oder abgelaufener Zurücksetz-Token.",
            mimetype="text/plain",
            status=403,
        )

    if request.method == "POST":
        neues_pw = request.form.get("password", "")
        if not neues_pw:
            flash("Bitte ein neues Passwort angeben.")
            return render_template("passwort_neu.html", user=benutzer, token=token)

        db = get_db()
        cursor = db.cursor()
        try:
            # Hier bewusst parametrisiert – die Lücke ist der ratbare Token,
            # nicht eine SQL-Injection an dieser Stelle.
            cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (neues_pw, benutzer),
            )
            db.commit()
            flash(f"Passwort für {benutzer} wurde neu gesetzt. Du kannst dich jetzt einloggen.")
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler beim Zurücksetzen: {err}")
        finally:
            cursor.close()
            db.close()
        return redirect(url_for("login"))

    return render_template("passwort_neu.html", user=benutzer, token=token)


# ---------------------------------------------------------------------------
# "ANMELDEN ALS …" (Entwickler-/Admin-Hilfe – mit kaputter Zugriffskontrolle)
# ---------------------------------------------------------------------------
@app.route("/konto/wechseln")
def konto_wechseln():
    """Schlüpft in ein anderes Konto und stellt das Auth-Cookie darauf aus.

    !!! SCHWACHSTELLE 12: BROKEN ACCESS CONTROL / PRIVILEGE ESCALATION !!!
    Gedacht war diese "Entwickler-Hilfe" nur für Admins (zum Testen fremder
    Konten). Tatsächlich wird aber NUR geprüft, OB überhaupt jemand eingeloggt
    ist – nicht, ob die Person dazu berechtigt ist. Jede eingeloggte Person
    kann so per ?user=<name> in ein beliebiges fremdes Konto wechseln
    (z. B. ?user=admin) und ist danach vollständig diese Person.
    Richtig wäre eine echte Rollen-/Rechteprüfung (nur Admins, und auch die
    nur mit Protokollierung).
    """
    if not current_user():
        return redirect(url_for("login"))

    ziel = request.args.get("user", "")
    db = get_db()
    cursor = db.cursor(dictionary=True)
    # Parametrisiert: die Lücke ist die fehlende Rechteprüfung, nicht SQLi.
    cursor.execute("SELECT id, username FROM users WHERE username = %s", (ziel,))
    neuer_user = cursor.fetchone()
    cursor.close()
    db.close()

    if not neuer_user:
        flash(f"Konto „{ziel}“ nicht gefunden.")
        return redirect(url_for("dashboard"))

    flash(f"Du bist jetzt als {neuer_user['username']} angemeldet.")
    return login_user(redirect(url_for("dashboard")), neuer_user)


# ---------------------------------------------------------------------------
# DASHBOARD / ÜBERSICHT DER HONIGTÖPFE
# ---------------------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
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
        sql_tipp(query)
        honigtoepfe = []
    else:
        if not honigtoepfe and sieht_nach_sqli_aus(search):
            sql_tipp(query)

    cursor.close()
    attach_details(db, honigtoepfe)
    db.close()

    return render_template(
        "dashboard.html",
        honigtoepfe=honigtoepfe,
        username=user["username"],
        search=search,
    )


# ---------------------------------------------------------------------------
# EINZELNEN HONIGTOPF ANSEHEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/<topf_id>")
def honigtopf_detail(topf_id):
    if not current_user():
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
        sql_tipp(query)
        topf = None
    else:
        if not topf and not str(topf_id).isdigit():
            sql_tipp(query)

    if topf:
        attach_details(db, [topf])
    cursor.close()
    db.close()

    if not topf:
        g.flashes_out.insert(0, "Honigtopf nicht gefunden.")
        return redirect(url_for("dashboard"))

    return render_template("honigtopf_detail.html", topf=topf)


# ---------------------------------------------------------------------------
# NEUEN HONIGTOPF ANLEGEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/neu", methods=["GET", "POST"])
def new_honigtopf():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")
        sorte = request.form.get("sorte", "bluete")
        kategorie = request.form.get("kategorie", "wissen")
        if sorte not in SORTEN:
            sorte = "bluete"
        if kategorie not in KATEGORIEN:
            kategorie = "wissen"

        if not title or not content:
            flash("Bitte Titel und Inhalt ausfüllen.")
            return render_template("new_honigtopf.html")

        db = get_db()
        cursor = db.cursor()

        query = (
            f"INSERT INTO honigtoepfe (title, content, author_id) "
            f"VALUES ('{title}', '{content}', {user['user_id']})"
        )
        try:
            cursor.execute(query)
            # Sorte/Kategorie sicher (parametrisiert) in eigener Tabelle ablegen
            cursor.execute(
                "INSERT INTO honigtopf_details (topf_id, kategorie, sorte) VALUES (%s, %s, %s)",
                (cursor.lastrowid, kategorie, sorte),
            )
            db.commit()
            flash(f"Dein Glas {SORTEN[sorte]['name']} steht jetzt im Regal.")
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler: {err}")
            sql_tipp(query)
        finally:
            cursor.close()
            db.close()

        return redirect(url_for("dashboard"))

    return render_template("new_honigtopf.html")


# ---------------------------------------------------------------------------
# HONIGTOPF BEARBEITEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/<topf_id>/bearbeiten", methods=["GET", "POST"])
def edit_honigtopf(topf_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # !!! SCHWACHSTELLE 5: IDOR / Broken Access Control !!!
    # Es wird nur geprueft, OB jemand eingeloggt ist - nicht, ob der Beitrag
    # dieser Person gehoert (kein author_id-Vergleich). Jede eingeloggte Person
    # kann so JEDEN fremden Honigtopf bearbeiten, einfach ueber die ID in der URL:
    #   /honigtopf/1/bearbeiten
    # Die topf_id wird ausserdem (wie in SCHWACHSTELLE 3) unparametrisiert
    # in die Query gebaut -> zusaetzlich SQL-injizierbar.
    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")
        update_query = (
            f"UPDATE honigtoepfe SET title = '{title}', content = '{content}' "
            f"WHERE id = {topf_id}"
        )
        try:
            cursor.execute(update_query)
            db.commit()
            flash("Honigtopf aktualisiert.")
        except mysql.connector.Error as err:
            flash(f"Datenbankfehler beim Bearbeiten: {err}")
            sql_tipp(update_query)
        finally:
            cursor.close()
            db.close()
        return redirect(url_for("honigtopf_detail", topf_id=topf_id))

    select_query = f"SELECT id, title, content FROM honigtoepfe WHERE id = {topf_id}"
    try:
        cursor.execute(select_query)
        topf = cursor.fetchone()
    except mysql.connector.Error as err:
        flash(f"Datenbankfehler: {err}")
        sql_tipp(select_query)
        topf = None
    cursor.close()
    db.close()

    if not topf:
        return render_template("404.html"), 404
    return render_template("edit_honigtopf.html", topf=topf)


# ---------------------------------------------------------------------------
# HONIGTOPF LÖSCHEN
# ---------------------------------------------------------------------------
@app.route("/honigtopf/<topf_id>/loeschen", methods=["POST"])
def delete_honigtopf(topf_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    # !!! SCHWACHSTELLE 7: IDOR + fehlender CSRF-Schutz beim Löschen !!!
    # - Keine Eigentuemer-Pruefung: jede eingeloggte Person kann jeden Beitrag
    #   loeschen (nur die ID in der URL zaehlt).
    # - Kein CSRF-Token: ein fremdes Formular/Bild auf einer anderen Seite kann
    #   den POST im Namen einer eingeloggten Person ausloesen.
    db = get_db()
    cursor = db.cursor()
    query = f"DELETE FROM honigtopf_details WHERE topf_id = {topf_id}"
    try:
        cursor.execute(query)
        query = f"DELETE FROM honigtoepfe WHERE id = {topf_id}"
        cursor.execute(query)
        db.commit()
        flash("Honigtopf gelöscht.")
    except mysql.connector.Error as err:
        flash(f"Datenbankfehler beim Löschen: {err}")
        sql_tipp(query)
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# INSIDER: kleine Brotkrumen für neugierige Angreifer:innen
# (alles harmlos – nichts davon ist eine zusätzliche echte Schwachstelle)
# ---------------------------------------------------------------------------
@app.after_request
def bienen_header(response):
    # Wer die Response-Header anschaut, wird belohnt
    response.headers["X-Powered-By"] = "Bienenwachs & String-Concatenation"
    response.headers["X-Wachbienen"] = "Mittagspause"
    return response


# ---------------------------------------------------------------------------
# ETIKETTEN-DOWNLOAD (Glas-Etiketten als Textdatei)
# ---------------------------------------------------------------------------
ETIKETTEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etiketten")


@app.route("/etikett")
def etikett():
    if not current_user():
        return redirect(url_for("login"))

    # !!! SCHWACHSTELLE 10: Path Traversal !!!
    # Der Dateiname aus ?datei= wird ungeprueft an den Etiketten-Ordner
    # gehaengt. Mit ../ kann man aus dem Ordner ausbrechen und beliebige
    # Dateien des Servers lesen, z. B.:
    #   /etikett?datei=../app.py
    #   /etikett?datei=../schema.sql
    # Richtig waere: nur den Basisnamen zulassen (os.path.basename) und den
    # aufgeloesten Pfad gegen ETIKETTEN_DIR pruefen.
    datei = request.args.get("datei", "akazie.txt")
    pfad = os.path.join(ETIKETTEN_DIR, datei)
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            inhalt = f.read()
    except OSError as err:
        # Information Disclosure: Fehlertext (inkl. Pfad) wird roh ausgegeben.
        return Response(f"Konnte Etikett nicht laden: {err}", mimetype="text/plain", status=404)
    return Response(inhalt, mimetype="text/plain")


@app.route("/robots.txt")
def robots():
    text = (
        "# Liebe Crawler, bitte nicht in den Keller schauen. Danke!\n"
        "User-agent: *\n"
        "Disallow: /honigkeller\n"
        "Disallow: /konto/wechseln\n"
        "Disallow: /intern/\n"
        "\n"
        "# TODO(imker_tom): Die Königin will ihren Tresor nicht mehr in einer\n"
        "# Datenbanktabelle haben. Wer weiß schon, wie die heißt ...\n"
        "# TODO(imker_tom): /konto/wechseln ist nur unsere Dev-Hilfe zum\n"
        "# Testen fremder Konten - vor Go-Live hinter eine Admin-Prüfung legen!\n"
    )
    return Response(text, mimetype="text/plain")


@app.route("/honigkeller", methods=["GET", "POST"])
def honigkeller():
    """Ein Honeypot im HoneyPot: sieht aus wie ein geheimer Admin-Login,
    ist aber eine Falle. Es wird NICHTS gespeichert – die Seite zeigt nur,
    was ein echter Honeypot jetzt über den Angreifer protokollieren würde."""
    erwischt = None
    if request.method == "POST":
        erwischt = {
            "username": request.form.get("username", ""),
            "pw_laenge": len(request.form.get("password", "")),
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "unbekannt"),
        }
    return render_template("honigkeller.html", erwischt=erwischt)


# ---------------------------------------------------------------------------
# BIENENFOTOS: Upload und Import per URL
# ---------------------------------------------------------------------------
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_UPLOAD = 2 * 1024 * 1024  # 2 MB – schützt die Übungsrechner vor Riesen-Uploads
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD
BILD_ENDUNGEN = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def _sicherer_basisname(name):
    """Nur den Dateinamen ohne Ordner behalten.

    Das verhindert, dass Uploads AUSSERHALB von uploads/ landen (z. B. app.py
    überschreiben). Die eigentliche Lücke (keine Typprüfung) bleibt bestehen.
    """
    name = os.path.basename((name or "").replace("\\", "/"))
    if name in ("", ".", "..") or name.startswith("."):
        return None
    return name


@app.route("/fotos", methods=["GET", "POST"])
def fotos():
    if not current_user():
        return redirect(url_for("login"))

    if request.method == "POST":
        datei = request.files.get("foto")
        name = _sicherer_basisname(datei.filename if datei else "")
        if not name:
            flash("Bitte eine Datei auswählen.")
            return redirect(url_for("fotos"))

        # !!! SCHWACHSTELLE 13: UNRESTRICTED FILE UPLOAD !!!
        # Es wird weder die Dateiendung noch der Inhalt (MIME-Typ, Magic Bytes)
        # geprüft. Eine .html- oder .svg-Datei wird angenommen und später unter
        # /uploads/<name> vom GLEICHEN Ursprung wie die App ausgeliefert – mit
        # passendem Content-Type (text/html bzw. image/svg+xml). Enthaltenes
        # JavaScript läuft damit im App-Kontext und kann z. B. document.cookie
        # lesen (das auth-Cookie ist nicht HttpOnly, siehe SCHWACHSTELLE 8).
        # Richtig wäre: Endungs-Whitelist + Inhaltsprüfung, zufällige Dateinamen,
        # Auslieferung mit "Content-Disposition: attachment" oder von einer
        # separaten Domain, dazu "X-Content-Type-Options: nosniff".
        datei.save(os.path.join(UPLOAD_DIR, name))
        flash(f"„{name}“ wurde hochgeladen.")
        return redirect(url_for("fotos"))

    eintraege = [
        n for n in os.listdir(UPLOAD_DIR)
        if not n.startswith(".") and os.path.isfile(os.path.join(UPLOAD_DIR, n))
    ]
    eintraege.sort(key=lambda n: os.path.getmtime(os.path.join(UPLOAD_DIR, n)), reverse=True)
    dateien = [{"name": n, "bild": n.lower().endswith(BILD_ENDUNGEN)} for n in eintraege]
    return render_template("fotos.html", dateien=dateien)


@app.route("/uploads/<path:name>")
def upload_datei(name):
    # send_from_directory verhindert ../ – ausgeliefert wird aber mit dem
    # Content-Type, der zur Endung passt (.html -> text/html).
    return send_from_directory(UPLOAD_DIR, name)


@app.route("/fotos/import", methods=["POST"])
def foto_import():
    if not current_user():
        return redirect(url_for("login"))

    url = request.form.get("url", "").strip()
    if not url.lower().startswith(("http://", "https://")):
        flash("Bitte eine http(s)-Adresse angeben.")
        return redirect(url_for("fotos"))

    # !!! SCHWACHSTELLE 16: SERVER-SIDE REQUEST FORGERY (SSRF) !!!
    # Der SERVER ruft die angegebene URL selbst ab – ohne zu prüfen, wohin.
    # So erreicht man Adressen, die von außen gesperrt sind, z. B.
    #   http://127.0.0.1:5000/intern/bienenstock-status
    # Der interne Endpunkt glaubt, die Anfrage käme "von innen" (localhost),
    # und gibt sein Geheimnis heraus. Die Antwort wird als Datei gespeichert
    # und ist danach in der Galerie lesbar. Die rohen Fehlermeldungen verraten
    # zusätzlich, welche Hosts/Ports erreichbar sind (Port-Scan von innen).
    # Richtig wäre: Ziel-Host auflösen und interne/private Adressen sperren,
    # nur eine Whitelist erlaubter Hosts, keine Weiterleitungen folgen.
    try:
        with urllib.request.urlopen(url, timeout=5) as antwort:
            daten = antwort.read(MAX_UPLOAD + 1)
    except (urllib.error.URLError, ValueError, OSError) as err:
        flash(f"Import fehlgeschlagen: {err}")
        return redirect(url_for("fotos"))

    if len(daten) > MAX_UPLOAD:
        flash("Import abgebrochen: Datei ist größer als 2 MB.")
        return redirect(url_for("fotos"))

    name = _sicherer_basisname(urllib.parse.urlparse(url).path) or "import"
    if "." not in name:
        name += ".txt"
    name = "import_" + name
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f:
        f.write(daten)
    flash(f"Von {url} importiert als „{name}“.")
    return redirect(url_for("fotos"))


@app.route("/intern/bienenstock-status")
def intern_status():
    """Interner Status-Endpunkt – angeblich nur vom Server selbst erreichbar."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return Response(
            "403 – Dieser Endpunkt ist nur intern (vom Server selbst) erreichbar.",
            mimetype="text/plain",
            status=403,
        )
    text = (
        "Bienenstock-Status (intern)\n"
        "===========================\n"
        "Völker: 12 | Königinnen: 12 | Wachbienen: schlafen\n"
        "Wartungs-Flag: HONEY{d3r_s3rv3r_h0lt_s31n_31g3n3s_g3h31mn1s}\n"
    )
    return Response(text, mimetype="text/plain")


# ---------------------------------------------------------------------------
# ETIKETTEN-DESIGNER (eigenes Glas-Etikett gestalten)
# ---------------------------------------------------------------------------
app.config["ETIKETTEN_FLAG"] = "HONEY{t3mpl4t3s_s1nd_k31n_h0n1gl3ck3n}"
# Sandbox: verhindert Code-Ausführung auf den Übungsrechnern (kein RCE),
# erlaubt aber weiterhin das Auslesen aller übergebenen Variablen.
_etiketten_env = SandboxedEnvironment()


@app.route("/etikett/designer")
def etikett_designer():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    imkerei = request.args.get("imkerei", "")
    sorte = request.args.get("sorte", "akazie")
    if sorte not in SORTEN:
        sorte = "akazie"

    etikett = fehler = None
    if imkerei:
        # !!! SCHWACHSTELLE 15: SERVER-SIDE TEMPLATE INJECTION (SSTI) !!!
        # Der Name der Imkerei wird per String-Concatenation IN die Vorlage
        # geschrieben, statt als Variable übergeben zu werden. Jinja-Ausdrücke
        # in der Eingabe werden dadurch auf dem Server ausgewertet:
        #   {{ 7*7 }}   -> 49
        #   {{ config }} -> komplette App-Konfiguration inkl. SECRET_KEY & Flag
        # Richtig wäre: feste Vorlage, Eingabe nur als Variable übergeben:
        #   env.from_string("Abgefüllt von {{ imkerei }}").render(imkerei=imkerei)
        vorlage = (
            "{{ sorte }}\n"
            "aus eigener Imkerei\n"
            "Abgefüllt von: " + imkerei + "\n"
            "Ernte {{ jahr }} · 500 g"
        )
        try:
            etikett = _etiketten_env.from_string(vorlage).render(
                sorte=SORTEN[sorte]["name"], jahr=2026, config=app.config
            )
        except TemplateError as err:
            fehler = f"Vorlagenfehler: {err}"

    return render_template(
        "etikett_designer.html", imkerei=imkerei, sorte=sorte, etikett=etikett, fehler=fehler
    )


@app.errorhandler(404)
def leere_wabe(err):
    return render_template("404.html"), 404


@app.errorhandler(413)
def zu_gross(err):
    flash("Die Datei ist zu groß (maximal 2 MB).")
    return redirect(url_for("fotos"))


if __name__ == "__main__":
    # debug=True NUR für die Übungsumgebung! Niemals in Produktion.
    # Host/Port über Umgebungsvariablen änderbar, z. B.:
    #   $env:HOST = "0.0.0.0"; $env:PORT = "5006"; python app.py
    app.run(
        debug=True,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
    )
