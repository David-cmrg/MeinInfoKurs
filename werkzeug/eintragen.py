#!/usr/bin/env python3
"""
eintragen.py - traegt Aufgaben in aufgaben.json ein oder aktualisiert sie.
Liest eine Liste von Eintraegen als JSON von stdin. Vorhandene IDs werden
ueberschrieben, neue angehaengt, die Reihenfolge (nr) bleibt wie angegeben.

    python3 werkzeug/eintragen.py < neue_aufgaben.json
"""
import json, pathlib, sys

WERK = pathlib.Path(__file__).resolve().parent
ZIEL = WERK / "aufgaben.json"

neu = json.load(sys.stdin)
if isinstance(neu, dict):
    neu = [neu]

alt = json.loads(ZIEL.read_text(encoding="utf-8"))
def schluessel(a):
    return (a["halbjahr"], a["bereich"], a["id"])

nach_id = {schluessel(a): a for a in alt}

for eintrag in neu:
    pflicht = {"id", "halbjahr", "bereich", "nr", "titel", "kurz", "quelle", "status"}
    fehlt = pflicht - set(eintrag)
    if fehlt:
        sys.exit(f"Eintrag {eintrag.get('id','?')}: es fehlen {sorted(fehlt)}")
    eintrag.setdefault("sprache", "java")
    if eintrag["status"] != "geplant":
        frag = WERK / "inhalt" / f"{eintrag['id']}.html"
        if not frag.exists():
            sys.exit(f"Eintrag {eintrag['id']}: inhalt/{eintrag['id']}.html fehlt")
    nach_id[schluessel(eintrag)] = eintrag

alle = sorted(nach_id.values(),
              key=lambda a: (a["halbjahr"], a["bereich"], a.get("nr", 0)))
ZIEL.write_text(json.dumps(alle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(neu)} Eintrag/Einträge verarbeitet, {len(alle)} Aufgaben insgesamt.")
