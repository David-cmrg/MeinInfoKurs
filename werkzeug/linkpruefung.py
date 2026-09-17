#!/usr/bin/env python3
"""
linkpruefung.py - prueft alle internen Links und Dateiverweise.
    python3 werkzeug/linkpruefung.py            (nur SEITE)
    python3 werkzeug/linkpruefung.py --alles    (ganzes Repo, also auch V1/V2)
"""
import pathlib, re, sys
from urllib.parse import unquote, urldefrag

# Seit die Seite an der Repo-Wurzel liegt, sind Seitenwurzel und Repo dasselbe.
# Die Archive V1/V2 liegen mit drin, werden aber nur mit --alles mitgeprueft:
# V2 hat bekannte tote Links, die dort so bleiben sollen.
WURZEL = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = {"V1", "V2", "Archiv"}
MIT_ARCHIV = "--alles" in sys.argv

MUSTER = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"', re.I)
EXTERN = re.compile(r'^(https?:|mailto:|tel:|data:|javascript:)', re.I)

fehler, geprueft, dateien = [], 0, 0

for seite in sorted(WURZEL.rglob("*.html")):
    if any(t in seite.parts for t in ("werkzeug", "node_modules")):
        continue
    if not MIT_ARCHIV and ARCHIVE & set(seite.parts):
        continue
    dateien += 1
    text = seite.read_text(encoding="utf-8", errors="replace")
    # In <pre>-Bloecken steht Beispielcode. Ein dort escaptes
    # &lt;a href="logout.php"&gt; ist kein Link der Seite, sondern Text.
    durchsuchbar = re.sub(r"<pre\b.*?</pre>", "", text, flags=re.S | re.I)
    for roh in MUSTER.findall(durchsuchbar):
        ziel = roh.strip()
        if not ziel or ziel == "#" or EXTERN.match(ziel):
            continue
        geprueft += 1
        pfad = unquote(urldefrag(ziel)[0])
        if not pfad:
            anker = urldefrag(ziel)[1]
            if anker and f'id="{anker}"' not in durchsuchbar:
                fehler.append((seite, ziel, "Anker auf dieser Seite existiert nicht"))
            continue
        if pfad.startswith("/"):
            # Seit dem CNAME (meininfokurs.cmrg.site) ist die Repo-Wurzel die
            # Domain-Wurzel, absolute Pfade stimmen also. Vorher, unter
            # david-cmrg.github.io/MeinInfoKurs/V3/, waeren sie kaputt gewesen.
            aufgeloest = (WURZEL / pfad.lstrip("/")).resolve()
        else:
            aufgeloest = (seite.parent / pfad).resolve()
        if aufgeloest.is_dir():
            aufgeloest = aufgeloest / "index.html"
        if not aufgeloest.exists():
            fehler.append((seite, ziel, "Ziel existiert nicht"))
            continue

        # Auch den Anker pruefen - ein Link auf #gibtsnicht ist genauso kaputt
        anker = urldefrag(ziel)[1]
        if anker and aufgeloest.suffix == ".html":
            ziel_text = aufgeloest.read_text(encoding="utf-8", errors="replace")
            if (f'id="{anker}"' not in ziel_text
                    and f"id='{anker}'" not in ziel_text
                    and f'name="{anker}"' not in ziel_text):
                fehler.append((seite, ziel, "Anker existiert nicht"))

print(f"{geprueft} interne Verweise in "
      f"{dateien} Dateien geprueft.\n")
if not fehler:
    print("Alles in Ordnung - keine toten Links.")
else:
    print(f"{len(fehler)} Problem(e):\n")
    for seite, ziel, grund in fehler:
        try:
            wo = seite.relative_to(WURZEL)
        except ValueError:
            wo = seite
        print(f"  {wo}\n      -> {ziel}   ({grund})")
sys.exit(1 if fehler else 0)
