#!/usr/bin/env python3
"""Prueft jede Diagramm-Markdown unter werkzeug/diagramme/.

    python3 werkzeug/diagrammpruefung.py

Geprueft wird zweierlei:
  1. Aufbau der Datei - Ueberschrift, Quellenangabe, genau ein mermaid-Block
  2. Syntax - der Block laeuft durch mermaid.parse() in einem headless Chrome

Warum ein eigenes Werkzeug: konsolenpruefung.py wirft alle Meldungen weg, deren
Quelle cdnjs ist. Mermaid-Parserfehler kommen genau von dort - ein kaputtes
Diagramm wuerde dort also als "keine Konsolenfehler" durchgehen.
"""
import http.server, json, os, pathlib, re, shutil, socketserver, subprocess, sys, tempfile, threading

WURZEL = pathlib.Path(__file__).resolve().parent.parent
DIAGRAMME = WURZEL / "werkzeug" / "diagramme"
INHALT = WURZEL / "werkzeug" / "inhalt"
CHROME = shutil.which("google-chrome") or shutil.which("chromium")
ZAUN = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)

PRUEFSEITE = """<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"></script>
</head><body><script>
var quellen = %s;
mermaid.initialize({startOnLoad:false, securityLevel:"strict"});
Promise.all(Object.keys(quellen).map(function (name) {
  return mermaid.parse(quellen[name])
    .then(function () { return [name, null]; })
    .catch(function (e) { return [name, String(e && e.message || e).slice(0, 300)]; });
})).then(function (paare) {
  var raus = {};
  paare.forEach(function (p) { if (p[1]) raus[p[0]] = p[1]; });
  document.body.setAttribute("data-ergebnis", JSON.stringify(raus));
});
</script></body></html>"""


def lies_alle():
    """Aufbau pruefen und die mermaid-Quellen einsammeln."""
    quellen, maengel = {}, []
    for datei in sorted(DIAGRAMME.glob("*.md")):
        if datei.name == "README.md":   # Doku des Ordners, kein Diagramm
            continue
        roh = datei.read_text(encoding="utf-8")
        bloecke = ZAUN.findall(roh)
        if len(bloecke) != 1:
            maengel.append((datei.name, f"{len(bloecke)} mermaid-Bloecke, genau einer gehoert da rein"))
            continue
        kopf = roh[:ZAUN.search(roh).start()]
        if not re.search(r"^# \S", kopf, re.M):
            maengel.append((datei.name, "keine Ueberschrift (# ...) - die wird zur Bildunterschrift"))
        if not re.search(r"^Quelle:\s*\S", kopf, re.M | re.I):
            maengel.append((datei.name, "keine Zeile 'Quelle: ...' - jedes Diagramm muss seine PDF-Seite nennen"))
        quellen[datei.stem] = bloecke[0].rstrip()
    return quellen, maengel


def unbenutzt(quellen):
    """Diagramme, die in keinem Inhaltsschnipsel eingebunden sind."""
    benutzt = set()
    for datei in INHALT.glob("*.html"):
        benutzt |= set(re.findall(r'data-diagramm="([a-z0-9-]+)"', datei.read_text(encoding="utf-8")))
    return sorted(set(quellen) - benutzt), sorted(benutzt - set(quellen))


def syntax_pruefen(quellen):
    if not CHROME:
        sys.exit("Kein Chrome gefunden - Syntaxpruefung nicht moeglich.")
    with tempfile.TemporaryDirectory() as ordner:
        seite = pathlib.Path(ordner) / "pruefung.html"
        seite.write_text(PRUEFSEITE % json.dumps(quellen, ensure_ascii=False), encoding="utf-8")
        os.chdir(ordner)
        h = http.server.SimpleHTTPRequestHandler
        h.log_message = lambda *a, **k: None
        with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            r = subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                 f"--user-data-dir={ordner}/profil", "--virtual-time-budget=20000",
                 "--dump-dom", f"http://127.0.0.1:{port}/pruefung.html"],
                capture_output=True, text=True, timeout=180)
            srv.shutdown()
    treffer = re.search(r'data-ergebnis="([^"]*)"', r.stdout)
    if not treffer:
        sys.exit("Die Syntaxpruefung hat nicht geantwortet (mermaid nicht geladen?).")
    import html as H
    return json.loads(H.unescape(treffer.group(1)) or "{}")


def main():
    quellen, maengel = lies_alle()
    if not quellen and not maengel:
        print("Keine Diagramme vorhanden.")
        return 0

    ohne_seite, ohne_datei = unbenutzt(quellen)
    fehler = syntax_pruefen(quellen) if quellen else {}

    for name, grund in maengel:
        print(f"  AUFBAU   {name}: {grund}")
    for name, grund in sorted(fehler.items()):
        print(f"  SYNTAX   {name}.md: {grund}")
    for name in ohne_datei:
        print(f"  FEHLT    {name}.md wird eingebunden, gibt es aber nicht")
    for name in ohne_seite:
        print(f"  UNGENUTZT {name}.md steht in keinem Inhaltsschnipsel")

    print(f"\n{len(quellen)} Diagramme geprueft.")
    schwer = len(maengel) + len(fehler) + len(ohne_datei)
    if schwer:
        print(f"{schwer} Beanstandung(en).")
        return 1
    print("Alle Diagramme in Ordnung."
          + (f" ({len(ohne_seite)} noch nicht eingebunden)" if ohne_seite else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
