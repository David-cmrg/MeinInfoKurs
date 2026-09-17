/**
                    *
                    * Programm zur Berechnung der Wassergeb�hren.
                    *
                    * @version 1.0 vom 16.03.2025
                    * @meininfokurs.cmrg.site
                    */

                    public class WassergebuehrenMeinInfo {

                        public static void main(String[] args) {
                            int zaehlerAlt, zaehlerNeu, wasserverbrauch;
                            double grundpreis, preisProM3, ust = 0.07;
                            double nettoVerbrauch, nettoGesamt, mehrwertsteuer, bruttoGesamt;

                            zaehlerAlt = InOut.readInt("Alter Z�hlerstand: ");
                            zaehlerNeu = InOut.readInt("Neuer Z�hlerstand: ");
                            grundpreis = InOut.readDouble("Monatlicher Grundpreis (Euro): ");
                            preisProM3 = InOut.readDouble("Preis pro Kubikmeter (Euro): ");

                            wasserverbrauch = zaehlerNeu - zaehlerAlt;
                            nettoVerbrauch = wasserverbrauch * preisProM3;
                            nettoGesamt = nettoVerbrauch + grundpreis;
                            mehrwertsteuer = nettoGesamt * ust;
                            bruttoGesamt = nettoGesamt + mehrwertsteuer;

                            System.out.println("Ihr Wasserverbrauch: " + wasserverbrauch + " m�");
                            System.out.println("Nettobetrag: " + InOut.format2(nettoGesamt) + " Euro");
                            System.out.println("Mehrwertsteuer: " + InOut.format2(mehrwertsteuer) + " Euro");
                            System.out.println("Bruttobetrag: " + InOut.format2(bruttoGesamt) + " Euro");
                        };
                    };  
