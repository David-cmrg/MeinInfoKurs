/* ==========================================================================
   MeinInfoKurs V3 - seite.js
   Ein Skript fuer alle Seiten. Jede Seite hat nur einen Teil der Elemente,
   deshalb wird hier ueberall geprueft ob es das Element ueberhaupt gibt,
   bevor darauf zugegriffen wird. Genau daran ist die alte script.js gestorben.
   ========================================================================== */

(function () {
    "use strict";

    var $  = function (sel, wurzel) { return (wurzel || document).querySelector(sel); };
    var $$ = function (sel, wurzel) { return Array.prototype.slice.call((wurzel || document).querySelectorAll(sel)); };

    /* localStorage kann werfen (privates Fenster, gesperrte Cookies).
       Deshalb nie direkt benutzen. */
    var speicher = {
        lies: function (schluessel, ersatz) {
            try {
                var wert = window.localStorage.getItem(schluessel);
                return wert === null ? ersatz : JSON.parse(wert);
            } catch (e) { return ersatz; }
        },
        schreib: function (schluessel, wert) {
            try { window.localStorage.setItem(schluessel, JSON.stringify(wert)); } catch (e) { /* egal */ }
        }
    };

    /* ---------------------------------------------------------------- Thema */

    function themaSetzen(thema) {
        document.documentElement.setAttribute("data-thema", thema);
        speicher.schreib("thema", thema);
        var knopf = $("#thema-schalter");
        if (knopf) {
            var hell = thema === "hell";
            knopf.setAttribute("aria-label", hell ? "Dunkles Design einschalten" : "Helles Design einschalten");
            knopf.setAttribute("aria-pressed", String(hell));
            var symbol = $("i", knopf);
            if (symbol) symbol.className = hell ? "fa-solid fa-moon" : "fa-solid fa-sun";
        }
    }

    function themaStarten() {
        var gespeichert = speicher.lies("thema", null);
        var systemHell = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
        themaSetzen(gespeichert || (systemHell ? "hell" : "dunkel"));

        var knopf = $("#thema-schalter");
        if (!knopf) return;
        knopf.addEventListener("click", function () {
            var jetzt = document.documentElement.getAttribute("data-thema");
            themaSetzen(jetzt === "hell" ? "dunkel" : "hell");
        });
    }

    /* -------------------------------------------------------------- Verlauf */

    var VERLAUF_MAX = 6;

    function verlaufMerken() {
        // Uebersichtsseiten und die Startseite landen nicht im Verlauf
        var main = $("main");
        if (!main || main.dataset.verlauf === "nein") return;

        var titel = (document.title || "").replace(/^MeinInfoKurs\s*[|·-]\s*/, "").trim();
        if (!titel) return;

        var liste = speicher.lies("verlauf", []);
        if (!Array.isArray(liste)) liste = [];

        var pfad = location.pathname;
        liste = liste.filter(function (e) { return e && e.pfad !== pfad; });
        liste.unshift({ titel: titel, pfad: pfad });
        speicher.schreib("verlauf", liste.slice(0, VERLAUF_MAX));
    }

    function verlaufZeigen() {
        var liste = $("#verlauf-liste");
        if (!liste) return;

        var eintraege = speicher.lies("verlauf", []);
        if (!Array.isArray(eintraege)) eintraege = [];
        // die aktuelle Seite selbst nicht mit anbieten
        eintraege = eintraege.filter(function (e) { return e && e.pfad !== location.pathname; });

        liste.textContent = "";
        if (!eintraege.length) {
            var leer = document.createElement("li");
            leer.className = "leer";
            leer.textContent = "Noch nichts angesehen.";
            liste.appendChild(leer);
            return;
        }
        eintraege.forEach(function (e) {
            var li = document.createElement("li");
            var a = document.createElement("a");
            a.href = e.pfad;
            a.textContent = e.titel;
            li.appendChild(a);
            liste.appendChild(li);
        });
    }

    /* --------------------------------------------------------------- Dialoge */

    function dialogVerdrahten() {
        $$("[data-oeffnet]").forEach(function (knopf) {
            var ziel = document.getElementById(knopf.dataset.oeffnet);
            if (!ziel || typeof ziel.showModal !== "function") return;
            knopf.addEventListener("click", function () {
                if (ziel.id === "verlauf-fenster") verlaufZeigen();
                if (ziel.id === "suche-fenster") suchIndexLaden();
                ziel.showModal();
                if (ziel.id === "suche-fenster") {
                    var feld = $("#suche-feld");
                    if (feld) feld.focus();
                }
            });
        });

        $$("dialog.fenster").forEach(function (dlg) {
            var zu = $("[data-schliesst]", dlg);
            if (zu) zu.addEventListener("click", function () { dlg.close(); });
            // Klick auf den Hintergrund schliesst ebenfalls
            dlg.addEventListener("click", function (ev) {
                if (ev.target === dlg) dlg.close();
            });
        });
    }


    /* ----------------------------------------------------------------- Suche
       Der Index liegt als eine JSON-Datei unter assets/suchindex.json und wird
       erst geholt, wenn jemand die Suche wirklich oeffnet. Gesucht wird ueber
       Titel, Kurztext, Halbjahr, Bereich und die Aufgabenstellung. */

    var suchIndex = null;
    var suchLaeuft = false;

    function basisPfad() {
        return document.documentElement.getAttribute("data-basis") || "";
    }

    function ohneAkzente(text) {
        var t = String(text).toLowerCase();
        // Umlaute so schreiben, wie Leute sie tippen: "loesung" findet "Lösung"
        t = t.replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss");
        return t;
    }

    function suchIndexLaden() {
        if (suchIndex || suchLaeuft) return;
        suchLaeuft = true;
        var hinweis = $("#suche-hinweis");
        fetch(basisPfad() + "assets/suchindex.json")
            .then(function (a) { return a.ok ? a.json() : Promise.reject(a.status); })
            .then(function (daten) {
                suchIndex = daten.map(function (e) {
                    e._ = ohneAkzente([e.t, e.k, e.h, e.b, e.a].join(" "));
                    return e;
                });
                suchLaeuft = false;
                suchen();
            })
            .catch(function () {
                suchLaeuft = false;
                if (hinweis) hinweis.textContent = "Die Suche laesst sich gerade nicht laden.";
            });
    }

    function suchen() {
        var feld = $("#suche-feld");
        var liste = $("#suche-treffer");
        var hinweis = $("#suche-hinweis");
        if (!feld || !liste) return;

        var frage = ohneAkzente(feld.value).trim();
        liste.textContent = "";

        if (!frage) {
            if (hinweis) {
                hinweis.hidden = false;
                hinweis.innerHTML = "Tippe los. <kbd>Strg</kbd>+<kbd>K</kbd> öffnet die Suche von überall.";
            }
            return;
        }
        if (!suchIndex) { suchIndexLaden(); return; }

        var woerter = frage.split(/\s+/);
        var treffer = suchIndex.filter(function (e) {
            return woerter.every(function (w) { return e._.indexOf(w) !== -1; });
        });

        // Titeltreffer zuerst, die will man fast immer
        var erstesWort = woerter[0];
        treffer.sort(function (a, b) {
            var ta = ohneAkzente(a.t).indexOf(erstesWort) !== -1 ? 0 : 1;
            var tb = ohneAkzente(b.t).indexOf(erstesWort) !== -1 ? 0 : 1;
            return ta - tb;
        });

        if (hinweis) {
            hinweis.hidden = false;
            hinweis.textContent = treffer.length === 0
                ? "Nichts gefunden."
                : treffer.length + (treffer.length === 1 ? " Aufgabe" : " Aufgaben");
        }

        treffer.slice(0, 40).forEach(function (e) {
            var li = document.createElement("li");
            var a = document.createElement("a");
            a.href = basisPfad() + e.u;

            var titel = document.createElement("span");
            titel.className = "suche-titel";
            titel.textContent = e.t;

            var wo = document.createElement("span");
            wo.className = "suche-wo";
            wo.textContent = e.h + " · " + e.b;

            a.appendChild(titel);
            a.appendChild(wo);
            li.appendChild(a);
            liste.appendChild(li);
        });
    }

    function sucheVerdrahten() {
        var fenster = $("#suche-fenster");
        var feld = $("#suche-feld");
        if (!fenster || !feld) return;

        feld.addEventListener("input", suchen);

        // Enter springt auf den ersten Treffer
        feld.addEventListener("keydown", function (ev) {
            if (ev.key !== "Enter") return;
            var erster = $("#suche-treffer a");
            if (erster) { ev.preventDefault(); erster.click(); }
        });

        // Strg+K von ueberall
        document.addEventListener("keydown", function (ev) {
            if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
                ev.preventDefault();
                if (!fenster.open && typeof fenster.showModal === "function") {
                    suchIndexLaden();
                    fenster.showModal();
                    feld.focus();
                }
            }
        });
    }

    /* ------------------------------------------------------------ Codeblock */

    function codeText(feld) {
        var block = $("code", feld);
        if (!block) return "";
        //   kommt aus dem HTML und macht im Java-Editor Aerger
        return block.textContent.replace(/ /g, " ").replace(/\s+$/, "");
    }

    function kurzRueckmeldung(knopf, text) {
        var vorher = knopf.textContent;
        knopf.textContent = text;
        knopf.classList.add("fertig");
        window.setTimeout(function () {
            knopf.textContent = vorher;
            knopf.classList.remove("fertig");
        }, 1600);
    }

    function codeVerdrahten() {
        $$(".code").forEach(function (block) {
            var feld = $(".code-feld", block);
            if (!feld) return;

            var aufdecken = $(".aufdecken", feld);
            if (aufdecken) {
                aufdecken.addEventListener("click", function () {
                    feld.classList.remove("verdeckt");
                    aufdecken.remove();
                });
            }

            var kopieren = $("[data-kopieren]", block);
            if (kopieren) {
                kopieren.addEventListener("click", function () {
                    var text = codeText(feld);
                    if (!text) return;
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(text).then(function () {
                            kurzRueckmeldung(kopieren, "Kopiert");
                        }, function () {
                            kurzRueckmeldung(kopieren, "Ging nicht");
                        });
                    } else {
                        kurzRueckmeldung(kopieren, "Ging nicht");
                    }
                });
            }

            var laden = $("[data-datei]", block);
            if (laden) {
                laden.addEventListener("click", function () {
                    var text = codeText(feld);
                    if (!text) return;
                    var blob = new Blob([text], { type: "text/plain;charset=utf-8" });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement("a");
                    a.href = url;
                    a.download = laden.dataset.datei || "MeinInfoKurs.txt";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
                });
            }
        });
    }

    /* -------------------------------------------------------- Antworten auf */

    function antwortenVerdrahten() {
        $$(".antwort").forEach(function (el) {
            el.addEventListener("click", function () { el.classList.add("offen"); });
        });
    }

    /* --------------------------------------------------------- Eigenwerbung */

    var eigeneWerbung = [
        {
            titel: "Mein Portfolio",
            text:  "Erfahre mehr über mich und meine Arbeit!",
            link:  "https://david-cmrg.github.io/AboutDavid/DE/",
            bild:  "David.jpeg"
        },
        {
            titel: "Meine Projekte",
            text:  "Sieh dir meinen Code an!",
            link:  "https://github.com/David-cmrg",
            bild:  "GitHub.webp"
        },
        {
            titel: "Bewerte MeinInfoKurs",
            text:  "Schreibe eine Bewertung!",
            link:  "https://docs.google.com/forms/d/e/1FAIpQLSdIS0osFMUzrgBYM7p84xiIwi_Io9ycmjyyiFF9a-1Ukb_xgw/viewform",
            bild:  "stern.png"
        },
        {
            titel: "Dein Werbespot!",
            text:  "Lade deine Werbung hoch, die hier angezeigt wird!",
            link:  "mailto:meininfokurs@gmail.com?subject=Anfrage%20zur%20Werbeschaltung%20auf%20MeinInfoKurs&body=Sehr%20geehrter%20Herr%20Gomez%20C.%2C%0D%0A%0D%0Aich%20interessiere%20mich%20für%20die%20Möglichkeit%2C%20Werbung%20auf%20Ihrer%20Website%20zu%20platzieren.%0D%0ABitte%20lassen%20Sie%20mir%20weitere%20Informationen%20zu%20Konditionen%2C%20Formaten%20und%20Reichweite%20zukommen.%0D%0A%0D%0AMit%20freundlichen%20Grüßen%2C%0D%0A%5BIhr%20Name%5D",
            bild:  "deineWerbung.png"
        }
    ];

    var WARTEZEIT = 3;       // Sekunden bis man schliessen darf
    var VERZOEGERUNG = 25000; // erst nach 25 s, nicht sofort ins Gesicht

    function werbungZeigen() {
        var fenster = $("#werbe-fenster");
        if (!fenster || typeof fenster.showModal !== "function") return;

        var inhalt = $("#werbe-inhalt", fenster);
        var zu     = $("[data-schliesst]", fenster);
        var uhr    = $("#werbe-uhr", fenster);
        if (!inhalt || !zu) return;

        var w = eigeneWerbung[Math.floor(Math.random() * eigeneWerbung.length)];
        var basis = document.documentElement.dataset.basis || "";

        inhalt.textContent = "";
        var bild = document.createElement("img");
        bild.src = basis + "assets/bilder/" + w.bild;
        bild.alt = "";
        bild.width = 200; bild.height = 200;
        bild.loading = "lazy";
        var h3 = document.createElement("h3"); h3.textContent = w.titel;
        var p  = document.createElement("p");  p.textContent  = w.text;
        var a  = document.createElement("a");
        a.className = "knopf";
        a.href = w.link;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Mehr erfahren";
        inhalt.append(bild, h3, p, a);

        zu.disabled = true;
        var rest = WARTEZEIT;
        if (uhr) uhr.textContent = "Noch " + rest + " s";
        var takt = window.setInterval(function () {
            rest -= 1;
            if (uhr) uhr.textContent = rest > 0 ? "Noch " + rest + " s" : "";
            if (rest <= 0) {
                window.clearInterval(takt);
                zu.disabled = false;
            }
        }, 1000);

        fenster.addEventListener("cancel", function (ev) {
            if (zu.disabled) ev.preventDefault();
        });

        fenster.showModal();
    }

    function werbungStarten() {
        if (!$("#werbe-fenster")) return;
        // Einmal pro Sitzung. Nicht alle zwei Minuten.
        try {
            if (window.sessionStorage.getItem("werbung-gesehen")) return;
            window.sessionStorage.setItem("werbung-gesehen", "1");
        } catch (e) { /* ohne sessionStorage halt einmal pro Seitenaufruf */ }
        window.setTimeout(werbungZeigen, VERZOEGERUNG);
    }

    /* ------------------------------------------------------- Hinweisstreifen */

    function hinweisVerdrahten() {
        var streifen = $("#hinweis-streifen");
        if (!streifen) return;
        var zu = $("[data-schliesst]", streifen);
        if (zu) zu.addEventListener("click", function () { streifen.hidden = true; });
    }

    /* ------------------------------------------------------------ Kopierschutz
       Uebernommen aus V2. Haelt niemanden ernsthaft ab, ist aber so gewollt. */

    function kopierschutz() {
        document.addEventListener("contextmenu", function (ev) { ev.preventDefault(); });
        document.addEventListener("keydown", function (ev) {
            var k = ev.key;
            if (k === "F12" ||
                (ev.ctrlKey && ev.shiftKey && (k === "I" || k === "J" || k === "C")) ||
                (ev.ctrlKey && k === "u")) {
                ev.preventDefault();
            }
        });
    }

    /* ------------------------------------------------------------------ Start */

    function start() {
        themaStarten();
        verlaufMerken();
        dialogVerdrahten();
        sucheVerdrahten();
        codeVerdrahten();
        antwortenVerdrahten();
        hinweisVerdrahten();
        kopierschutz();
        werbungStarten();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
