# Die vier Multiplizitäten an einer Schule

Quelle: Q1.1.pdf S. 148

```mermaid
classDiagram
    Direktor "1" -- "*" Sekretaerin
    Direktor "1" -- "1..*" Lehrer
    Schulsozialarbeiter "0..1" -- "1..*" Lehrer
```
