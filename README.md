# HoneyPot – Die Imker-Community

Eine bewusst unsicher programmierte Übungs-Webseite zum Training von SQL-Injection-Angriffen.
**Nur für den geschützten Kurs-/Lehrbetrieb bestimmt – niemals öffentlich deployen!**

Statt eines Ticketsystems ist HoneyPot eine kleine Community-Plattform für Imker:innen:
Nutzer registrieren sich, loggen sich ein und teilen "Honigtöpfe" (Tipps, Rezepte, Anleitungen
rund um Bienen & Honig). Der Begriff "HoneyPot" ist dabei bewusst doppeldeutig gewählt – in der
IT-Security bezeichnet ein "Honeypot" eine Lockfalle für Angreifer.

## Setup

### 1. MySQL-Datenbank einrichten
```bash
mysql -u root -p < schema.sql
```
Das legt die Datenbank `honeypot` mit den Tabellen `users` und `honigtoepfe` an und füllt sie
mit Beispieldaten (inkl. drei Test-Logins, siehe `schema.sql`).

### 2. Python-Umgebung vorbereiten
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Datenbank-Zugangsdaten setzen (optional, per Umgebungsvariable)
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=dein_passwort
export DB_NAME=honeypot
```
Ohne gesetzte Variablen greift die App auf `root` ohne Passwort zurück (siehe `app.py`).

### 4. App starten
```bash
python app.py
```
Die Seite läuft dann unter `http://localhost:5000`.

## Test-Logins (aus schema.sql)
| Benutzername | Passwort           |
|--------------|---------------------|
| admin        | bienenkoenigin99    |
| imker_tom    | waldhonig2024       |
| lisa_b       | summsumm            |

## Absichtliche Schwachstellen (für Trainer:innen)

Alle Schwachstellen sind durch String-Concatenation statt Prepared Statements entstanden –
der Klassiker bei SQL-Injections. Sie sind im Code mit `!!! SCHWACHSTELLE X !!!`-Kommentaren
markiert.

### 1. Login-Bypass (`/login`)
Die Query lautet intern sinngemäß:
```sql
SELECT * FROM users WHERE username = '<input>' AND password = '<input>'
```
**Beispiel-Payload** (Feld „Benutzername"): `admin' -- `
→ Der Passwort-Check wird durch den SQL-Kommentar `--` ausgehebelt, man wird als `admin` eingeloggt,
ganz ohne das echte Passwort zu kennen.

### 2. UNION-based Injection im Suchfeld (`/dashboard?q=...`)
```sql
SELECT id, title, created_at FROM honigtoepfe WHERE title LIKE '%<input>%' ORDER BY created_at DESC
```
**Beispiel-Payload**: `%' UNION SELECT id, username, password FROM users -- `
→ Zeigt in der Dashboard-Übersicht plötzlich Benutzernamen und Passwörter anstelle von Honigtopf-Titeln an.

### 3. Injection über die ID in der URL (`/honigtopf/<id>`)
```sql
SELECT ... FROM honigtoepfe JOIN users ... WHERE honigtoepfe.id = <input>
```
Da die ID ungeprüft eingebaut wird, kann man hier ebenfalls UNION-Angriffe fahren oder über
absichtlich provozierte Fehlermeldungen Informationen über die Tabellenstruktur gewinnen
(Error-based Injection), da DB-Fehler direkt angezeigt werden.

### 4. Schwachstelle in der Registrierung (`/register`)
Auch die Prüfung auf bereits vergebene Benutzernamen läuft über eine verwundbare Query –
guter Übungsfall, um zu zeigen, dass nicht nur Login-Formulare betroffen sein können.

### 5. Weitere bewusste Schwachpunkte
- Passwörter werden **im Klartext** gespeichert (kein Hashing, z. B. mit `bcrypt`/`werkzeug.security`)
- Datenbankfehler werden 1:1 an den Nutzer ausgegeben (Information Disclosure)
- `app.secret_key` ist hartcodiert und trivial
- `debug=True` ist aktiv (zeigt im Fehlerfall ganze Stacktraces)

## Nächste Schritte (für Aufgabe 3 / Absicherung)
Sobald die Injection-Übungen durchgeführt wurden, bietet sich als Folgeaufgabe an:
1. Alle Queries auf **Prepared Statements / Parametrisierung** umstellen (`cursor.execute(query, (param,))`)
2. Passwörter mit `werkzeug.security.generate_password_hash` / `check_password_hash` hashen
3. Eingaben serverseitig validieren (z. B. ID als `int` casten, Längen/Formate prüfen)
4. Generische Fehlermeldungen statt Rohdaten der DB-Exception anzeigen
5. `secret_key` aus Umgebungsvariable statt hartcodiert
6. `debug=False` für den produktiven Betrieb, dazu ein echter WSGI-Server (z. B. Gunicorn) + Prozessmanager

## Projektstruktur
```
honeypot/
├── app.py                      # Flask-App mit allen Routen (inkl. Schwachstellen)
├── schema.sql                  # Datenbankschema + Beispieldaten
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── honigtopf_detail.html
│   └── new_honigtopf.html
└── static/
    └── style.css
```
