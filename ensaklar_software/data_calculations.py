# -*- coding: utf-8 -*-
"""
File for the calculation model. 

@author: jbgru
"""

from datetime import date


# Klasse für das Gebäude (Mieter, Eigentümer etc.)
class Gebaeude:
    GESAMTNUTZUNGSDAUER = 80 #Jahre für Wohnungen und Häuser laut Verordnung
    JAHRESZAHL = date.today().year #jetziges Jahr
    BAUPREISINDEX = 183.3 #Baupreisindex 2025 zur Anpassung der Regelherstellungskosten aus 2010 gemäß BewG §190
    BETRIEBSKOSTEN_QM = 2.67 # Deutscher Mieterbund 2024 Betriebskostenspiegel

    # Zur Initialisierung eines Gebäudes mit folgenden Variablen:
    def __init__(self, baujahr: int):
        self.baujahr = baujahr
        
        self.restnutzungsdauer = self.GESAMTNUTZUNGSDAUER - (self.JAHRESZAHL - self.baujahr)
        if self.restnutzungsdauer < 0:
            self.restnutzungsdauer = 0

        
    # Klassenfunktion zur Berechnung/Abschätzung des Ertragwerts einer Immobilie
    def immobilienwert_ertragswert(self, bodenrichtwert, grundstuecksflaeche, wohnflaeche, miete_qm, grundstuecksart, anzahl_wohnungen, maengel, saniert: bool, sanierungsbestandteile_data=None):
        # bodenrichtwert in €/qm; bestimmt durch Gutachterausschuss für spezifische Region
        # grundstuecksflaeche: gesamte Fläche des vermieteten Objekts
        # miete_qm in €/qm; Nettokaltmiete pro m² - nutze hier die ortsübliche Vergleichsmiete/Mietspiegel als Input, wenn nicht vorhanden
        # grundstuecksart: nach § 249 BewG: Ein- und Zweifamilienhaus [1], Wohneigentum [2] oder Mietwohngrundstück [3]
        # liegenschaftszins in %; Zinssatz für bestimmtes Immobilienobjekt
        # maengel: Fixbetrag für bestimmte Mängel
        # saniert: True/False?
        
        # Berechnung der Bruttokaltmiete aus Miete pro qm (Nettokaltmiete)
        marktueblicher_mietwert_qm = miete_qm + self.BETRIEBSKOSTEN_QM
        
        # Ertragswert Ermittlung
        bodenwert = bodenrichtwert * grundstuecksflaeche
        rohertrag = wohnflaeche * marktueblicher_mietwert_qm * 12 # 12 Monate für ein Jahr
        
        if saniert:
            restnutzungsdauer = self.restnutzungsdauer_saniert(sanierungsbestandteile_data)
        else:
            restnutzungsdauer = self.restnutzungsdauer
        
        bewirtschaftungskosten_faktor = self.bewirtschaftungskosten_faktor(grundstuecksart=grundstuecksart, restnutzungsdauer=restnutzungsdauer)
        liegenschaftszins = self.liegenschaftszins(grundstuecksart=grundstuecksart, anzahl_wohnungen=anzahl_wohnungen, bodenrichtwert=bodenrichtwert)
        
        betriebskosten_jahr = self.betriebskosten_jahr(wohnflaeche)
        jahresreinertrag = rohertrag - (rohertrag * bewirtschaftungskosten_faktor) - betriebskosten_jahr # minus Instandhaltungskosten, Verwaltungskosten, Mietausfallwagnis, Betriebskosten (ImmoWertV § 32)
        bodenwert_verzinsung = bodenwert * liegenschaftszins
        
        # Vervielfältiger: Rechengröße, wie lange es dauert bis Investition durch Mieteinnahmen wieder ausgeglichen werden, Formel aus Bewertungsgesetz (BewG) Anlage 21 bzw. ImmoWertV §34 Absatz 2
        vervielfaeltiger = (((1 + liegenschaftszins) ** restnutzungsdauer) - 1) / (((1 + liegenschaftszins) ** restnutzungsdauer) * ((1 + liegenschaftszins) - 1))
        
        gebaeudeertragswert = (jahresreinertrag - bodenwert_verzinsung) * vervielfaeltiger
        ertragswert_vorlaeufig = gebaeudeertragswert + bodenwert
        immobilienwert_ertragswert = ertragswert_vorlaeufig - maengel
        
        return immobilienwert_ertragswert 


    # Klassenfunktion zur Berechnung/Abschätzung des Sachwerts einer Immobilie
    def immobilienwert_sachwert(self, bodenrichtwert, grundstuecksflaeche, regelherstellungskosten, bruttogrundflaeche, marktanpassungsfaktor, saniert: bool):
        # bodenrichtwert in €/qm; bestimmt durch Gutachterausschuss für spezifische Region
        # grundstuecksflaeche in m²; gesamte Fläche des Grundstücks
        # regelherstellungskosten in €/m²; Herstellungs-/Baukosten des Gebäudes pro qm; beinhalten alle Kosten für Materialien, Planung, Fertigung, Einkauf, Wareneingang, Handwerker, Genehmigungen sowie Anschlusskosten andere nicht
        # bruttogrundflaeche in m²; gesamte Grundfläche des Gebäudes
        # marktanpassungsfaktor 0 - 2; Entwicklung der Sachwerte verglichen mit den tatsächlichen Kaufpreisen
        
        bodenwert = bodenrichtwert * grundstuecksflaeche
        
        if saniert:
            restnutzungsdauer = float(input("\nNeue Restnutzungsdauer eingeben: "))
            alterswertminderung = (self.GESAMTNUTZUNGSDAUER - restnutzungsdauer) / (self.GESAMTNUTZUNGSDAUER * 100) #in Prozent
        
        else:
            alterswertminderung = (self.GESAMTNUTZUNGSDAUER - self.restnutzungsdauer) / (self.GESAMTNUTZUNGSDAUER * 100) #in Prozent
        
        # regelherstellungskosten = 
        gesamtherstellungskosten = bruttogrundflaeche * regelherstellungskosten * (self.BAUPREISINDEX / 100)
        gebaeudesachwert = gesamtherstellungskosten - (gesamtherstellungskosten * alterswertminderung)
        
        sachwert_vorlaeufig = (gebaeudesachwert + bodenwert)
        # marktanpassungsfaktor = 
        
        immobilienwert_sachwert = sachwert_vorlaeufig * marktanpassungsfaktor
        
        return immobilienwert_sachwert


    # Klassenfunktion zur Bestimmung der Bewirtschaftungskosten (ohne Betriebskosten) nach Anlage 40 zu § 255 BewG
    def bewirtschaftungskosten_faktor(self, grundstuecksart, restnutzungsdauer):
        # Grundstuecksart nach § 249 BewG: Ein- und Zweifamilienhaus [1], Wohneigentum [2] oder Mietwohngrundstück [3]
        
        if grundstuecksart == 1:
            if restnutzungsdauer >= 60:
                bewirtschaftungskosten = 0.18
            elif 40 < restnutzungsdauer < 60:
                bewirtschaftungskosten = 0.21
            elif 20 < restnutzungsdauer < 40:
                bewirtschaftungskosten = 0.25
            elif restnutzungsdauer < 20:
                bewirtschaftungskosten = 0.27
        elif grundstuecksart == 2:
            if restnutzungsdauer >= 60:
                bewirtschaftungskosten = 0.23
            elif 40 < restnutzungsdauer < 60:
                bewirtschaftungskosten = 0.25
            elif 20 < restnutzungsdauer < 40:
                bewirtschaftungskosten = 0.29
            elif restnutzungsdauer < 20:
                bewirtschaftungskosten = 0.31
        elif grundstuecksart == 3:
            if restnutzungsdauer >= 60:
                bewirtschaftungskosten = 0.21
            elif 40 < restnutzungsdauer < 60:
                bewirtschaftungskosten = 0.23
            elif 20 < restnutzungsdauer < 40:
                bewirtschaftungskosten = 0.27
            elif restnutzungsdauer < 20:
                bewirtschaftungskosten = 0.29
                
        return bewirtschaftungskosten
    
    
    # Klassenfunktion zur Bestimmung des Liegenschaftszinssatz nach § 256 BewG
    def liegenschaftszins(self, grundstuecksart, anzahl_wohnungen, bodenrichtwert):
        # anzahl_wohnungen: Wie viele Wohneinheiten das Gebäude hat
        # Grundstuecksart nach § 249 BewG: Ein- und Zweifamilienhaus [1], Wohneigentum [2] oder Mietwohngrundstück [3]

        if grundstuecksart == 1:
            if bodenrichtwert <= 500:
                liegenschaftszins = 0.025
            elif 500 < bodenrichtwert < 1500:
                faktor = (bodenrichtwert - 500) / 100
                liegenschaftszins = 0.025 - (int(faktor) * 0.001)
            elif bodenrichtwert >= 1500:
                liegenschaftszins = 0.015
        elif grundstuecksart == 2:
            if bodenrichtwert <= 2000:
                liegenschaftszins = 0.03
            elif 2000 < bodenrichtwert < 3000:
                faktor = (bodenrichtwert - 2000) / 100
                liegenschaftszins = 0.03 - (int(faktor) * 0.001)
            elif bodenrichtwert >= 3000:
                liegenschaftszins = 0.02
        elif grundstuecksart == 3:
            if anzahl_wohnungen <= 6:
                liegenschaftszins = 0.04
            elif anzahl_wohnungen > 6:
                liegenschaftszins = 0.045
                
        return liegenschaftszins
        
    
    # Klassenfunktion zur Berechnung/Abschätzung der Restnutzungsdauer nach Sanierung, mittels Abschätzung des Modernisierungsgrads
    def restnutzungsdauer_saniert(self, sanierungsbestandteile: list):
        # Relative Alter bestimmt, ob die Modernisierung überhaupt Auswirkungen auf die Restnutzungsdauer hat. 
        # Beispiel: Wenn Haus 10 Jahre alt und nur ein paar Dinge renoviert werden (warum auch immer), hat dies keine Auswikrungen auf RND
        relatives_alter = ((self.JAHRESZAHL - self.baujahr) / self.GESAMTNUTZUNGSDAUER)
        
        # Bewertung des Modernisierungsgrads mittels Sanierungsbestandteile; über index und boolean in Liste Punkte vergeben
        # modernisierungspunkte = ["Fenster und Außentüren", "Leitungssysteme", "Heizungsanlage", "Bädern", "Innenausbaus, z. B. Decken, Fußböden, Treppen", "Wesentliche Verbesserung der Grundrissgestaltung", "Dacherneuerung mit Wärmedämmung", "Wärmedämmung Außenwände"]
        # nicht berücksichtigt werden: "Bädern", "Innenausbaus, z. B. Decken, Fußböden, Treppen", "Wesentliche Verbesserung der Grundrissgestaltung"
        modernisierungspunkte = 0
        
        if sanierungsbestandteile[0]:
            modernisierungspunkte += 1 # für Leitungssystem (nur Heizrohre, nicht Strom, Wasser)
        if sanierungsbestandteile[1]:
            modernisierungspunkte += 2 # für Heizungsanlage
        if sanierungsbestandteile[7]:
            modernisierungspunkte += 10 # für Effizienzhaus-Gesamtpaket, alle Außenwände, Dach, Kellerdecke, Türen und Fenster
        else:
            if sanierungsbestandteile[2]:
                modernisierungspunkte += 4 # für Dacherneuerung und Wärmedämmung
            if sanierungsbestandteile[3]:
                modernisierungspunkte += 1 # für Fenstererneuerung
            if sanierungsbestandteile[4]:
                modernisierungspunkte += 1 # für Eingangstüren
            if sanierungsbestandteile[5]:
                modernisierungspunkte += 3 # für Außenwanddämmung
            if sanierungsbestandteile[6]:
                modernisierungspunkte += 1 # für Kellerdeckendämmung
        
        if modernisierungspunkte <= 1 and relatives_alter >= 0.6:
            restnutzungsdauer_saniert = (1.2500 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (2.6250 * (self.JAHRESZAHL - self.baujahr)) + (1.5250 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 2 and relatives_alter >= 0.55:
            restnutzungsdauer_saniert = (1.0767 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (2.2757 * (self.JAHRESZAHL - self.baujahr)) + (1.3878 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 3 and relatives_alter >= 0.55:
            restnutzungsdauer_saniert = (0.9033 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.9263 * (self.JAHRESZAHL - self.baujahr)) + (1.2505 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 4 and relatives_alter >= 0.4:
            restnutzungsdauer_saniert = (0.7300 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.5770 * (self.JAHRESZAHL - self.baujahr)) + (1.1133 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 5 and relatives_alter >= 0.35:
            restnutzungsdauer_saniert = (0.6725 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.4578 * (self.JAHRESZAHL - self.baujahr)) + (1.0850 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 6 and relatives_alter >= 0.3:
            restnutzungsdauer_saniert = (0.6150 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.3385 * (self.JAHRESZAHL - self.baujahr)) + (1.0567 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 7 and relatives_alter >= 0.25:
            restnutzungsdauer_saniert = (0.5575 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.2193 * (self.JAHRESZAHL - self.baujahr)) + (1.0283 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 8 and relatives_alter >= 0.2:
            restnutzungsdauer_saniert = (0.5000 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.1000 * (self.JAHRESZAHL - self.baujahr)) + (1.0000 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 9 and relatives_alter >= 0.19:
            restnutzungsdauer_saniert = (0.4660 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (1.0270 * (self.JAHRESZAHL - self.baujahr)) + (0.9906 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 10 and relatives_alter >= 0.18:
            restnutzungsdauer_saniert = (0.4320 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.9540 * (self.JAHRESZAHL - self.baujahr)) + (0.9811 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 11 and relatives_alter >= 0.17:
            restnutzungsdauer_saniert = (0.3980 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.8810 * (self.JAHRESZAHL - self.baujahr)) + (0.9717 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 12 and relatives_alter >= 0.16:
            restnutzungsdauer_saniert = (0.3640 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.8080 * (self.JAHRESZAHL - self.baujahr)) + (0.9622 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 13 and relatives_alter >= 0.15:
            restnutzungsdauer_saniert = (0.3300 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.7350 * (self.JAHRESZAHL - self.baujahr)) + (0.9528 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 14 and relatives_alter >= 0.14:
            restnutzungsdauer_saniert = (0.3040 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.6760 * (self.JAHRESZAHL - self.baujahr)) + (0.9506 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 15 and relatives_alter >= 0.13:
            restnutzungsdauer_saniert = (0.2780 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.6170 * (self.JAHRESZAHL - self.baujahr)) + (0.9485 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 16 and relatives_alter >= 0.12:
            restnutzungsdauer_saniert = (0.2520 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.5580 * (self.JAHRESZAHL - self.baujahr)) + (0.9463 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte == 17 and relatives_alter >= 0.11:
            restnutzungsdauer_saniert = (0.2260 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.4990 * (self.JAHRESZAHL - self.baujahr)) + (0.9442 * self.GESAMTNUTZUNGSDAUER)
        elif modernisierungspunkte >= 18 and relatives_alter >= 0.1:
            restnutzungsdauer_saniert = (0.2000 * (((self.JAHRESZAHL - self.baujahr) ** 2) / self.GESAMTNUTZUNGSDAUER)) - (0.4400 * (self.JAHRESZAHL - self.baujahr)) + (0.9420 * self.GESAMTNUTZUNGSDAUER)
        else:
            print("Relatives Alter zu jung. Modernisierungen haben erst ab einem bestimmten Alter der baulichen Anlagen Auswirkungen auf die Restnutzungsdauer.")
            return
        
        return restnutzungsdauer_saniert
    
    
    # Klassenfunktion zur Berechnung/Abschätzung der Kaltmiete
    def nettokaltmiete(self, wohnflaeche_mieter: float, miete_qm: float):
        nettokaltmiete = wohnflaeche_mieter * miete_qm
        
        return nettokaltmiete
    
    
    # Klassenfunktion zur Berechnung der umlagefähigen Betriebskosten zur Bestimmung der Bruttokaltmiete
    def betriebskosten_jahr(self, wohnflaeche: float):
        betriebskosten_jahr = wohnflaeche * self.BETRIEBSKOSTEN_QM * 12
        
        return betriebskosten_jahr
    
    
    # Klassenfunktion zur Berechnung/Abschätzung der Kaltmiete
    def bruttokaltmiete(self, wohnflaeche_mieter: float, miete_qm: float):
        # Berechnung der Bruttokaltmiete aus Miete pro qm (Nettokaltmiete)
        bruttokaltmiete_qm = miete_qm + self.BETRIEBSKOSTEN_QM
        bruttokaltmiete = wohnflaeche_mieter * bruttokaltmiete_qm
        
        return bruttokaltmiete
    
    
    # Klassenfunktion zur Berechnung/Abschätzung der Heiz- und Stromkosten
    def nebenkosten(self, energiekosten: float):
        nebenkosten = energiekosten / 12 # Monate
        
        return nebenkosten
    
    
    # Klassenfunktion zum Berechnen der Gesamtförderung
    def foederung_beg(self, daten: dict):
        bestandteile = ["Handwerker-Steuervorteil-BEG", "Heizung Grundfoerderung", 
                        "Heizung Klimageschwindigkeitsbonus", "Heizung Einkommensbonus", 
                        "Gebaeudehuelle BAFA-Foerderung", "Gebaeudehuelle Tilgungszuschuss KfW"]
        foerderung = 0
        for elem in bestandteile:
            wert = daten.get(elem)
            if wert is None:
                continue
            elif isinstance(wert, (int, float)):
                foerderung += wert
            else:
                continue
        
        return foerderung


    def foederung_geg(self, daten: dict):
        bestandteile = ["Handwerker-Steuervorteil-GEG"]
        foerderung = 0
        for elem in bestandteile:
            wert = daten.get(elem)
            if wert is None:
                continue
            elif isinstance(wert, (int, float)):
                foerderung += wert
            else:
                continue
        
        return foerderung
    
    
    # Klasenfunktion zur Berechnung der umlageberechtigten Investitionskosten; von der Investition müssen alle Fördersummen und Drittmittel abgezogen werden
    def umlageberechtigte_sanierungskosten(self, daten, sanierungskosten):
        wert = sanierungskosten - self.foederung_beg(daten)
        
        return wert
    
    
    # Klassenfunktion zur Berechnung der neuen Miete pro qm nach Sanierung und Umlage der Investitionskosten von max 8% pro Jahr, sowie Limit von 3 bzw. 2 €/m²
    def mietanpassung_saniert(self, wohnflaeche_mieter: float, miete_pro_qm: float, sanierungskosten: float):
        jahresumlage = sanierungskosten * (8 / 100)
        monatsumlage = jahresumlage / 12
        mietanpassung_saniert = (monatsumlage / wohnflaeche_mieter) + miete_pro_qm
        
        # Überprüfen, wie groß der Anstieg der sanierten Miete pro qm ist, falls >3 €/m² limitieren
        diff = mietanpassung_saniert - miete_pro_qm
        # Bei ausgehender Miete von <7 €/m² darf die Miete über die nächsten 6 Jahre höchstens 2 €/m² steigen
        if miete_pro_qm < 7 and diff > 2:
            mietanpassung_saniert = miete_pro_qm + 2
        # Bei ausgehender Miete von >=7 €/m² darf die Miete über die nächsten 6 Jahre höchstens 3 €/m² steigen
        elif miete_pro_qm >= 7 and diff > 3:
            mietanpassung_saniert = miete_pro_qm + 3
        
        return mietanpassung_saniert
    
    
    # Klassenfunktion zur Berechnung der Kredit-Parameter
    def kreditrechnung(self, sanierungskosten, kreditsumme, jahreszins, laufzeit, daten: dict):
        fremdkapital_quote = round(((kreditsumme + self.foederung_beg(daten)) / sanierungskosten) * 100, 2)
        eigenkapital_quote = round((1 - ((kreditsumme + self.foederung_beg(daten)) / sanierungskosten)) * 100, 2)
        
        annuitaetenfaktor = (((1 + jahreszins / 12) ** laufzeit) * (jahreszins / 12)) / (((1 + jahreszins / 12) ** laufzeit) - 1)
        annuitaet_rechnung = kreditsumme * annuitaetenfaktor
        annuitaet = round(annuitaet_rechnung, 2)
        
        gesamtaufwand = round(annuitaet_rechnung * laufzeit, 2)
        zinsaufwand = round(gesamtaufwand - kreditsumme, 2)
        
        return fremdkapital_quote, eigenkapital_quote, annuitaet, zinsaufwand, gesamtaufwand
    
    
# to run the above code as a script in here we need the following phrase. It prevents that the class/objects or functions from this file when used somewhere else run the following code.    
if __name__ == "__main__":
    """Test Ertragswert-Rechnung"""
    eigentuemer = Gebaeude(baujahr=1965)
    sanierungsbestandteile_list = [True, True, True, True, True, True, True, False]
    #Köln Deutz an TH, mit Mietspiegel 15,27€, Bodenrichtwert laut BORIS-D 1590€
    ertragswert_haus1 = eigentuemer.immobilienwert_ertragswert(bodenrichtwert=760, grundstuecksflaeche=1000, wohnflaeche=390, miete_qm=12.7, grundstuecksart=3, anzahl_wohnungen=5, maengel=0, saniert= False)
    #Köln Kalk Bodenrichtwert
    ertragswert_haus2 = eigentuemer.immobilienwert_ertragswert(bodenrichtwert=760, grundstuecksflaeche=1000, wohnflaeche=390, miete_qm=12.7, grundstuecksart=3, anzahl_wohnungen=5, maengel=0, saniert= True, sanierungsbestandteile_data=sanierungsbestandteile_list)

    # ertragswert_haus2 = eigentuemer.immobilienwert_ertragswert(930, 500, 120, 15.27, 0.2, 3, 5000, False)
    
    print("Der Ertragswert unsaniert betraegt:", round(ertragswert_haus1, 2), "€")
    print("Der Ertragswert saniert betraegt:", round(ertragswert_haus2, 2), "€")
    
    
    """Test restnutzungsdauer_saniert Funktion"""
    restnutzungsdauer_unsaniert = 80 - (2026 - 1965)
    print("Restnutzungsdauer ohne Sanierung:", restnutzungsdauer_unsaniert)
    restnutzungsdauer_saniert = eigentuemer.restnutzungsdauer_saniert(sanierungsbestandteile_list)
    print("Restnutzungsdauer nach Sanierung:", restnutzungsdauer_saniert)


    """Test Sachwert-Rechnung"""
    #Köln Deutz an TH, Bodenrichtwert laut BORIS-D an der TH 1590€
    # sachwert_haus1 = eigentuemer.immobilienwert_sachwert(bodenrichtwert=1590, grundstuecksflaeche=100, regelherstellungskosten=735, bruttogrundflaeche=300, marktanpassungsfaktor=1.3, saniert=False)
    # #Köln Kalk Bodenrichtwert
    # sachwert_haus2 = eigentuemer.immobilienwert_sachwert(930, 100, 735, 300, 1.3, False)
    
    # print("\nDer Sachwert von Haus1 betraegt:", round(sachwert_haus1, 2), "€")
    # print("Der Sachwert von Haus2 betraegt:", round(sachwert_haus2, 2), "€")
    
    # sachwert_saniert = eigentuemer.immobilienwert_sachwert(930, 100, 735, 300, 1.3, saniert=True)
    # print("Der Sachwert von Haus2 betraegt:", round(sachwert_saniert, 2), "€")
    
    
    """Test der gesamten Ertragswert-Rechnung mit Funktionsvariablen"""
    # bodenrichtwert=760
    # grundstuecksflaeche=1000
    # wohnflaeche=390
    # miete_qm=12.7
    # betriebskosten_qm = 2.36
    # grundstuecksart = 3
    # anzahl_wohnungen = 5
    # # faktor_bewirtschaftungskosten=0.2
    # # liegenschaftszins=3
    # maengel=0
    # saniert= True
    # baujahr = 1965
    # jahreszahl = 2026
    # gesamtnutzungsdauer = 80
    
    # restnutzungsdauer = gesamtnutzungsdauer - (jahreszahl - baujahr)
    
    # # Berechnung der Bruttokaltmiete aus miete_qm (Nettokaltmiete)
    # marktueblicher_mietwert_qm = miete_qm + betriebskosten_qm
    
    # # Ertragswert Ermittlung
    # bodenwert = bodenrichtwert * grundstuecksflaeche
    # rohertrag = wohnflaeche * marktueblicher_mietwert_qm * 12 # 12 Monate für ein Jahr
    
    # if saniert:
    #     restnutzungsdauer = Gebaeude(1965).restnutzungsdauer_saniert(sanierungsbestandteile_list)
    # else:
    #     restnutzungsdauer = restnutzungsdauer
    
    # bewirtschaftungskosten_faktor = Gebaeude(1965).bewirtschaftungskosten_faktor(grundstuecksart=grundstuecksart, restnutzungsdauer=restnutzungsdauer)
    # liegenschaftszins = Gebaeude(1965).liegenschaftszins(grundstuecksart=grundstuecksart, anzahl_wohnungen=anzahl_wohnungen, bodenrichtwert=bodenrichtwert)
    
    # betriebskosten_jahr = Gebaeude(1965).betriebskosten_jahr(wohnflaeche)
    # jahresreinertrag = rohertrag - (rohertrag * bewirtschaftungskosten_faktor) - betriebskosten_jahr # minus Instandhaltungskosten, Verwaltungskosten, Mietausfallwagnis, Betriebskosten (ImmoWertV § 32)
    # bodenwert_verzinsung = bodenwert * liegenschaftszins
    
    # # Vervielfältiger: Rechengröße, wie lange es dauert bis Investition durch Mieteinnahmen wieder ausgeglichen werden, Formel aus Bewertungsgesetz (BewG) Anlage 21 bzw. ImmoWertV §34 Absatz 2
    # vervielfaeltiger = (((1 + liegenschaftszins) ** restnutzungsdauer) - 1) / (((1 + liegenschaftszins) ** restnutzungsdauer) * ((1 + liegenschaftszins) - 1))
    
    # gebaeudeertragswert = (jahresreinertrag - bodenwert_verzinsung) * vervielfaeltiger
    # ertragswert_vorlaeufig = gebaeudeertragswert + bodenwert
    # immobilienwert_ertragswert = ertragswert_vorlaeufig - maengel
    
    # print("Der Ertragswert betraegt:", round(immobilienwert_ertragswert, 2), "€")
    
    
    """Test Förderungs-, Umlage- und Mietrechnungen"""
    # daten = {'Haushaltsstrom': 9000, 'Heizung & Warmwasser': 76500, 'CO2 Ausstoß': 17500, 'Energiebedarf': 220, 'Energieklasse': 'Energieklasse G', 'Energiekosten unsaniert': 11790, 'Energiekosten saniert': 5310, 'Sanierungskosten GEG': 102500, 'Sanierungskosten BEG': 119000, 'Handwerker-Steuervorteil': None, 'Heizung Grundfoerderung': 2500, 'Heizung Klimageschwindigkeitsbonus': 500, 'Gebaeudehuelle BAFA-Foerderung': 13500}
    # bestandteile = ["Handwerker-Steuervorteil", "Heizung Grundfoerderung", "Heizung Klimageschwindigkeitsbonus", "Gebaeudehuelle BAFA-Foerderung"]
    # sanierungskosten = 119000
    # miete = 9
    
    # foerderung = 0
    # for elem in bestandteile:
    #     wert = daten.get(elem)
    #     if wert is None:
    #         continue
    #     elif isinstance(wert, (int, float)):
    #         foerderung += wert
    #     else:
    #         continue
    # print("Gesamtförderung:", foerderung)

    # wert = sanierungskosten - eigentuemer.foederung_beg(daten)

    # print("Umlage-berechtigte Sanierungskosten:", wert)
    
    # mietspiegel_saniert = eigentuemer.mietanpassung_saniert(100, miete, wert)
    # print("Neue Miete pro qm:", mietspiegel_saniert)
    
    # anstiegsfaktor_sanierung = mietspiegel_saniert / miete
    # print("Anstiegsfaktor der Sanierung:", anstiegsfaktor_sanierung)
    
    # bewirtschaftungskosten= eigentuemer.bewirtschaftungskosten(2, 34)
    # print(bewirtschaftungskosten)
    
    """Test Kredit - Annuitätendarlehen Rechnung"""
    # kreditsumme = 100000
    # investition = 150000
    # jahreszins = 0.05
    # laufzeit = 120
    
    # fremdkapital_quote = kreditsumme / investition
    # eigenkapital_quote = 1 - (kreditsumme / investition)
    
    # annuitaetenfaktor = (((1 + jahreszins / 12) ** laufzeit) * (jahreszins / 12)) / (((1 + jahreszins / 12) ** laufzeit) - 1)
    # annuitaet = kreditsumme * annuitaetenfaktor
    
    # kredit_gesamtkosten = annuitaet * laufzeit
    # zinskosten = kredit_gesamtkosten - kreditsumme
    # Tilgungsplan für Annuitätendarlehen
    # zinsaufwand = 0
    # for x in range(1, laufzeit + 1):
    #     zinsbetrag = kreditsumme * (jahreszins / 12)
    #     tilgung = annuitaet - zinsbetrag
    #     kreditsumme -= tilgung
    #     zinsaufwand += zinsbetrag
    
    
    
    
        
        
    
