# 🐝 HoneyPot – Challenge-Sammlung
`http://localhost:5000`.


---

## Challenge 1 — Anmelden ohne Benutzer und Passwort 🟢

Logge dich ein, ohne gültige Zugangsdaten zu kennen.
**Tipp:** Schreib ins Benutzerfeld `' OR 1=1 -- ` (Leerzeichen am Ende), Passwort egal.

---

## Challenge 2 — Als imker_tom anmelden – ohne Passwort 🟢

Übernimm gezielt das `imker_tom`-Konto, ohne das Passwort zu kennen.
**Tipp:** Benutzerfeld `imker_tom' -- ` (Leerzeichen am Ende), Passwort egal.

---

## Challenge 3 — Eigenen Code einschleusen (Stored XSS) 🟡

Lege einen Beitrag an, dessen Inhalt beim Öffnen **Code ausführt** (z. B. ein Pop-up).
**Tipp:** Der Inhalt wird als HTML gerendert. Probier ein `<script>`-Schnipsel –
aber ohne einfache Anführungszeichen (`'`), sonst bricht das Speichern ab.

---

## Challenge 4 — Passwörter über das Suchfeld abgreifen (UNION-SQLi) 🟡

Bring das Suchfeld im Dashboard dazu, Benutzernamen und Passwörter anzuzeigen.
**Tipp:** Mit `UNION SELECT` eigene Spalten „unterschieben" – die Suche hat
**3 Spalten**, deine Auswahl muss genauso viele haben. Payload mit `%'` beginnen,
mit `-- ` beenden.

---

## Challenge 5 — Fremde Dateien vom Server lesen (Path Traversal) 🟡

Der „Etikett"-Download liefert Dateien aus einem Ordner aus. Lies darüber eine
Datei, die dort **nicht** liegt (z. B. den Quellcode).
**Tipp:** Schau dir `/etikett?datei=akazie.txt` an. Wie kommst du mit `../` aus dem
Ordner heraus?

---

## Challenge 6 — Fremde Session übernehmen (Cookie Hijacking) 🟡

Das `auth`-Cookie ist signiert – aber mit einem schwachen Schlüssel, der im
Quellcode steht. Bau dir selbst ein gültiges Cookie und werde damit `admin`.
**Tipp:** Schlüssel und Salt findest du im Code (siehe Challenge 5). Mit
`itsdangerous` lässt sich ein eigenes Cookie signieren und im Browser setzen.

---

> **Ab hier: Partner-Modus.** Jede:r startet die App auf dem **eigenen** Rechner,
> der/die **Nachbar:in** greift diese Instanz an:
> ```powershell
> $env:HOST = "0.0.0.0"; .\venv\Scripts\python.exe app.py   # http://<deine-ip>:5000
> ```
> **Spielregeln:** Nur die eingeladene Instanz. Nur harmlose Payloads (`alert`).
> Kein DoS, keine echten Schad-Dateien, keine Massen-Uploads. Nur während des
> Übungstermins. Lösungsweg kurz dokumentieren.

## Challenge 7 — Datei wird zur Waffe (Unrestricted File Upload) 🟡

Unter **Fotos** kann man „Bienenfotos" hochladen. Lade eine Datei hoch, die beim
Öffnen JavaScript **im App-Kontext** ausführt und das `auth`-Cookie anzeigt.
**Tipp:** Prüft der Server wirklich, ob es ein Bild ist? Welcher `Content-Type`
kommt zurück, wenn du die hochgeladene Datei öffnest?

---

## Challenge 8 — Der Link, der zurückschlägt (Reflected XSS) 🟢

Bau einen **Link** zum Dashboard, der beim Anklicken ein Pop-up auslöst –
ohne dass etwas gespeichert wird.
**Tipp:** Schau dir an, wo dein Suchbegriff auf der Ergebnisseite wieder auftaucht.

---

## Challenge 9 — Das Etikett plaudert (Server-Side Template Injection) 🔴

Der **Etiketten-Designer** baut aus deinem Imkerei-Namen ein Etikett. Bring ihn
dazu, **auf dem Server zu rechnen** – und dann die geheime Konfiguration der App
inkl. Flag auszugeben.
**Tipp:** Die App ist in Flask/Jinja2 geschrieben. Was passiert mit `{{ 7*7 }}`?

---

## Challenge 10 — Der Server holt's dir (SSRF) 🔴

`/intern/bienenstock-status` ist von außen gesperrt (403). Lies trotzdem das
Wartungs-Flag aus.
**Tipp:** Unter **Fotos** kann der Server Bilder per Link selbst abholen. Von wo
aus kommt dann die Anfrage? (Ein Blick in `robots.txt` lohnt sich.)

---

