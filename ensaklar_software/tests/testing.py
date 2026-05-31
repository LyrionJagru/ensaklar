
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 13:17:14 2026

@author: jbgru
"""

from datetime import date

jahreszahl = date.today().year #jetziges Jahr
years = []
for val in range(0, 15, 1):
    jahreszahl += 1
    years.append(str(jahreszahl))

    
# %%
from PyQt5.QtWidgets import QApplication, QTextBrowser
import sys

app = QApplication(sys.argv)

browser = QTextBrowser()
browser.setHtml("""
    <h3>Links</h3>
    <p><a href="https://www.python.org">Python</a></p>
    <p><a href="https://www.qt.io">Qt</a></p>
""")
browser.setOpenExternalLinks(True)

browser.show()
sys.exit(app.exec_())

# %%
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import Qt
import sys

app = QApplication(sys.argv)

label = QLabel()
label.setText('<a href="https://www.google.com">Open Google</a>')
label.setOpenExternalLinks(True)          # open in default browser
label.setTextInteractionFlags(Qt.TextBrowserInteraction)
label.setAlignment(Qt.AlignCenter)

label.show()
sys.exit(app.exec_())

# %%
import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

import data_calculations

gebaeude = data_calculations.Gebaeude(1970)

betriebskosten = gebaeude.betriebskosten_jahr(100)
betr_kosten_anpassung = [betriebskosten]
for jahr in range(2, 15 + 1):
    betr_kosten_anpassung.append(round(betr_kosten_anpassung[-1] * (1 + 0.02), 2))
    
# %%
import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
import data_calculations

betrachtungszeitraum = 20
mietanstieg = 0.02
betriebskostenanstieg = 0.02
energiepreis_entwicklung = 0.04

check_reelle_miete = True
reelle_miete = 12
mietspiegel = 12
miete_saniert = 15
wohnfläche = 100
kappungsgrenze = 0.15

gebaeude = data_calculations.Gebaeude(1970)

# Betriebskosten
# betriebskosten = gebaeude.betriebskosten_jahr(100)
# betr_kosten_reihe_saniert = [betriebskosten]
# for jahr in range(1, betrachtungszeitraum + 1):
#     betr_kosten_reihe_saniert.append(round(betriebskosten * ((1 + betriebskostenanstieg) ** (jahr)), 2))
# betr_kosten_reihe_unsaniert = betr_kosten_reihe_saniert

# Nettokaltmiete
# Preisentwicklung ortsübliche Vergleichsmiete/ Mietspiegel Faktoren
anstiegsfaktoren = []
for x in range(betrachtungszeitraum):
    anstiegsfaktoren.append((1 + mietanstieg) ** x)
# Prüfen, ob Kappungsgrenze innerhalb 3-Jahreszeitraum durch Mietpreisentwicklung (Neue Verträge) überschritten wird
diff_kappungsgrenze = kappungsgrenze - ((anstiegsfaktoren[3] / anstiegsfaktoren[0]) - 1)
    
nettokaltmiete_mietspiegel = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=mietspiegel) * 12
nettokaltmiete_unsaniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=reelle_miete) * 12
nettokaltmiete_saniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=miete_saniert) * 12

# reelle Miete wurde eingegeben
if check_reelle_miete is True:
    # SANIERTE Nettokaltmiete Reihen
    quotient_saniertmiete_mietspiegel = miete_saniert / mietspiegel
    # <1: sanierte miete < mietspiegel; >1: sanierte miete > mietspiegel
    
    # sanierte Miete > Mietspiegel
    if quotient_saniertmiete_mietspiegel > 1:
        jahr_anstieg_mgl = next((index for index, faktor in enumerate(anstiegsfaktoren) if faktor > quotient_saniertmiete_mietspiegel), None)
        if jahr_anstieg_mgl is None:
            # Stellt sicher, dass Datensatz-Erstellung unten funktioniert
            jahr_anstieg_mgl = betrachtungszeitraum
        
        nettokaltmiete_reihe_saniert = []
        for x in range(jahr_anstieg_mgl):
            nettokaltmiete_reihe_saniert.append(nettokaltmiete_saniert)
        for x in range(jahr_anstieg_mgl, betrachtungszeitraum):
            relative_x = x - jahr_anstieg_mgl
            if diff_kappungsgrenze > 0:
                # hier "%" weil alle 3 Jahre faktor neu berechnet mit x == entsprechendes Jahr
                if relative_x % 3 == 0:
                    faktor = (1 + mietanstieg) ** x
                    mietniveau = nettokaltmiete_mietspiegel * faktor
                nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
            elif diff_kappungsgrenze < 0:
                # hier "//" weil alle 3 Jahre Faktor + 1 [0, 0, 0, 1, 1, 1, 2, 2, 2 etc.]
                dreijahresblock = relative_x // 3
                faktor = ((1 + kappungsgrenze) ** dreijahresblock)
                mietniveau = (nettokaltmiete_mietspiegel * ((1 + mietanstieg) ** jahr_anstieg_mgl)) * faktor
                nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
        
    # sanierte Miete < Mietspiegel
    elif quotient_saniertmiete_mietspiegel <= 1:
        # Prüfen: Erreicht Anstieg mit Kappungsgrenze Niveau von Mietspiegel: Ja/Nein? Wenn ja wann? Ist immer eine Vielzahl von 3, da in 3er Blöcken erhöht wird
        anstiegsfaktoren_bis_mietspiegel = []
        for x in range(betrachtungszeitraum):
            dreijahresblock = x // 3
            faktor = quotient_saniertmiete_mietspiegel * ((1 + kappungsgrenze) ** dreijahresblock)
            anstiegsfaktoren_bis_mietspiegel.append(faktor)
        jahr_mietspiegel_erreicht = next((index for index, (x, y) in enumerate(zip(anstiegsfaktoren, anstiegsfaktoren_bis_mietspiegel)) if y > x), None)
        # falls die Mietspiegel-Entwicklung zu groß (>=5 % pro Jahr bei 15% Kappungsgrenze) ist, kann diese nicht erreicht werden
        if jahr_mietspiegel_erreicht is None:
            jahr_mietspiegel_erreicht = betrachtungszeitraum
        
        # Nun Nettokaltmiete-Reihe erstellen mit 
        # Ab dem Jahr wo das Niveau des Mietspiegel erreicht wird, Mietspiegelentwicklung übernehmen alle 3 Jahre
        nettokaltmiete_reihe_saniert = []
        for x in range(jahr_mietspiegel_erreicht):
            dreijahresblock = x // 3
            mietniveau = nettokaltmiete_saniert * ((1 + kappungsgrenze) ** dreijahresblock)
            nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
        # wird nicht ausgeführt wenn jahr_mietspiegel_erreicht == betrachtungszeitraum
        for x in range(jahr_mietspiegel_erreicht, betrachtungszeitraum):
            if x % 3 == 0:
                faktor = (1 + mietanstieg) ** x
                mietniveau = nettokaltmiete_mietspiegel * faktor
            nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
    
    # UNSANIERTE Nettokaltmiete Reihen
    quotient_miete_mietspiegel = reelle_miete / mietspiegel
    # <1: reelle miete < mietspiegel; >1: reelle miete > mietspiegel
    
    # Unsaniert und reelle Miete > Mietspiegel
    if quotient_miete_mietspiegel > 1:
        # Prüfen ob und in welchem Jahr Mieterhöhung möglich mit Preisentwicklung ortsübliche Vergleichsmiete/ Mietspiegel Faktoren
        jahr_anstieg_mgl = next((index for index, faktor in enumerate(anstiegsfaktoren) if faktor > quotient_miete_mietspiegel), None)
        if jahr_anstieg_mgl is None:
            # Stellt sicher, dass Datensatz-Erstellung unten funktioniert
            jahr_anstieg_mgl = betrachtungszeitraum
        
        nettokaltmiete_reihe_unsaniert = []
        for x in range(jahr_anstieg_mgl):
            nettokaltmiete_reihe_unsaniert.append(nettokaltmiete_unsaniert)
        for x in range(jahr_anstieg_mgl, betrachtungszeitraum):
            relative_x = x - jahr_anstieg_mgl
            if diff_kappungsgrenze > 0:
                # hier "%" weil alle 3 Jahre faktor neu berechnet mit x == entsprechendes Jahr
                if relative_x % 3 == 0:
                    faktor = (1 + mietanstieg) ** x
                    mietniveau = nettokaltmiete_mietspiegel * faktor
                nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
            elif diff_kappungsgrenze < 0:
                # hier "//" weil alle 3 Jahre Faktor + 1 [0, 0, 0, 1, 1, 1, 2, 2, 2 etc.]
                dreijahresblock = relative_x // 3
                faktor = ((1 + kappungsgrenze) ** dreijahresblock)
                mietniveau = (nettokaltmiete_mietspiegel * ((1 + mietanstieg) ** jahr_anstieg_mgl)) * faktor
                nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
                
    # Unsaniert und reelle Miete < Mietspiegel
    elif quotient_miete_mietspiegel <= 1:
        # Prüfen: Erreicht Anstieg mit Kappungsgrenze Niveau von Mietspiegel: Ja/Nein? Wenn ja wann? Ist immer eine Vielzahl von 3, da in 3er Blöcken erhöht wird
        anstiegsfaktoren_bis_mietspiegel = []
        for x in range(betrachtungszeitraum):
            dreijahresblock = x // 3
            faktor = quotient_miete_mietspiegel * ((1 + kappungsgrenze) ** dreijahresblock)
            anstiegsfaktoren_bis_mietspiegel.append(faktor)
        jahr_mietspiegel_erreicht = next((index for index, (x, y) in enumerate(zip(anstiegsfaktoren, anstiegsfaktoren_bis_mietspiegel)) if y > x), None)
        # falls die Mietspiegel-Entwicklung zu groß (>=5 % pro Jahr bei 15% Kappungsgrenze) ist, kann diese nicht erreicht werden
        if jahr_mietspiegel_erreicht is None:
            jahr_mietspiegel_erreicht = betrachtungszeitraum
        
        # Nun Nettokaltmiete-Reihe erstellen mit 
        # Ab dem Jahr wo das Niveau des Mietspiegel erreicht wird, Mietspiegelentwicklung übernehmen alle 3 Jahre
        nettokaltmiete_reihe_unsaniert = []
        for x in range(jahr_mietspiegel_erreicht):
            dreijahresblock = x // 3
            mietniveau = nettokaltmiete_unsaniert * ((1 + kappungsgrenze) ** dreijahresblock)
            nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
        # wird nicht ausgeführt wenn jahr_mietspiegel_erreicht == betrachtungszeitraum
        for x in range(jahr_mietspiegel_erreicht, betrachtungszeitraum):
            if x % 3 == 0:
                faktor = (1 + mietanstieg) ** x
                mietniveau = nettokaltmiete_mietspiegel * faktor
            nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
            
    # damit Jahr 0 bzw. der Ausgangsfall angezeigt wird
    nettokaltmiete_reihe_unsaniert.insert(0, nettokaltmiete_unsaniert)
    nettokaltmiete_reihe_saniert.insert(0, nettokaltmiete_unsaniert)
    
# nur Mietspiegel wurde angegeben
else:
    print("Der Code dazu ist der in der nächsten Zelle :D")
    
    

#%%
import os
import sys
file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)
from operator import add
import data_calculations

betrachtungszeitraum = 20
mietanstieg = 0.02
betriebskostenanstieg = 0.02
energiepreis_entwicklung = 0.04

mietspiegel = 15
miete_saniert = 18
wohnfläche = 100
kappungsgrenze = 0.2

gebaeude = data_calculations.Gebaeude(1970)

# Betriebskosten
betriebskosten = gebaeude.betriebskosten_jahr(100)
betr_kosten_reihe_saniert = [betriebskosten]
for jahr in range(1, betrachtungszeitraum + 1):
    betr_kosten_reihe_saniert.append(round(betriebskosten * ((1 + betriebskostenanstieg) ** (jahr)), 2))
betr_kosten_reihe_unsaniert = betr_kosten_reihe_saniert

# Nettokaltmiete
# SANIERT
# Preisentwicklung ortsübliche Vergleichsmiete Faktoren
anstiegsfaktor_sanierung = miete_saniert / mietspiegel
anstiegsfaktoren = []
for x in range(betrachtungszeitraum):
    anstiegsfaktoren.append((1 + mietanstieg) ** x)
jahr_anstieg_mgl = next((index for index, faktor in enumerate(anstiegsfaktoren) if faktor > anstiegsfaktor_sanierung), None)
if jahr_anstieg_mgl is None:
    # Stellt sicher, dass Datensatz-Erstellung unten funktioniert
    jahr_anstieg_mgl = betrachtungszeitraum
else:
    pass

# Prüfen, ob Kappungsgrenze/Mietpreisbremse innerhalb 3-Jahreszeitraum durch Mietpreisentwicklung (Neue Verträge) überschritten wird
diff_kappungsgrenze = kappungsgrenze - ((anstiegsfaktoren[3] / anstiegsfaktoren[0]) - 1)

nettokaltmiete_saniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=miete_saniert) * 12
nettokaltmiete_unsaniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=mietspiegel) * 12
nettokaltmiete_reihe_saniert = []
for x in range(jahr_anstieg_mgl):
    nettokaltmiete_reihe_saniert.append(nettokaltmiete_saniert)
for x in range(betrachtungszeitraum - jahr_anstieg_mgl):
    nettokaltmiete_reihe_saniert.append(nettokaltmiete_unsaniert)

if jahr_anstieg_mgl < betrachtungszeitraum:
    if diff_kappungsgrenze > 0:
        index = jahr_anstieg_mgl
        faktor = anstiegsfaktoren[index]
        for dreijahresblock_start in range(jahr_anstieg_mgl, betrachtungszeitraum, 3):
            dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
            # Ganzen 3er Jahresblock mit Anstiegsfaktor multiplizieren
            nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende] = [round(v * faktor, 4) for v in nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende]]
            try:
                index += 3
                faktor = anstiegsfaktoren[index]
            except:
                pass
    # bei überschreiten der kappungsgrenze Miete_saniert mit Kappungsgrenze multiplizieren
    elif diff_kappungsgrenze < 0:
        letzter_nettokaltmiete_wert = nettokaltmiete_reihe_saniert[jahr_anstieg_mgl - 1]
        zaehler = 1
        for dreijahresblock_start in range(jahr_anstieg_mgl, betrachtungszeitraum, 3):
            dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
            neue_nettokaltmiete_kappgrenze = letzter_nettokaltmiete_wert * ((1 + kappungsgrenze) ** zaehler)
            nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende] = [round((v - v) + neue_nettokaltmiete_kappgrenze, 2) for v in nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende]]
            zaehler += 1
nettokaltmiete_reihe_saniert.insert(0, nettokaltmiete_unsaniert)


# UNSANIERT
nettokaltmiete_unsaniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=wohnfläche, miete_qm=mietspiegel) * 12
nettokaltmiete_reihe_unsaniert = []
for x in range(betrachtungszeitraum):
    nettokaltmiete_reihe_unsaniert.append(nettokaltmiete_unsaniert)

if diff_kappungsgrenze > 0:
    index = 0
    faktor = anstiegsfaktoren[index]
    for dreijahresblock_start in range(0, betrachtungszeitraum, 3):
        dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
        # Ganzen 3er Jahresblock mit Anstiegsfaktor multiplizieren
        nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende] = [round(v * faktor, 2) for v in nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende]]
        try:
            index += 3
            faktor = anstiegsfaktoren[index]
        except:
            pass
# bei überschreiten der kappungsgrenze Miete_saniert mit Kappungsgrenze multiplizieren
elif diff_kappungsgrenze < 0:
    zaehler = 1
    for dreijahresblock_start in range(0, betrachtungszeitraum, 3):
        dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
        nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende] = [round(v * (1 + kappungsgrenze) ** zaehler, 2) for v in nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende]]
        zaehler += 1
nettokaltmiete_reihe_unsaniert.insert(0, nettokaltmiete_unsaniert)


# Addieren beiden Datenreihen: Nettokaltmiete + Betriebskosten für Warmmiete Diagramm
bruttokaltmiete_reihe_saniert = list(map(add, nettokaltmiete_reihe_saniert, betr_kosten_reihe_saniert))
bruttokaltmiete_reihe_unsaniert = list(map(add, nettokaltmiete_reihe_unsaniert, betr_kosten_reihe_unsaniert))

nebenkosten_saniert = gebaeude.nebenkosten(2070)
nebenkosten_unsaniert = gebaeude.nebenkosten(17870)

bruttokaltmiete_pro_monat_reihe_saniert = [jahr / 12 for jahr in bruttokaltmiete_reihe_saniert]
bruttokaltmiete_pro_monat_reihe_unsaniert = [jahr / 12 for jahr in bruttokaltmiete_reihe_unsaniert]
nebenkosten_reihe_saniert = [round(nebenkosten_unsaniert, 2), round(nebenkosten_saniert, 2)]
for x in range(1, betrachtungszeitraum):
    nebenkosten_reihe_saniert.append(round(nebenkosten_reihe_saniert[1] * ((1 + energiepreis_entwicklung) ** x), 2))
nebenkosten_reihe_unsaniert = [round(nebenkosten_unsaniert, 2)]
for x in range(betrachtungszeitraum):
    nebenkosten_reihe_unsaniert.append(round(nebenkosten_reihe_unsaniert[0] * ((1 + energiepreis_entwicklung) ** x), 2))


# %%
from itertools import accumulate

amortisation_reihe = [0]
liste = [1, 2, 3, 4, 5, 6, 7, 8, 9]
# Akkumulieren der Nettokaltmieten über die Jahre
nettokaltmiete_reihe_akkumuliert = list(accumulate(liste))
amortisation_reihe.extend(nettokaltmiete_reihe_akkumuliert)

# %%
jahreszahl = 0
years = []
for x in range(20 + 1):
    years.append(jahreszahl)
    jahreszahl += 1
    
        
        
        
        
