# Diagramme

Dieser Ordner lässt sich direkt als **Obsidian-Vault** öffnen. Jede `.md` hier
ist ein Diagramm der Webseite — in Obsidian siehst du genau dasselbe Bild wie
unter [meininfokurs.cmrg.site](https://meininfokurs.cmrg.site).

## Aufbau einer Datei

```
# Die Überschrift wird zur Bildunterschrift

Quelle: Q1.1.pdf S. 35–42

​```mermaid
classDiagram
    Autohaus ..> Auto : erzeugt mit new
​```
```

Drei Pflichtteile, sonst bricht `baue.py` ab:

| Teil | Wofür |
| --- | --- |
| `# Überschrift` | steht später unter dem Bild |
| `Quelle: <PDF> S. <Seite>` | nur intern — wird **nicht** angezeigt |
| ein ```mermaid-Block | das Diagramm selbst |

Die Quellenangabe erscheint nicht auf der Webseite: wer die Seite liest, hat die
OneNote-PDFs nicht. Pflicht ist sie trotzdem — sie ist der Beleg, dass ein
Diagramm aus dem Unterrichtsmaterial kommt und nicht ausgedacht ist.

## Einbinden

Im Inhaltsschnipsel `werkzeug/inhalt/<aufgabe>.html` an der passenden Stelle:

```html
        <div data-diagramm="uml-auto-autohaus"></div>
```

`baue.py` macht daraus beim Bauen die fertige `<figure>`.

## Prüfen

```
python3 werkzeug/diagrammpruefung.py
```

Prüft Aufbau und Syntax (jeder Block läuft durch `mermaid.parse()`) und meldet
Diagramme, die eingebunden sind aber fehlen — oder umgekehrt.

## Wann ein Diagramm hingehört

Nur wenn das Bild etwas zeigt, das Fließtext schlecht transportiert:
Klassenbeziehungen, Normalisierungsschritte, Rekursionsbäume, Zustandsautomaten.
Ein Flussdiagramm für „gib deinen Namen aus" lässt eine Seite künstlich aussehen.

Und: **kein ER-Diagramm für Datenbanken, deren Schema nicht im OneNote steht**
(`cia`, Übung 3, Kurs, Nordwind). Ein Diagramm sieht autoritativ aus und würde
aus einer Annahme eine scheinbare Tatsache machen.
