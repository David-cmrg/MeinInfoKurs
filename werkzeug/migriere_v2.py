#!/usr/bin/env python3
"""
migriere_v2.py - holt die Aufgabenseiten aus V2 nach V3.

Texte und Loesungen bleiben WORTWOERTLICH. Geaendert wird nur die Huelle:
  * das von Hand getippte Syntax-Highlighting (<span class="keyword">...)
    wird zu reinem Text in <pre><code class="language-java"> - Prism macht
    die Farben jetzt selbst
  * die alten Bausteine werden auf die V3-Klassen abgebildet
  * Navigation, Modale, Werbung, Inline-Skripte fliegen raus (macht V3 zentral)

    python3 werkzeug/migriere_v2.py
danach:
    python3 werkzeug/baue.py
"""

import json
import pathlib
import re
import sys
import textwrap
import unicodedata

from bs4 import BeautifulSoup, Comment, NavigableString

V3 = pathlib.Path(__file__).resolve().parent.parent
V2 = V3.parent / "V2" / "Seiten"
WERK = V3 / "werkzeug"
INHALT = WERK / "inhalt"

# Seiten, die keine Aufgaben sind. docs/fehlersuche wandern als Nachschlage-
# seiten mit, weil etliche Aufgaben darauf verlinken (docs.html#Datentyp).
KEINE_AUFGABE = {"Java.html", "html.html", "Python.html", "support.html"}
# Gehoert inhaltlich zu Q1, nicht zur E-Phase:
NACH_Q1 = {"Autohaus.html", "OOP-Einstieg.html", "Geometrische-Figuren.html"}

UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}


def slug(text):
    for a, b in UMLAUTE.items():
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text


# --------------------------------------------------------------------------- #
#  Code aus den V2-Spans zurueck in reinen Text
# --------------------------------------------------------------------------- #

# Fehler im V2-Quelltext, die den Code nicht kompilieren lassen.
# Jeweils mit Begruendung, damit spaeter nachvollziehbar ist warum.
CODE_REPARATUR = {
    "Fahrscheinautomat.html": [
        # Die aeussere if-Abfrage wurde zu frueh geschlossen. David schreibt
        # vier Zeilen weiter selbst: "Am Ende dieses IFs Statements kommt keine
        # schliessende Klammer hin." Das } widerspricht seinem eigenen
        # Kommentar und macht den Code unkompilierbar (eine } zu viel).
        ('System.out.print("Rückgabe: ");\n          } // end of if\n',
         'System.out.print("Rückgabe: ");\n'),
    ],
}


def code_text(code_el):
    """Holt den Quelltext aus einem <code>, egal wie viele <span> drinstecken."""
    roh = code_el.get_text()
    roh = roh.replace(" ", " ").replace("​", "")
    zeilen = [z.rstrip() for z in roh.split("\n")]
    while zeilen and not zeilen[0].strip():
        zeilen.pop(0)
    while zeilen and not zeilen[-1].strip():
        zeilen.pop()
    if not zeilen:
        return ""
    # Die Einrueckung stammt aus der HTML-Quelle, nicht aus dem Programm.
    # Die kleinste vorkommende Einrueckung ist also die "Nullposition".
    zeilen = [z.expandtabs(4) for z in zeilen]
    tiefen = [len(z) - len(z.lstrip(" ")) for z in zeilen if z.strip()]
    ab = min(tiefen) if tiefen else 0
    return "\n".join(z[ab:] if z.strip() else "" for z in zeilen).rstrip()


SPRACHE_ZU_PRISM = {
    "java": "java", "html": "markup", "css": "css", "sql": "sql",
    "php": "php", "konsole": None, "ausgabe": None, "text": None,
}


def neuer_codeblock(soup, *, quelltext, beschriftung, sprache, datei=None, verdeckt=False):
    """Baut den V3-Codeblock."""
    huelle = soup.new_tag("div", attrs={"class": "code"})

    if beschriftung or datei:
        leiste = soup.new_tag("div", attrs={"class": "code-leiste"})
        span = soup.new_tag("span", attrs={"class": "code-sprache"})
        symbol = soup.new_tag("i", attrs={
            "class": "fa-solid fa-terminal" if sprache is None else "fa-solid fa-code",
            "aria-hidden": "true"})
        span.append(symbol)
        span.append(NavigableString(" " + (beschriftung or "Code")))
        leiste.append(span)
        if datei:
            knoepfe = soup.new_tag("div", attrs={"class": "code-knoepfe"})
            k1 = soup.new_tag("button", attrs={"type": "button", "class": "knopf",
                                               "data-kopieren": ""})
            k1.string = "Kopieren"
            k2 = soup.new_tag("button", attrs={"type": "button", "class": "knopf",
                                               "data-datei": datei})
            k2.string = "Herunterladen"
            knoepfe.append(k1); knoepfe.append(k2)
            leiste.append(knoepfe)
        huelle.append(leiste)

    if datei:   # nur die eigentliche Loesung bekommt ein Wasserzeichen
        wz = soup.new_tag("span", attrs={"class": "wz"})
        wz.string = "/* MeinInfoKurs.github.io */"
        huelle.append(wz)

    feld = soup.new_tag("div", attrs={"class": "code-feld verdeckt" if verdeckt else "code-feld"})
    if verdeckt:
        knopf = soup.new_tag("button", attrs={"type": "button", "class": "aufdecken"})
        innen = soup.new_tag("span"); innen.string = "Lösung anzeigen"
        knopf.append(innen)
        feld.append(knopf)

    pre = soup.new_tag("pre")
    code = soup.new_tag("code")
    if sprache:
        code["class"] = f"language-{sprache}"
    code.string = quelltext
    pre.append(code)
    feld.append(pre)
    huelle.append(feld)
    return huelle


# --------------------------------------------------------------------------- #
#  Eine Seite umbauen
# --------------------------------------------------------------------------- #

def status_lesen(main):
    el = main.find(id="code-status-display")
    if el is not None:
        klassen = el.get("class", [])
        if "verifiziert" in klassen and "nicht-verifiziert" not in klassen:
            return "verifiziert"
        if "nicht-verifiziert" in klassen:
            return "nicht-verifiziert"
        if "fehler" in klassen:
            return "fehler"
    if main.find(id="ChatSVG") is not None:
        return "nicht-verifiziert"
    # Fragenseiten tragen den Marker nicht oben, sondern an jeder Antwort
    haken = main.select(".antwort")
    if haken and all(el.find_previous(class_="verifiziert") is not None for el in haken):
        return "verifiziert"
    return "nicht-verifiziert"


# In V2 stand auf der Wassergebuehren-Seite der Dateiname der Bahnreise -
# ein Copy-Paste-Fehler. Wer das herunterlaedt, speichert die Loesung unter
# dem falschen Klassennamen und wundert sich, warum Java meckert.
DATEINAME_REPARATUR = {"Wassergebuehren.html": "Wassergebuehren.java"}


def dateiname_lesen(roh, pfad=None):
    if pfad is not None and pfad.name in DATEINAME_REPARATUR:
        return DATEINAME_REPARATUR[pfad.name]
    m = re.search(r"a\.download\s*=\s*['\"]([^'\"]+)['\"]", roh)
    return m.group(1) if m else None


def umbauen(pfad):
    roh = pfad.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(roh, "lxml")
    main = soup.find("main")
    if main is None:
        return None

    titel_el = main.find(id="titlePage")
    titel = titel_el.get_text(" ", strip=True) if titel_el else pfad.stem
    status = status_lesen(main)
    datei = dateiname_lesen(roh, pfad)

    # --- Huelle wegwerfen, die V3 zentral stellt ---------------------------- #
    for kommentar in main.find_all(string=lambda t: isinstance(t, Comment)):
        kommentar.extract()
    for wahl in ("#nav-title-verifystatus", "#toggle-history", "#history-modal",
                 "#ad-modal", "#warning-bar", ".vorherige-naechste", "#titlePage",
                 "#code-status-display", "#ChatSVG", "script", "noscript"):
        for el in main.select(wahl):
            el.decompose()

    # --- Codebloecke -------------------------------------------------------- #
    for cc in main.select(".code-container"):
        code_el = cc.find("code")
        if code_el is None:
            cc.decompose()
            continue
        quelltext = code_text(code_el)
        if not quelltext or quelltext.strip() in ("X", "x", "TODO", "..."):
            cc.decompose()      # leeres Geruest aus V2, kein Inhalt
            continue

        leiste = cc.find(class_="toolbar")
        beschriftung = None
        if leiste is not None:
            span = leiste.find("span")
            if span is not None:
                beschriftung = span.get_text(" ", strip=True) or None

        ist_loesung = code_el.get("id") == "codeBlock" or cc.find(class_="show-button") is not None
        sprache = "java"
        if beschriftung:
            sprache = SPRACHE_ZU_PRISM.get(beschriftung.strip().lower(), "java")
        if "html" in pfad.parts[-2].lower():
            sprache = "markup" if sprache == "java" else sprache

        for suchen, ersetzen in CODE_REPARATUR.get(pfad.name, []):
            if suchen in quelltext:
                quelltext = quelltext.replace(suchen, ersetzen)

        neu = neuer_codeblock(
            soup,
            quelltext=quelltext,
            beschriftung=beschriftung,
            sprache=sprache,
            datei=datei if ist_loesung and datei else None,
            verdeckt=ist_loesung,
        )
        cc.replace_with(neu)

    # --- Aufgabenstellung --------------------------------------------------- #
    for el in main.select(".Aufgabenstellung"):
        neu = soup.new_tag("div", attrs={"class": "aufgabenstellung"})
        marke = soup.new_tag("span", attrs={"class": "marke"})
        marke.string = "Die Aufgabenstellung lautet"
        neu.append(marke)
        p = soup.new_tag("p")
        for kind in list(el.contents):
            p.append(kind.extract())
        neu.append(p)
        el.replace_with(neu)

    # Die Ankuendigung steht bei vielen Seiten im Absatz davor - die waere
    # jetzt doppelt, weil der Kasten sie selbst als Marke traegt.
    for kasten in main.select(".aufgabenstellung"):
        vorher = kasten.find_previous_sibling()
        if vorher is None:
            continue
        for stueck in vorher.find_all(string=True):
            neu = re.sub(r"\s*Die Aufgabenstellung lautet:?\s*$", "", str(stueck))
            if neu != str(stueck):
                stueck.replace_with(neu)

    # --- Ueberschriften und Listen ------------------------------------------ #
    for el in main.select("#Lösungsprozess, #L\\00f6sungsprozess"):
        el.attrs.pop("id", None)
        el.string = "Lösungsprozess der Aufgabe"
    for el in main.find_all(["h2", "h3"]):
        if el.get_text(strip=True).rstrip(":") == "Lösungsprozess der Aufgabe":
            el.name = "h2"
            el.attrs.pop("id", None)
            el.string = "Lösungsprozess der Aufgabe"

    for el in main.select(".SchritteListe"):
        el["class"] = ["schritte"]
    for el in main.select(".Schritte"):
        el.name = "h3"
        el["class"] = ["schritt-titel"]

    # --- Fragen / Antworten ------------------------------------------------- #
    for liste in main.select("#Fragen"):
        neu = soup.new_tag("ol", attrs={"class": "frageliste"})
        aktuell = None
        for kind in list(liste.children):
            if isinstance(kind, NavigableString):
                continue
            if kind.name == "li":
                aktuell = soup.new_tag("li")
                p = soup.new_tag("p", attrs={"class": "frage"})
                stark = kind.find("strong")
                quelle = stark if stark is not None else kind
                for teil in list(quelle.contents):
                    p.append(teil.extract())
                aktuell.append(p)
                neu.append(aktuell)
            elif kind.name == "div" and aktuell is not None:
                antwort = kind.find(class_="antwort")
                if antwort is not None:
                    antwort.attrs.pop("onclick", None)
                    antwort["class"] = ["antwort"]
                    antwort["tabindex"] = "0"
                    antwort["role"] = "button"
                    aktuell.append(antwort.extract())
        liste.replace_with(neu)

    for el in main.select(".antwort"):
        el.attrs.pop("onclick", None)
        el.attrs.setdefault("tabindex", "0")
        el.attrs.setdefault("role", "button")

    # --- Kleinkram ----------------------------------------------------------- #
    # Token-Klassen ausserhalb von <pre>: die hat David benutzt, um einzelne
    # Woerter im Fliesstext hervorzuheben ("<span class='keyword'>While</span>
    # heisst auf Deutsch ..."). In V3 faerbt Prism nur noch echten Code, also
    # wird daraus das, was es eigentlich ist: Inline-Code.
    TOKEN = ("keyword", "class-name", "method", "type", "string", "comment",
             "gui", "number", "literal", "andererCode")
    for name in TOKEN:
        for el in main.select(f"span.{name}"):
            if el.find_parent("pre") is not None:
                continue
            el.name = "code"
            el.attrs.pop("class", None)

    for el in main.select(".TastenKombination"):
        el.name = "kbd"
        el.attrs.pop("class", None)
    for tab in main.find_all("table"):
        huelle = soup.new_tag("div", attrs={"class": "tabelle-huelle"})
        tab.wrap(huelle)
    for bild in main.find_all("img"):
        src = bild.get("src", "")
        if src and not src.startswith(("http", "../../assets")):
            bild["src"] = "../../assets/bilder/" + src.rsplit("/", 1)[-1]
        bild.attrs.setdefault("loading", "lazy")
        bild.attrs.setdefault("alt", "")
    # Verweise, die schon in V2 ins Leere zeigten
    REPARATUR = {
        "../Java-Docs.html#eva": "docs.html#Eingabe-Ausgabe",
        "Java-Docs.html#eva": "docs.html#Eingabe-Ausgabe",
        # Diese Anker gab es in docs.html noch nie - der Verweis landet jetzt
        # wenigstens auf der richtigen Seite statt im Nichts.
        "docs.html#if-statement": "docs.html",
        "docs.html#if-else-statement": "docs.html",
        "docs.html#IfElse": "docs.html",
        "docs.html#bedingungen": "docs.html",
    }
    for a in main.find_all("a", href=True):
        h = a["href"]
        if h in REPARATUR:
            a["href"] = REPARATUR[h]
            continue
        if h.endswith(".html") and "/" not in h:
            a["href"] = slug(h[:-5]) + ".html"
    for el in main.select(".button, .show-button, .toolbar, .buttons, .container"):
        if el.name and not el.select(".code"):
            el.unwrap() if el.name == "div" else el.decompose()

    # --- "X"-Platzhalter aus V2 ---------------------------------------------- #
    # Auf ein paar Seiten stehen als Erklaerung nur einzelne "X" - die hat David
    # als Geruest getippt und nie ausgefuellt. Auf der Webseite sieht das aus
    # wie ein Fehler. Also raus damit und stattdessen ehrlich hinschreiben,
    # dass die Erklaerung fehlt. Die Loesung darueber bleibt natuerlich stehen.
    platzhalter = 0
    for el in main.find_all(["p", "h2", "h3", "h4", "li"]):
        if el.find_parent("pre") is not None:
            continue
        if " ".join(el.get_text(" ", strip=True).split()) in ("X", "x"):
            el.decompose()
            platzhalter += 1
    for leer in main.find_all(["ol", "ul", "div"]):
        if leer.get("class") and "code" in leer.get("class"):
            continue
        if not leer.get_text(strip=True) and not leer.find(["img", "pre", "iframe"]):
            leer.decompose()

    if platzhalter:
        hinweis = soup.new_tag("p", attrs={"class": "hinweis"})
        symbol = soup.new_tag("i", attrs={"class": "fa-solid fa-pen-ruler",
                                          "aria-hidden": "true"})
        hinweis.append(symbol)
        hinweis.append(NavigableString(
            " Die Lösung steht oben, die Schritt-für-Schritt-Erklärung dazu "
            "fehlt hier aber noch. Die schreibe ich nach."))
        main.append(hinweis)

    # --- ausgeben ------------------------------------------------------------ #
    # Wichtig: KEIN prettify() und keine nachtraegliche Einrueckung des ganzen
    # Textes - beides wuerde den Inhalt von <pre> umformatieren und damit den
    # Quelltext zerschiessen. Nur die oberste Ebene bekommt eine Einrueckung,
    # und zwar ausschliesslich vor dem oeffnenden Tag.
    teile = []
    for kind in main.children:
        if isinstance(kind, Comment):
            continue
        if isinstance(kind, NavigableString):
            if kind.strip():
                teile.append("        " + kind.strip())
            continue
        teile.append("        " + str(kind))
    text = "\n".join(teile)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Manche V2-Seiten waren nie fertig ("Bitte warten Sie auf erstellung der
    # Seite."). Die uebernehmen wir nicht als Aufgabe, sondern als Platzhalter.
    nur_text = " ".join(BeautifulSoup(text, "lxml").get_text(" ", strip=True).split())
    leer = (re.search(r"[Bb]itte warten Sie auf erstellung", nur_text) is not None
            or len(nur_text) < 120)

    return {"titel": titel, "status": "geplant" if leer else status,
            "datei": datei, "inhalt": text.rstrip(), "leer": leer}


# --------------------------------------------------------------------------- #
#  Reihenfolge und Kategorien aus der alten Java-Uebersicht
# --------------------------------------------------------------------------- #

def v2_reihenfolge(index_datei, ordner):
    """Liest die Kachel-Reihenfolge aus einer alten Uebersichtsseite."""
    soup = BeautifulSoup(index_datei.read_text(encoding="utf-8", errors="replace"), "lxml")
    raus = []
    for a in soup.select(".aufgaben-section a[href]"):
        h4 = a.find("h4")
        if h4 is None:
            continue
        beschriftung = h4.get_text(" ", strip=True)
        m = re.match(r"\[(\w+)\]\s*(.*)", beschriftung)
        kategorie, name = (m.group(1), m.group(2)) if m else ("", beschriftung)
        raus.append({
            "html": a["href"],
            "titel": name,
            "kategorie": kategorie,
            "datei": ordner / a["href"],
        })
    return raus


def kurzfassung(inhalt_html, ersatz, titel=""):
    """Kurztext fuer Karte, <meta description> und og:description.

    Nimmt Davids eigene Worte, wirft aber den immer gleichen Auftakt
    ("Die Aufgabe der heutigen Stunde ist X!") weg - der steht sonst auf
    jeder einzelnen Karte und frisst die ganze Zeile.
    """
    soup = BeautifulSoup(inhalt_html, "lxml")

    # Floskeln, die auf fast jeder Seite stehen und nichts ueber die Aufgabe sagen
    FLOSKELN = (
        r"^Die Aufgabe der heutigen Stunde (ist|sind)\s*",
        r"^Dazu schauen wir uns (mal )?die Aufgabe (genauer )?an[^.!?]*[.!?]\s*",
        r"^Die Aufgabenstellung lautet:?\s*",
        r"^Naja, reden wir nicht so viel[^.!?]*[.!?]\s*",
        r"^In der Aufgabenstellung wird gefordert[^.!?]*[.!?:]\s*",
    )

    def entfloskeln(text):
        vorher = None
        while vorher != text:
            vorher = text
            for muster in FLOSKELN:
                text = re.sub(muster, "", text, flags=re.I)
            if titel:
                text = re.sub(r"^(die |das |der )?" + re.escape(titel) + r"[!.:,]?\s*",
                              "", text, flags=re.I)
            text = re.sub(r"^(mit\s+)?[A-ZÄÖÜ][^!.?]{0,45}[!]\s+(?=[A-ZÄÖÜ])", "", text)
            text = text.strip()
        return text

    # Kandidaten in der Reihenfolge, in der sie am meisten aussagen
    kandidaten = []
    for p in soup.find_all("p"):
        klassen = p.get("class") or []
        if "hinweis" in klassen:          # unser eigener Nachtrag, kein Inhalt
            continue
        if p.find_parent("li") and "frage" not in klassen:
            continue
        kandidaten.append(" ".join(p.get_text(" ", strip=True).split()))

    geputzte = [entfloskeln(k) for k in kandidaten]
    roh = next((g for g in geputzte if len(g) >= 45), "")
    if not roh and geputzte:
        roh = max(geputzte, key=len)          # der laengste ist immer noch der beste
    if not roh:
        return ersatz

    roh = roh[0].upper() + roh[1:]
    # "Ist ein standart Programm..." - da fehlt vorne der Titel, den wir
    # gerade weggeschnitten haben
    if titel and re.match(r"^(Ist|Sind|War|Waren)\s", roh):
        roh = f"{titel} {roh[0].lower()}{roh[1:]}"

    # moeglichst an einer Satzgrenze aufhoeren
    saetze = re.split(r"(?<=[.!?])\s+", roh)
    text = ""
    for satz in saetze:
        if text and len(text) + len(satz) > 165:
            break
        text = (text + " " + satz).strip()
        if len(text) >= 80:
            break
    if not text:
        text = roh
    if len(text) > 185:
        text = text[:185].rsplit(" ", 1)[0].rstrip(" ,;:") + " …"
    return text


KATEGORIE_NAME = {
    "K": "Konsole", "G": "GUI", "A": "Arrays", "OOP": "OOP", "": "Aufgabe",
}


def main():
    INHALT.mkdir(parents=True, exist_ok=True)
    aufgaben = json.loads((WERK / "aufgaben.json").read_text(encoding="utf-8"))
    vorhanden = {a["id"] for a in aufgaben}

    neu, fehlend, uebersprungen = [], [], []
    nr = 0

    for eintrag in v2_reihenfolge(V2 / "Java" / "Java.html", V2 / "Java"):
        html = eintrag["html"]
        if html in KEINE_AUFGABE:
            continue
        if html in NACH_Q1:
            uebersprungen.append((html, "gehört zu Q1, wird dort gebaut"))
            continue

        nr += 1
        kennung = slug(pathlib.Path(html).stem)

        if not eintrag["datei"].exists():
            fehlend.append(eintrag["titel"])
            neu.append({
                "id": kennung, "halbjahr": "e", "bereich": "java", "nr": nr,
                "titel": eintrag["titel"],
                "kurz": f"{KATEGORIE_NAME.get(eintrag['kategorie'], 'Aufgabe')} – "
                        f"diese Seite gab es in V2 noch nicht.",
                "quelle": "Informatik E-Phase",
                "status": "geplant", "sprache": "java",
                "kategorie": eintrag["kategorie"],
            })
            continue

        ergebnis = umbauen(eintrag["datei"])
        if ergebnis is None:
            uebersprungen.append((html, "kein <main> gefunden"))
            continue

        if ergebnis.get("leer"):
            fehlend.append(eintrag["titel"] + " (V2-Seite war leer)")
            neu.append({
                "id": kennung, "halbjahr": "e", "bereich": "java", "nr": nr,
                "titel": ergebnis["titel"] or eintrag["titel"],
                "kurz": f"{KATEGORIE_NAME.get(eintrag['kategorie'], 'Aufgabe')} – "
                        f"die Lösung fehlt hier noch.",
                "quelle": "Informatik E-Phase",
                "status": "geplant", "sprache": "java",
                "kategorie": eintrag["kategorie"],
            })
            continue

        (INHALT / f"{kennung}.html").write_text(ergebnis["inhalt"] + "\n", encoding="utf-8")
        neu.append({
            "id": kennung, "halbjahr": "e", "bereich": "java", "nr": nr,
            "titel": ergebnis["titel"] or eintrag["titel"],
            "kurz": kurzfassung(ergebnis["inhalt"], eintrag["titel"], ergebnis["titel"] or eintrag["titel"]),
            "quelle": f"Informatik E-Phase · übernommen aus V2/Seiten/Java/{html}",
            "status": ergebnis["status"],
            "sprache": "java",
            "kategorie": eintrag["kategorie"],
        })

    # Nachschlagewerke - keine Aufgaben, aber etliche Seiten verlinken darauf
    for html, titel in (("docs.html", "Java Nachschlagewerk"),
                        ("fehlersuche.html", "Fehler in Java")):
        pfad = V2 / "Java" / html
        if not pfad.exists():
            continue
        ergebnis = umbauen(pfad)
        if ergebnis is None:
            continue
        nr += 1
        kennung = slug(pathlib.Path(html).stem)
        (INHALT / f"{kennung}.html").write_text(ergebnis["inhalt"] + "\n", encoding="utf-8")
        neu.append({
            "id": kennung, "halbjahr": "e", "bereich": "java", "nr": nr,
            "titel": ergebnis["titel"] or titel,
            "kurz": kurzfassung(ergebnis["inhalt"], titel, ergebnis["titel"] or titel),
            "quelle": f"Informatik E-Phase · übernommen aus V2/Seiten/Java/{html}",
            "status": "nachschlagen", "sprache": "java",
            "kategorie": "Nachschlagen",
        })

    # HTML-Bereich
    pfad = V2 / "HTML" / "Grundgeruest.html"
    if pfad.exists():
        ergebnis = umbauen(pfad)
        if ergebnis:
            kennung = slug("Grundgeruest")
            (INHALT / f"{kennung}.html").write_text(ergebnis["inhalt"] + "\n", encoding="utf-8")
            neu.append({
                "id": kennung, "halbjahr": "e", "bereich": "html", "nr": 1,
                "titel": ergebnis["titel"] or "Das Grundgerüst",
                "kurz": kurzfassung(ergebnis["inhalt"], "Das HTML-Grundgerüst", ergebnis["titel"] or ""),
                "quelle": "Informatik E-Phase · übernommen aus V2/Seiten/HTML/Grundgeruest.html",
                "status": ergebnis["status"], "sprache": "html", "kategorie": "HTML",
            })

    behalten = [a for a in aufgaben if a["halbjahr"] != "e"]
    alle = behalten + [a for a in neu if a["id"] not in vorhanden or a["halbjahr"] == "e"]
    (WERK / "aufgaben.json").write_text(
        json.dumps(alle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gebaut = len([a for a in neu if a["status"] != "geplant"])
    print(f"{gebaut} Seiten übernommen, {len(fehlend)} als \"geplant\" vorgemerkt.")
    if fehlend:
        print("\nGab es in V2 nicht (jetzt ehrlich als 'kommt noch' markiert):")
        for t in fehlend:
            print(f"  - {t}")
    if uebersprungen:
        print("\nÜbersprungen:")
        for h, grund in uebersprungen:
            print(f"  - {h}: {grund}")
    print(f"\nInsgesamt {len(alle)} Aufgaben in aufgaben.json.")


if __name__ == "__main__":
    main()
