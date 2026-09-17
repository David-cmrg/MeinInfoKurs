#!/usr/bin/env python3
"""
pruefen.py - prueft die gebauten Seiten auf die Fehler, die beim Schreiben
der Aufgaben immer wieder passieren.

    python3 werkzeug/pruefen.py            alle Seiten
    python3 werkzeug/pruefen.py q1         nur ein Halbjahr
"""
import html, json, pathlib, re, sys

SEITE = pathlib.Path(__file__).resolve().parent.parent
filter_hj = sys.argv[1] if len(sys.argv) > 1 else None

AUFGABEN = json.loads((SEITE / "werkzeug" / "aufgaben.json").read_text(encoding="utf-8"))
probleme, geprueft = [], 0

for a in AUFGABEN:
    if a.get("status") == "geplant":
        continue
    if filter_hj and a["halbjahr"] != filter_hj:
        continue
    datei = SEITE / a["halbjahr"] / a["bereich"] / f"{a['id']}.html"
    if not datei.exists():
        probleme.append((a["id"], "Seite wurde nicht gebaut"))
        continue
    geprueft += 1
    s = datei.read_text(encoding="utf-8")

    # Diagramme sind mermaid-Quelltext, kein Java. Klammern wie in
    # "A[Start] --> B{Bedingung}" gehen dort absichtlich nicht paarweise auf.
    # Die Syntax prueft diagrammpruefung.py, nicht dieses Werkzeug.
    s = re.sub(r'<pre class="mermaid".*?</pre>', "", s, flags=re.S)

    for roh in re.findall(r"<code[^>]*>(.*?)</code>", s, re.S):
        code = html.unescape(roh)

        # doppelt escaped: nach einmal unescapen duerfen keine Entities uebrig sein
        if re.search(r"&(lt|gt|amp|quot);", code):
            probleme.append((a["id"], f"doppelt escaped: {code[:50]!r}"))

        # Klammern muessen aufgehen (nur bei richtigen Code-Bloecken).
        # fehlersuche.html zeigt absichtlich kaputten Code als Beispiel.
        if a["id"] != "fehlersuche" and ("public class" in code or "public void" in code):
            # Kommentare und Strings raus - dort stehen Klammern wie in
            # "// Aufgabe 5 b)", die nichts mit der Code-Struktur zu tun haben.
            ohne = re.sub(r"//[^\n]*", "", code)
            ohne = re.sub(r"/\*.*?\*/", "", ohne, flags=re.S)
            ohne = re.sub(r'"(\\.|[^"\\])*"', '""', ohne)
            if ohne.count("{") != ohne.count("}"):
                probleme.append((a["id"],
                                 f"geschweifte Klammern ungleich: {ohne.count('{')} auf, "
                                 f"{ohne.count('}')} zu"))
            if ohne.count("(") != ohne.count(")"):
                probleme.append((a["id"], "runde Klammern ungleich"))

        # Platzhalter werden weiter unten geprueft - nur in echten
        # <pre>-Bloecken, nicht bei Inline-Code im Fliesstext. Ein
        # <code>X</code> mitten im Satz ist legitimer Inhalt.

    # Wasserzeichen darf nicht IN einem code-Element stehen
    for roh in re.findall(r"<code[^>]*>(.*?)</code>", s, re.S):
        if "meininfokurs.cmrg.site */" in html.unescape(roh):
            probleme.append((a["id"], "Wasserzeichen-Span im Codeblock"))

    # Platzhalter nur in echten Codebloecken suchen
    for roh in re.findall(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>", s, re.S):
        if html.unescape(roh).strip() in ("X", "x", "TODO", "..."):
            probleme.append((a["id"], "Platzhalter im Codeblock"))

    # geschuetzte Leerzeichen zerschiessen den Java-Editor
    if " " in s:
        probleme.append((a["id"], "geschuetztes Leerzeichen auf der Seite"))

    # Loesungsblock sollte verdeckt sein und einen Download anbieten.
    # Ausnahme: Nachschlageseiten (verdeckt: false) - eine Befehlsuebersicht
    # unscharf zu machen hilft niemandem.
    if a.get("verdeckt", True) and "data-datei=" in s and "code-feld verdeckt" not in s:
        probleme.append((a["id"], "Loesung ist nicht verdeckt"))

    # leere Absaetze / uebriggebliebene Geruestreste
    if re.search(r"<p>\s*(X|x|TODO)\s*</p>", s):
        probleme.append((a["id"], "Platzhalter-Absatz"))

print(f"{geprueft} Seiten geprueft.")
if probleme:
    print(f"\n{len(probleme)} Problem(e):")
    for kennung, was in probleme:
        print(f"  {kennung}: {was}")
    sys.exit(1)
print("Keine Beanstandungen.")
