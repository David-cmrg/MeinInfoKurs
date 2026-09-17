#!/usr/bin/env python3
"""
karten.py - erzeugt die Vorschaubilder (1200x630) fuer Discord, Twitter & Co.
Rendert echtes HTML mit Chrome, damit die Karte aussieht wie die Seite.
    python3 werkzeug/karten.py
"""
import pathlib, shutil, subprocess, sys, tempfile

WURZEL = pathlib.Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "assets" / "og"
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")

KARTEN = [
    {"id": "start", "pille": "", "titel": "MeinInfoKurs",
     "zeile": "Aufgaben, Lösungen und Erklärungen aus dem Info-Kurs.",
     "code": ["public class Autohaus {", "  Auto auto1 = new Auto(…);",
              "  auto1.tanken(30);", "  auto1.fahren(10);", "}"]},
    {"id": "e", "pille": "E-Phase · Klasse 10", "titel": "Grundlagen",
     "zeile": "Der Einstieg in Java und HTML.",
     "code": ['System.out.println("Hello World");', "int zahl = 11;",
              "while (zahl > 0) {", "  zahl = zahl - 2;", "}"]},
    {"id": "q1", "pille": "Q1 · Klasse 11, 1. Halbjahr", "titel": "OOP &amp; Algorithmen",
     "zeile": "Objektorientierung in Java, Suchen und Sortieren.",
     "code": ["mitte = (links + rechts) / 2;", "if (a[mitte] == schluessel)",
              "  return true;", "else if (a[mitte] < schluessel)", "  links = mitte + 1;"]},
    {"id": "q2", "pille": "Q2 · Klasse 11, 2. Halbjahr", "titel": "Datenbanken",
     "zeile": "Schlüssel, SQL, Normalisierung und der Zugriff aus PHP.",
     "code": ["SELECT name, bip", "  FROM cia", " WHERE region = 'Europa'",
              " ORDER BY bip DESC", " LIMIT 10;"]},
    {"id": "q3", "pille": "Q3 · Klasse 12, 1. Halbjahr", "titel": "Formale Sprachen",
     "zeile": "Alphabete, Syntax und Semantik.",
     "code": ["Σ = { P, ' ', 0…9 }", "w = P2 2 2 3 0 1 2 3", "L = { aⁿb | n ≥ 0 }",
              "halli·halli·hallo", "syntaktisch korrekt ✓"]},
]

VORLAGE = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:1200px; height:630px; }}
  body {{
    background:#14151f;
    background-image:
      radial-gradient(circle at 92% 6%, rgba(216,180,254,.20), transparent 44%),
      radial-gradient(circle at 4% 96%, rgba(125,211,252,.15), transparent 48%);
    font-family:"Montserrat",system-ui,sans-serif;
    color:#e6e7ef;
    display:grid; grid-template-columns:1fr 0.82fr;
    position:relative; overflow:hidden;
  }}
  body::before {{
    content:""; position:absolute; inset:0;
    background-image:linear-gradient(#ffffff07 1px,transparent 1px),
                     linear-gradient(90deg,#ffffff07 1px,transparent 1px);
    background-size:56px 56px;
    -webkit-mask-image:linear-gradient(115deg,#000 6%,transparent 68%);
  }}
  .links {{
    position:relative; z-index:2;
    padding:74px 20px 66px 86px;
    display:flex; flex-direction:column; justify-content:space-between;
  }}
  .marke {{ font-size:18px; font-weight:700; letter-spacing:.26em;
            text-transform:uppercase; color:#7b8095; }}
  .pille {{
    display:inline-block; align-self:flex-start;
    font-size:20px; font-weight:600; letter-spacing:.04em;
    padding:8px 20px; border-radius:999px; margin-bottom:24px;
    border:1.5px solid rgba(125,211,252,.38); color:#7dd3fc;
  }}
  h1 {{
    font-size:{gross}px; font-weight:700; line-height:1.02; letter-spacing:-.028em;
    background:linear-gradient(94deg,#7dd3fc,#d8b4fe);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }}
  p {{ margin-top:24px; font-size:27px; line-height:1.45; color:#9b9fb5; max-width:26ch; }}
  .fuss {{ display:flex; align-items:center; gap:14px; font-size:20px;
           font-weight:600; color:#6f7489; }}
  .punkt {{ width:9px; height:9px; border-radius:50%; background:#7dd3fc; flex:none; }}

  /* rechte Seite: angedeuteter Code, damit die Karte nicht halb leer ist */
  .rechts {{
    position:relative; z-index:1;
    display:flex; flex-direction:column; justify-content:center; gap:20px;
    padding:0 60px 0 34px;
    font-family:"JetBrains Mono",ui-monospace,monospace;
    font-size:21px; line-height:1.5; white-space:nowrap;
    -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 9%,#000 82%,transparent);
  }}
  .rechts div {{ color:#7dd3fc; opacity:.15; }}
  .rechts div:nth-child(2) {{ color:#d8b4fe; opacity:.13; }}
  .rechts div:nth-child(3) {{ opacity:.19; }}
  .rechts div:nth-child(4) {{ color:#d8b4fe; opacity:.11; }}
  .rechts div:nth-child(5) {{ opacity:.13; }}
</style></head><body>
  <div class="links">
    <div class="marke">MeinInfoKurs</div>
    <div>
      {pille_block}
      <h1>{titel}</h1>
      <p>{zeile}</p>
    </div>
    <div class="fuss"><span class="punkt"></span>david-cmrg.github.io/MeinInfoKurs</div>
  </div>
  <div class="rechts">{code_block}</div>
</body></html>"""


def main():
    if not CHROME:
        sys.exit("Kein Chrome gefunden - Karten koennen nicht gerendert werden.")
    ZIEL.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for k in KARTEN:
            pille = f'<div class="pille">{k["pille"]}</div>' if k["pille"] else ""
            code = "".join(f"<div>{z}</div>" for z in k["code"])
            gross = 92 if len(k["titel"]) > 15 else 104
            html = VORLAGE.format(titel=k["titel"], zeile=k["zeile"],
                                  pille_block=pille, code_block=code, gross=gross)
            quelle = tmp / f"{k['id']}.html"
            quelle.write_text(html, encoding="utf-8")
            subprocess.run([
                CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                "--window-size=1200,630",
                f"--screenshot={ZIEL / (k['id'] + '.png')}",
                quelle.as_uri(),
            ], check=True, capture_output=True, timeout=90)
            print(f"  assets/og/{k['id']}.png")
    print("\nKarten fertig.")


if __name__ == "__main__":
    main()
