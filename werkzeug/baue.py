#!/usr/bin/env python3
"""
baue.py - erzeugt aus konfig.json + aufgaben.json + inhalt/*.html die
fertigen statischen Seiten von MeinInfoKurs V3.

Das Ergebnis ist normales HTML. GitHub Pages braucht keinen Build-Schritt;
dieses Skript ist nur ein Geruestbauer, damit jede Seite gleich aussieht.
Einmal laufen lassen:   python3 werkzeug/baue.py
"""

import html
import json
import pathlib
import re
import sys
from datetime import date

WURZEL = pathlib.Path(__file__).resolve().parent.parent      # die Repo-Wurzel
WERK = WURZEL / "werkzeug"

KONFIG = json.loads((WERK / "konfig.json").read_text(encoding="utf-8"))
AUFGABEN = json.loads((WERK / "aufgaben.json").read_text(encoding="utf-8"))

BASIS = KONFIG["basis_url"].rstrip("/")
ADS = KONFIG["adsense"]
AUTOR = KONFIG["autor"]
NAME = KONFIG["seitenname"]

HALBJAHRE = {h["id"]: h for h in KONFIG["halbjahre"]}


# --------------------------------------------------------------------------- #
#  Hilfen
# --------------------------------------------------------------------------- #

def e(text):
    """HTML-Escape fuer Attribute und Text."""
    return html.escape(str(text), quote=True)


def pfad_hoch(tiefe):
    """'' fuer die Startseite, '../' pro Ebene darunter."""
    return "../" * tiefe


def aufgaben_von(halbjahr=None, bereich=None):
    treffer = [a for a in AUFGABEN
               if (halbjahr is None or a["halbjahr"] == halbjahr)
               and (bereich is None or a["bereich"] == bereich)]
    return sorted(treffer, key=lambda a: a.get("nr", 0))


# Die Kuerzel stammen aus der alten Java-Uebersicht ([K] Hello World ...)
KATEGORIE_MARKE = {
    "K": "Konsole", "G": "GUI", "A": "Array", "OOP": "OOP",
    "HTML": "HTML", "Nachschlagen": "Nachschlagen",
    "Algorithmen": "Algorithmus", "Datenbanken": "Datenbank",
    "Formale Sprachen": "Sprache", "": "Aufgabe",
}

STATUS_TEXT = {
    "verifiziert": ("ist-verifiziert", "fa-circle-check",
                    "Lösung geprüft"),
    "nicht-verifiziert": ("ist-nicht-verifiziert", "fa-triangle-exclamation",
                          "Noch nicht geprüft"),
    "fehler": ("ist-fehler", "fa-circle-exclamation",
               "Hier steckt noch ein Fehler drin"),
    "fehlt": ("ist-fehler", "fa-circle-question",
              "Aufgabenblatt fehlt"),
    "nachschlagen": ("ist-verifiziert", "fa-book",
                     "Zum Nachschlagen"),
}


# --------------------------------------------------------------------------- #
#  Kopf, Navigation, Fuss
# --------------------------------------------------------------------------- #

def kopf(*, titel, beschreibung, url, tiefe, og_bild, jsonld=None, extra_css=(),
         mit_diagrammen=False):
    b = pfad_hoch(tiefe)
    voller_titel = titel if titel == NAME else f"{NAME} | {titel}"

    css = "\n".join(
        f'    <link rel="stylesheet" href="{b}assets/{datei}">' for datei in
        ("stil.css", "prism-thema.css", *extra_css)
    )

    # mermaid ist knapp ein MB. Es wird nur auf den Seiten geladen, die
    # wirklich ein Diagramm haben - das sind keine 20 von 96.
    diagramm_skript = ""
    if mit_diagrammen:
        diagramm_skript = (
            '\n    <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/'
            '10.9.1/mermaid.min.js" defer></script>')

    jsonld_block = ""
    if jsonld:
        jsonld_block = ('\n    <script type="application/ld+json">\n'
                        + json.dumps(jsonld, ensure_ascii=False, indent=2)
                        + "\n    </script>")

    return f"""<!DOCTYPE html>
<html lang="de" data-basis="{b}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{e(voller_titel)}</title>
    <meta name="description" content="{e(beschreibung)}">
    <meta name="author" content="{e(AUTOR)}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{e(url)}">

    <meta property="og:site_name" content="{e(NAME)}">
    <meta property="og:locale" content="de_DE">
    <meta property="og:type" content="{'website' if tiefe == 0 else 'article'}">
    <meta property="og:title" content="{e(voller_titel)}">
    <meta property="og:description" content="{e(beschreibung)}">
    <meta property="og:url" content="{e(url)}">
    <meta property="og:image" content="{e(og_bild)}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:alt" content="{e(voller_titel)}">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{e(voller_titel)}">
    <meta name="twitter:description" content="{e(beschreibung)}">
    <meta name="twitter:image" content="{e(og_bild)}">

    <meta name="theme-color" content="#14151f">

    <link rel="icon" href="{b}assets/logo.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="{b}assets/logo.png">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
{css}

    <!-- Thema sofort setzen, sonst blitzt beim Laden das falsche auf -->
    <script>
        (function () {{
            try {{
                var t = JSON.parse(localStorage.getItem("thema"));
                if (!t) t = matchMedia("(prefers-color-scheme: light)").matches ? "hell" : "dunkel";
                document.documentElement.setAttribute("data-thema", t);
            }} catch (e) {{ document.documentElement.setAttribute("data-thema", "dunkel"); }}
        }})();
    </script>

    <!-- Werbung.
         Das AdSense-Skript wird nur geladen, wenn die Seite wirklich ueber
         http(s) ausgeliefert wird. Oeffnet man die Datei lokal per file://,
         haengt sich das Skript auf und die Seite laedt nie fertig
         ("Page Unresponsive"). In Produktion aendert die Pruefung nichts. -->
    <meta name="google-adsense-account" content="{ADS}">
    <script>
        if (location.protocol === "http:" || location.protocol === "https:") {{
            var werbeSkript = document.createElement("script");
            werbeSkript.async = true;
            werbeSkript.crossOrigin = "anonymous";
            werbeSkript.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS}";
            document.head.appendChild(werbeSkript);
        }}
    </script>{diagramm_skript}{jsonld_block}
</head>
<body>"""


def navigation(tiefe, aktiv):
    b = pfad_hoch(tiefe)
    teile = [
        f'        <a href="{b}index.html" class="nur-symbol"'
        f'{" aria-current=\"page\"" if aktiv == "start" else ""} aria-label="Startseite">'
        f'<i class="fa-solid fa-house" aria-hidden="true"></i></a>'
    ]
    for h in KONFIG["halbjahre"]:
        strom = ' aria-current="page"' if aktiv == h["id"] else ""
        teile.append(
            f'        <a href="{b}{h["id"]}/index.html"{strom}>'
            f'<span class="beschriftung">{e(h["kuerzel"])}</span></a>'
        )
    teile.append(
        f'        <a href="{b}info.html" class="nur-symbol"'
        f'{" aria-current=\"page\"" if aktiv == "info" else ""} aria-label="Info und Kontakt">'
        f'<i class="fa-solid fa-circle-info" aria-hidden="true"></i></a>'
    )
    return ('    <nav class="nav" aria-label="Hauptnavigation">\n'
            + "\n".join(teile) + "\n    </nav>\n")


def werkzeugleiste(mit_verlauf=True):
    verlauf = ""
    if mit_verlauf:
        verlauf = ('        <button type="button" id="verlauf-knopf" data-oeffnet="verlauf-fenster" '
                   'aria-label="Zuletzt angesehen">'
                   '<i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i></button>\n')
    suche = ('        <button type="button" id="suche-knopf" data-oeffnet="suche-fenster" '
             'aria-label="Aufgabe suchen">'
             '<i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i></button>\n')
    return ('    <div class="werkzeuge">\n'
            + suche
            + verlauf
            + '        <button type="button" id="thema-schalter" aria-label="Helles Design einschalten" aria-pressed="false">'
              '<i class="fa-solid fa-sun" aria-hidden="true"></i></button>\n'
            + '    </div>\n')


def dialoge(mit_verlauf=True, mit_werbung=True):
    teile = ["""    <dialog class="fenster fenster-suche" id="suche-fenster">
        <div class="fenster-kopf">
            <h2>Aufgabe suchen</h2>
            <button type="button" class="schliessen" data-schliesst aria-label="Schließen">&times;</button>
        </div>
        <div class="fenster-koerper">
            <input type="search" id="suche-feld" placeholder="Thema, Titel oder Stichwort"
                   autocomplete="off" spellcheck="false" aria-label="Suchbegriff">
            <p class="suche-hinweis" id="suche-hinweis">Tippe los. <kbd>Strg</kbd>+<kbd>K</kbd> öffnet die Suche von überall.</p>
            <ul id="suche-treffer" class="suche-treffer"></ul>
        </div>
    </dialog>
"""]
    if mit_verlauf:
        teile.append("""    <dialog class="fenster" id="verlauf-fenster">
        <div class="fenster-kopf">
            <h2>Zuletzt angesehen</h2>
            <button type="button" class="schliessen" data-schliesst aria-label="Schließen">&times;</button>
        </div>
        <div class="fenster-koerper">
            <ul id="verlauf-liste"></ul>
        </div>
    </dialog>
""")
    if mit_werbung:
        teile.append("""    <dialog class="fenster" id="werbe-fenster">
        <div class="fenster-kopf">
            <h2>Werbung <span id="werbe-uhr"></span></h2>
            <button type="button" class="schliessen" data-schliesst aria-label="Schließen" disabled>&times;</button>
        </div>
        <div class="fenster-koerper">
            <div class="eigenwerbung" id="werbe-inhalt"></div>
        </div>
    </dialog>
""")
    return "".join(teile)


def werbeplatz(name):
    """Ein Werbeplatz im Textfluss.

    Ohne echte Anzeigenblock-ID aus dem AdSense-Konto wird hier bewusst nichts
    ausgegeben: ein <ins> ohne gueltige data-ad-slot rendert nur einen leeren
    weissen Kasten. Die Auto-Ads aus dem Kopf-Skript funktionieren trotzdem.
    IDs eintragen in werkzeug/konfig.json unter "adsense_slots".
    """
    slot = KONFIG.get("adsense_slots", {}).get(name, "").strip()
    if not slot:
        return f"        <!-- Werbeplatz \"{name}\": noch keine Anzeigenblock-ID hinterlegt -->\n"
    return f"""        <aside class="werbeplatz" aria-label="Werbung">
            <ins class="adsbygoogle"
                 style="display:block"
                 data-ad-client="{ADS}"
                 data-ad-slot="{slot}"
                 data-ad-format="auto"
                 data-full-width-responsive="true"></ins>
            <script>if (window.adsbygoogle) {{ adsbygoogle.push({{}}); }}</script>
        </aside>
"""

def werbeschienen():
    """Die beiden senkrechten Schienen links und rechts vom Text.

    Sie stehen ausserhalb von <main>, damit sie nicht im Lesefluss landen und
    Screenreader sie nicht mitten im Text vorlesen. Das Stylesheet blendet sie
    unter 1400px Fensterbreite komplett aus - erst ab da bleibt neben der
    677px breiten Textspalte genug Platz fuer 160px Anzeige plus Luft. Auf dem
    Handy existieren sie damit gar nicht, also kein Layoutsprung.
    """
    teile = []
    for wo, name in (("links", "schiene_links"), ("rechts", "schiene_rechts")):
        slot = KONFIG.get("adsense_slots", {}).get(name, "").strip()
        if not slot:
            teile.append('    <!-- Werbeschiene %s: noch keine Anzeigenblock-ID hinterlegt -->\n' % wo)
            continue
        teile.append(
            '    <aside class="werbe-schiene %s" aria-label="Werbung" aria-hidden="true">\n'
            '        <ins class="adsbygoogle"\n'
            '             style="display:inline-block;width:160px;height:600px"\n'
            '             data-ad-client="%s"\n'
            '             data-ad-slot="%s"></ins>\n'
            '        <script>if (window.adsbygoogle) { adsbygoogle.push({}); }</script>\n'
            '    </aside>\n' % (wo, ADS, slot))
    return "".join(teile)


def mit_werbung_oben(inhalt):
    """Setzt den oberen Werbeplatz direkt hinter die Aufgabenstellung.

    Das ist die Stelle, die jeder Leser passiert: die Aufgabe hat er gelesen,
    die Loesung will er sehen. Findet sich kein Aufgabenkasten, kommt der Platz
    an den Anfang.
    """
    block = werbeplatz("oben")
    marke = '<div class="aufgabenstellung">'
    start = inhalt.find(marke)
    if start == -1:
        return block + inhalt
    # passendes </div> suchen, Verschachtelung mitzaehlen
    i, tiefe = start + len(marke), 1
    while tiefe and i < len(inhalt):
        auf, zu = inhalt.find("<div", i), inhalt.find("</div>", i)
        if zu == -1:
            return block + inhalt
        if auf != -1 and auf < zu:
            tiefe += 1
            i = auf + 4
        else:
            tiefe -= 1
            i = zu + 6
    return inhalt[:i] + "\n\n" + block + inhalt[i:]



def fuss(tiefe):
    b = pfad_hoch(tiefe)
    jahr = date.today().year
    return f"""    <footer class="fuss">
        <p>Die Aufgaben stammen aus dem Unterricht und wurden nicht von mir erstellt.
           Diese Seite gibt sie wieder und zeigt, wie man sie lösen kann.</p>
        <p>&copy; {jahr} {e(AUTOR)} &middot;
           <a href="{b}info.html">Info &amp; Kontakt</a> &middot;
           <a href="mailto:{KONFIG['email']}">{KONFIG['email']}</a></p>
    </footer>
    <script src="{b}assets/seite.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-markup.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-clike.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-java.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-markup-templating.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-php.min.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
#  Diagramme
#
#  Ein Diagramm ist eine ganz normale Markdown-Datei unter werkzeug/diagramme/,
#  genau so wie man sie in Obsidian schreiben wuerde:
#
#      # Die Klasse Auto als UML-Diagramm
#      Quelle: Q1.1.pdf S. 42
#
#      ```mermaid
#      classDiagram
#        class Auto { ... }
#      ```
#
#  Man kann den Ordner direkt als Obsidian-Vault oeffnen und sieht dort exakt
#  dasselbe Bild wie auf der Webseite. baue.py liest die Datei beim Bauen,
#  holt Ueberschrift, Quellenangabe und den mermaid-Block raus und setzt daraus
#  die fertige <figure>. Im Browser laeuft kein Markdown-Parser - das waere auf
#  einer statisch erzeugten Seite nur Ballast.
#
#  Eingebunden wird ein Diagramm im Inhaltsschnipsel mit einer leeren Huelle:
#      <div data-diagramm="uml-klasse-auto"></div>
# --------------------------------------------------------------------------- #

DIAGRAMME = WERK / "diagramme"
DIAGRAMM_MARKE = re.compile(r'[ \t]*<div data-diagramm="([a-z0-9-]+)"></div>')
ZAUN = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


def lies_diagramm(name):
    """Liest eine Diagramm-Markdown und gibt (titel, quelle, mermaid) zurueck."""
    datei = DIAGRAMME / f"{name}.md"
    if not datei.exists():
        sys.exit(f"FEHLER: Diagramm '{name}' gibt es nicht ({datei}).")
    roh = datei.read_text(encoding="utf-8")

    treffer = ZAUN.search(roh)
    if not treffer:
        sys.exit(f"FEHLER: In {datei.name} fehlt der ```mermaid-Block.")
    mermaid = treffer.group(1).rstrip()

    titel = quelle = ""
    for zeile in roh[:treffer.start()].splitlines():
        zeile = zeile.strip()
        if zeile.startswith("# ") and not titel:
            titel = zeile[2:].strip()
        elif zeile.lower().startswith("quelle:") and not quelle:
            quelle = zeile.split(":", 1)[1].strip()
    if not titel:
        sys.exit(f"FEHLER: In {datei.name} fehlt die Ueberschrift (# ...).")
    if not quelle:
        sys.exit(f"FEHLER: In {datei.name} fehlt die Zeile 'Quelle: ...'. "
                 f"Jedes Diagramm muss sagen, aus welcher PDF-Seite es stammt.")
    return titel, quelle, mermaid


def diagramm_html(name):
    # Die Quellenangabe wird gelesen (und ist Pflicht), aber NICHT angezeigt:
    # Leser der Webseite haben die OneNote-PDFs nicht, fuer die ist "Q1.1.pdf
    # S. 42" nur Rauschen. Sie steht in der .md, damit spaeter nachpruefbar
    # bleibt, dass das Diagramm aus dem Unterrichtsmaterial stammt.
    titel, _quelle, mermaid = lies_diagramm(name)
    # Die Quelle steht in data-quelle, weil mermaid beim Rendern den Inhalt des
    # <pre> durch das SVG ersetzt. Ohne die Kopie koennte man beim Themenwechsel
    # nicht neu zeichnen.
    return (
        '        <figure class="diagramm">\n'
        '            <div class="diagramm-huelle">\n'
        f'                <pre class="mermaid" data-quelle="{e(mermaid)}">{e(mermaid)}</pre>\n'
        '            </div>\n'
        f'            <figcaption>{e(titel)}</figcaption>\n'
        '        </figure>\n')


def setze_diagramme(inhalt):
    """Ersetzt alle <div data-diagramm="..."></div> durch die fertige figure.

    Gibt (inhalt, anzahl) zurueck - die Anzahl entscheidet, ob die Seite
    ueberhaupt das mermaid-Skript laden muss.
    """
    gefunden = []

    def ersetze(m):
        gefunden.append(m.group(1))
        return diagramm_html(m.group(1))

    return DIAGRAMM_MARKE.sub(ersetze, inhalt), len(gefunden)


# --------------------------------------------------------------------------- #
#  Aufgabenseite
# --------------------------------------------------------------------------- #

def aufgabe_url(a):
    return f"{BASIS}/{a['halbjahr']}/{a['bereich']}/{a['id']}.html"


def aufgabe_datei(a):
    return WURZEL / a["halbjahr"] / a["bereich"] / f"{a['id']}.html"


def baue_aufgabe(a):
    hj = HALBJAHRE[a["halbjahr"]]
    bereich = next(x for x in hj["bereiche"] if x["id"] == a["bereich"])
    tiefe = 2
    b = pfad_hoch(tiefe)
    url = aufgabe_url(a)

    fragment = WERK / "inhalt" / f"{a['id']}.html"
    if not fragment.exists():
        print(f"  ! kein Inhalt fuer {a['id']} - uebersprungen")
        return None
    inhalt = fragment.read_text(encoding="utf-8").rstrip()
    inhalt, anzahl_diagramme = setze_diagramme(inhalt)

    klasse, symbol, status_text = STATUS_TEXT.get(
        a.get("status", "nicht-verifiziert"), STATUS_TEXT["nicht-verifiziert"])

    geschwister = aufgaben_von(a["halbjahr"], a["bereich"])
    i = geschwister.index(a)
    vorher = geschwister[i - 1] if i > 0 else None
    nachher = geschwister[i + 1] if i + 1 < len(geschwister) else None

    blaettern = []
    if vorher:
        blaettern.append(
            f'            <a class="zurueck" href="{vorher["id"]}.html">'
            f'<small>Vorherige Aufgabe</small>{e(vorher["titel"])}</a>')
    if nachher:
        blaettern.append(
            f'            <a class="weiter" href="{nachher["id"]}.html">'
            f'<small>Nächste Aufgabe</small>{e(nachher["titel"])}</a>')
    blaettern_block = ""
    if blaettern:
        blaettern_block = ('        <nav class="blaettern" aria-label="Weitere Aufgaben">\n'
                           + "\n".join(blaettern) + "\n        </nav>\n")

    jsonld = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": a["titel"],
        "description": a["kurz"],
        "url": url,
        "inLanguage": "de",
        "learningResourceType": "Aufgabe mit Lösung",
        "educationalLevel": f"{hj['name']} – {hj['zusatz']}",
        "about": bereich["name"],
        "author": {"@type": "Person", "name": AUTOR},
        "publisher": {"@type": "Person", "name": AUTOR},
        "isPartOf": {"@type": "Course", "name": f"{NAME} – {hj['name']}",
                     "url": f"{BASIS}/{hj['id']}/"},
        "isBasedOn": a.get("quelle", ""),
        "license": f"{BASIS}/info.html",
    }

    seite = kopf(titel=a["titel"], beschreibung=a["kurz"], url=url,
                 tiefe=tiefe, og_bild=f"{BASIS}/assets/og/{hj['id']}.png",
                 jsonld=jsonld, mit_diagrammen=anzahl_diagramme > 0)
    seite += navigation(tiefe, hj["id"])
    seite += werkzeugleiste()
    seite += f"""
    <main class="seite">
        <p class="brotkrumen">
            <a href="{b}{hj['id']}/index.html">{e(hj['name'])}</a>
            <span aria-hidden="true">/</span>
            <a href="{b}{hj['id']}/index.html#{e(bereich['id'])}">{e(bereich['name'])}</a>
        </p>
        <h1 class="titel">{e(a['titel'])}</h1>
        <p class="status {klasse}">
            <i class="fa-solid {symbol}" aria-hidden="true"></i>{e(status_text)}
        </p>

{mit_werbung_oben(inhalt)}

{werbeplatz("unten")}
{blaettern_block}    </main>

{werbeschienen()}{dialoge()}"""
    seite += fuss(tiefe)
    return seite


def baue_platzhalter(a):
    """Seite fuer eine Aufgabe, die es noch nicht gibt.

    Besser als ein toter Link: der Leser landet auf einer ehrlichen Notiz statt
    auf einer 404. noindex, damit Google die duenne Seite nicht aufnimmt.
    """
    hj = HALBJAHRE[a["halbjahr"]]
    bereich = next(x for x in hj["bereiche"] if x["id"] == a["bereich"])
    tiefe = 2
    b = pfad_hoch(tiefe)

    seite = kopf(titel=a["titel"], beschreibung=a["kurz"], url=aufgabe_url(a),
                 tiefe=tiefe, og_bild=f"{BASIS}/assets/og/{hj['id']}.png")
    seite = seite.replace('<meta name="robots" content="index, follow">',
                          '<meta name="robots" content="noindex, follow">')
    seite += navigation(tiefe, hj["id"])
    seite += werkzeugleiste()
    seite += f"""
    <main class="seite" data-verlauf="nein">
        <p class="brotkrumen">
            <a href="{b}{hj['id']}/index.html">{e(hj['name'])}</a>
            <span aria-hidden="true">/</span>
            <a href="{b}{hj['id']}/index.html#{e(bereich['id'])}">{e(bereich['name'])}</a>
        </p>
        <h1 class="titel">{e(a['titel'])}</h1>
        <p class="status ist-nicht-verifiziert">
            <i class="fa-solid fa-hourglass-half" aria-hidden="true"></i>Kommt noch
        </p>

        <p>Diese Aufgabe steht zwar auf der Liste, aber eine Lösung dazu gibt es
           hier noch nicht. Ich trage sie nach, sobald ich dazu komme.</p>

        <p>Wenn du sie selbst schon gelöst hast und deine Lösung hier stehen
           soll, schreib mir gerne: <a href="mailto:{KONFIG['email']}">{KONFIG['email']}</a></p>

        <p><a href="{b}{hj['id']}/index.html">Zurück zur Übersicht</a></p>
    </main>

{dialoge(mit_verlauf=True, mit_werbung=False)}"""
    seite += fuss(tiefe)
    return seite


# --------------------------------------------------------------------------- #
#  Uebersichten
# --------------------------------------------------------------------------- #

def baue_halbjahr(hj):
    tiefe = 1
    url = f"{BASIS}/{hj['id']}/"
    seite = kopf(titel=f"{hj['name']} – {hj['bereiche'][0]['name'] if len(hj['bereiche']) == 1 else 'Übersicht'}",
                 beschreibung=hj["beschreibung"], url=url, tiefe=tiefe,
                 og_bild=f"{BASIS}/assets/og/{hj['id']}.png",
                 jsonld={
                     "@context": "https://schema.org",
                     "@type": "Course",
                     "name": f"{NAME} – {hj['name']}",
                     "description": hj["beschreibung"],
                     "url": url,
                     "inLanguage": "de",
                     "provider": {"@type": "Person", "name": AUTOR},
                 })
    seite += navigation(tiefe, hj["id"])
    seite += werkzeugleiste()
    seite += f"""
    <main class="seite weit" data-verlauf="nein">
        <p class="brotkrumen">{e(hj['zusatz'])}</p>
        <h1 class="titel">{e(hj['name'])}</h1>
        <p>{e(hj['beschreibung'])}</p>
"""
    for bereich in hj["bereiche"]:
        liste = aufgaben_von(hj["id"], bereich["id"])
        seite += f'\n        <h2 id="{e(bereich["id"])}">{e(bereich["name"])}</h2>\n'
        if not liste:
            seite += ('        <p class="hinweis"><i class="fa-solid fa-hourglass-half" aria-hidden="true"></i>'
                      ' Hier ist noch nichts. Kommt bald!</p>\n')
            continue
        seite += '        <div class="raster">\n'
        for a in liste:
            klassen = "karte" + (" kommt-noch" if a.get("status") == "geplant" else "")
            ziel = f'{bereich["id"]}/{a["id"]}.html'
            seite += f"""            <a class="{klassen}" href="{ziel}">
                <span class="marke">{e(KATEGORIE_MARKE.get(a.get('kategorie', ''), 'Aufgabe'))} {a.get('nr', '')}</span>
                <span class="name">{e(a['titel'])}</span>
                <span class="zusatz">{e(a['kurz'])}</span>
            </a>
"""
        seite += "        </div>\n"

    seite += f"\n{werbeplatz('unten')}    </main>\n\n{dialoge()}"
    seite += fuss(tiefe)
    return seite


def baue_start():
    tiefe = 0
    url = f"{BASIS}/"
    besch = ("Alle Aufgaben aus dem Informatik-Unterricht – mit Lösung und einer "
             "Erklärung, die auch wirklich erklärt. Von der E-Phase bis Q3.")
    seite = kopf(titel=NAME, beschreibung=besch, url=url, tiefe=tiefe,
                 og_bild=f"{BASIS}/assets/og/start.png",
                 jsonld={
                     "@context": "https://schema.org",
                     "@type": "WebSite",
                     "name": NAME,
                     "description": besch,
                     "url": url,
                     "inLanguage": "de",
                     "author": {"@type": "Person", "name": AUTOR},
                 })
    seite += navigation(tiefe, "start")
    seite += werkzeugleiste()

    karten = ""
    for h in KONFIG["halbjahre"]:
        anzahl = len(aufgaben_von(h["id"]))
        zusatz = f"{anzahl} Aufgabe{'n' if anzahl != 1 else ''}" if anzahl else "kommt bald"
        karten += f"""            <a class="karte" href="{h['id']}/index.html">
                <span class="kuerzel">{e(h['kuerzel'])}</span>
                <span class="name">{e(h['zusatz'])}</span>
                <span class="zusatz">{e(zusatz)}</span>
            </a>
"""

    seite += f"""
    <main class="seite weit" data-verlauf="nein">
        <h1 class="titel">MeinInfoKurs</h1>
        <p>Hier findest du die Aufgaben aus unserem Info-Kurs – jede mit fertiger
           Lösung und einer Erklärung, wie man da hinkommt. Such dir das Halbjahr
           aus, in dem ihr gerade seid.</p>

        <div class="raster halbjahre">
{karten}        </div>

{werbeplatz("unten")}
        <h2>Wie das hier gedacht ist</h2>
        <p>Jede Aufgabe hat die gleiche Struktur: oben die Aufgabenstellung, dann
           die fertige Lösung zum Aufdecken, und darunter Schritt für Schritt,
           warum sie so aussieht wie sie aussieht. Der Code lässt sich kopieren
           und herunterladen.</p>
        <p>Abschreiben bringt dir in der Klausur nichts. Lies die Erklärung.</p>
    </main>

{dialoge()}"""
    seite += fuss(tiefe)
    return seite


def baue_info():
    tiefe = 0
    url = f"{BASIS}/info.html"
    besch = "Kontakt, Hinweise und Rechtliches zu MeinInfoKurs."
    seite = kopf(titel="Info & Kontakt", beschreibung=besch, url=url, tiefe=tiefe,
                 og_bild=f"{BASIS}/assets/og/start.png")
    seite += navigation(tiefe, "info")
    seite += werkzeugleiste(mit_verlauf=False)   # info.html hat keinen Verlaufs-Dialog
    seite += f"""
    <main class="seite" data-verlauf="nein">
        <h1 class="titel">Info &amp; Kontakt</h1>

        <h2>Hilfe</h2>
        <p>Hast du Schwierigkeiten mit der Seite, oder ist dir ein Fehler in einer
           Lösung aufgefallen? Schreib mir, ich helfe gerne.</p>
        <p><a href="mailto:{KONFIG['email']}">{KONFIG['email']}</a></p>
        <p>Fehler im Code oder auf der Seite kannst du auch direkt über
           <a href="https://github.com/David-cmrg/MeinInfoKurs/issues/new" target="_blank" rel="noopener">GitHub</a>
           oder das <a href="https://forms.gle/3oMjzmyj9pixUfJx6" target="_blank" rel="noopener">Formular</a> melden.</p>

        <h2>Zu den Aufgaben</h2>
        <p>Die Aufgaben hier stammen aus dem Unterricht und wurden nicht von mir
           erstellt. Diese Seite gibt sie wieder, damit man nachvollziehen kann,
           wie eine Lösung zustande kommt. Die Lösungen sind meine eigenen. Ich
           kann nicht garantieren, dass alles richtig ist – wo ich mir nicht
           sicher war, steht das oben auf der Seite dran.</p>

        <h2>Werbung</h2>
        <p>Die Seite finanziert sich über Werbung. Wenn du selbst hier werben
           möchtest, schreib mir einfach.</p>

        <h2>Dateien</h2>
        <p>Meine bearbeiteten Dateien aus der E-Phase liegen im Ordner
           <code>Dateien/</code> – die Java-Programme zum Herunterladen.</p>

{werbeplatz("unten")}    </main>

{dialoge(mit_verlauf=False)}"""
    seite += fuss(tiefe)
    return seite


# --------------------------------------------------------------------------- #
#  Sitemap / robots
# --------------------------------------------------------------------------- #

def baue_suchindex():
    """Der Index fuer die Suche.

    Wird beim Bauen mit erzeugt und liegt als eine JSON-Datei neben dem
    Stylesheet. Das Skript laedt sie erst, wenn jemand die Suche oeffnet - wer
    nie sucht, laedt sie nie.

    Gesucht wird ueber Titel, Kurzbeschreibung, Halbjahr, Bereich, Kategorie und
    den Text der Aufgabenstellung. Der Rest der Seite bleibt draussen: sonst
    findet man bei "String" saemtliche Java-Aufgaben.
    """
    eintraege = []
    for a in AUFGABEN:
        if a.get("status") == "geplant":
            continue
        hj = HALBJAHRE[a["halbjahr"]]
        bereich = next(x for x in hj["bereiche"] if x["id"] == a["bereich"])

        stellung = ""
        quelle = WERK / "inhalt" / f"{a['id']}.html"
        if quelle.exists():
            roh = quelle.read_text(encoding="utf-8")
            start = roh.find('<div class="aufgabenstellung">')
            if start != -1:
                ende = roh.find("</div>", start)
                stellung = re.sub(r"<[^>]+>", " ", roh[start:ende])
                stellung = html.unescape(stellung)
                stellung = re.sub(r"\s+", " ", stellung).strip()[:400]

        eintraege.append({
            "t": a["titel"],
            "k": a["kurz"],
            "u": aufgabe_url(a).replace(BASIS + "/", ""),
            "h": hj["kuerzel"],
            "b": bereich["name"],
            "a": stellung,
        })
    return json.dumps(eintraege, ensure_ascii=False, separators=(",", ":")) + "\n"


def baue_sitemap():
    heute = date.today().isoformat()
    urls = [f"{BASIS}/", f"{BASIS}/info.html"]
    # Halbjahre ohne veroeffentlichte Aufgabe sind duenne Seiten - nicht anmelden
    urls += [f"{BASIS}/{h['id']}/" for h in KONFIG["halbjahre"]
             if any(a.get("status") != "geplant" for a in aufgaben_von(h["id"]))]
    urls += [aufgabe_url(a) for a in AUFGABEN if a.get("status") != "geplant"]

    zeilen = "\n".join(
        f"    <url><loc>{u}</loc><lastmod>{heute}</lastmod>"
        f"<changefreq>monthly</changefreq>"
        f"<priority>{'1.0' if u == BASIS + '/' else '0.8'}</priority></url>"
        for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{zeilen}\n</urlset>\n")


# --------------------------------------------------------------------------- #

def baue_robots():
    """robots.txt.

    Die liest ein Crawler nur im Domain-Root. Frueher lag die Seite unter
    david-cmrg.github.io/MeinInfoKurs/V3/ - da waere eine Datei hier wirkungslos
    gewesen. Seit die eigene Domain (CNAME) draufzeigt, IST die Repo-Wurzel die
    Domain-Wurzel, also gehoert sie hierher.
    """
    return ("User-agent: *\n"
            "Allow: /\n"
            "\n"
            "# Die Werkzeuge sind Quellcode, keine Seiten.\n"
            "Disallow: /werkzeug/\n"
            "\n"
            f"Sitemap: {BASIS}/sitemap.xml\n")


def baue_ads():
    """ads.txt.

    Ohne sie stuft AdSense das Inventar als "unauthorized" ein und ein Teil der
    Bieter steigt aus. Gleiche Regel wie bei robots.txt: nur im Domain-Root
    wirksam, und der ist seit dem CNAME genau hier.
    """
    return f"google.com, {ADS.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n"


def schreib(pfad, text):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")
    print(f"  {pfad.relative_to(WURZEL)}")


def pruefe_eindeutig():
    """Zwei Aufgaben duerfen nicht in dieselbe Datei schreiben."""
    gesehen = {}
    for a in AUFGABEN:
        ziel = aufgabe_datei(a)
        if ziel in gesehen:
            sys.exit(f"FEHLER: '{a['id']}' und '{gesehen[ziel]}' schreiben beide "
                     f"nach {ziel.relative_to(WURZEL)}. IDs muessen je Bereich "
                     f"eindeutig sein.")
        gesehen[ziel] = a["id"]


def main():
    pruefe_eindeutig()
    print("Baue MeinInfoKurs V3 ...")
    schreib(WURZEL / "index.html", baue_start())
    schreib(WURZEL / "info.html", baue_info())

    for h in KONFIG["halbjahre"]:
        schreib(WURZEL / h["id"] / "index.html", baue_halbjahr(h))

    gebaut = geplant = 0
    for a in AUFGABEN:
        if a.get("status") == "geplant":
            schreib(aufgabe_datei(a), baue_platzhalter(a))
            geplant += 1
            continue
        seite = baue_aufgabe(a)
        if seite:
            schreib(aufgabe_datei(a), seite)
            gebaut += 1

    schreib(WURZEL / "assets" / "suchindex.json", baue_suchindex())
    schreib(WURZEL / "sitemap.xml", baue_sitemap())
    schreib(WURZEL / "robots.txt", baue_robots())
    schreib(WURZEL / "ads.txt", baue_ads())
    print(f"\nFertig. {gebaut} Aufgabenseiten, {geplant} Platzhalter, "
          f"{len(KONFIG['halbjahre'])} Übersichten.")


if __name__ == "__main__":
    main()
