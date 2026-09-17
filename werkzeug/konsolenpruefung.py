#!/usr/bin/env python3
"""Laedt jede ausgelieferte V3-Seite in einem headless Chrome und meldet
Konsolenfehler. Startet sich den lokalen Server selbst.

    python3 werkzeug/konsolenpruefung.py          # alle Seiten
    python3 werkzeug/konsolenpruefung.py q2       # nur ein Halbjahr

Gemeldet werden nur echte Fehler der Seite. Ignoriert werden Meldungen von
AdSense/Font Awesome (externe Dienste, im Netz manchmal blockiert) und die
uebliche favicon-Warnung.
"""
import http.server, os, re, socketserver, subprocess, sys, tempfile, threading, shutil

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = WURZEL   # Seite und Repo sind dasselbe
CHROME = shutil.which("google-chrome") or shutil.which("chromium")

# externe Dienste, die uns nicht gehoeren
EGAL = re.compile(r"googlesyndication|googletagservices|doubleclick|adsbygoogle|"
                  r"fontawesome|cdnjs\.cloudflare\.com|favicon|ERR_BLOCKED_BY_CLIENT|"
                  r"ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED")
KONSOLE = re.compile(r"CONSOLE\(\d+\)\] \"(.*?)\", source: (\S+)")


def seiten(filter_=""):
    for ordner, _, dateien in os.walk(WURZEL):
        # V2 ist ein eingefrorenes Archiv mit bekannt kaputtem script.js
        if any(x in ordner for x in ("werkzeug", "Dateien", "/V2", "/V1", "/Archiv")):
            continue
        for d in sorted(dateien):
            if d.endswith(".html"):
                p = os.path.relpath(os.path.join(ordner, d), REPO)
                if not filter_ or f"/{filter_}/" in "/" + p:
                    yield p


def main():
    if not CHROME:
        sys.exit("Kein Chrome gefunden.")
    filter_ = sys.argv[1] if len(sys.argv) > 1 else ""
    liste = list(seiten(filter_))

    os.chdir(REPO)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **k: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        beanstandet = 0
        with tempfile.TemporaryDirectory() as profil:
            for p in liste:
                ergebnis = subprocess.run(
                    [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                     f"--user-data-dir={profil}", "--enable-logging=stderr", "--v=0",
                     "--virtual-time-budget=4000", "--dump-dom",
                     f"http://127.0.0.1:{port}/{p}"],
                    capture_output=True, text=True, timeout=60)
                for zeile in ergebnis.stderr.splitlines():
                    if "CONSOLE" not in zeile or EGAL.search(zeile):
                        continue
                    if ":ERROR:" not in zeile and "Uncaught" not in zeile:
                        continue
                    m = KONSOLE.search(zeile)
                    print(f"{p}: {m.group(1) if m else zeile.strip()}")
                    beanstandet += 1
        srv.shutdown()

    print(f"\n{len(liste)} Seiten geladen.")
    print("Keine Konsolenfehler." if not beanstandet
          else f"{beanstandet} Konsolenfehler.")
    return 1 if beanstandet else 0


if __name__ == "__main__":
    sys.exit(main())
