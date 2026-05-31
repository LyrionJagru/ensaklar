# -*- coding: utf-8 -*-
"""
Prototyp

Combination of image recognition, data collection and calculation.

@author: jbgru
"""

import os
import data_collection as datacol
from data_calculations import Gebaeude


try:
    pfad = r"C:\Users\jbgru\Documents\GitHub\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW_paulstraße7bonn.pdf"
    inhalt = datacol.ocr_pdf(pfad)
    file_name = os.path.basename(pfad)
    print("\n-----     ------     -----", inhalt, "\n-----     ------     -----")
    
    data = datacol.extract_specific_data(inhalt)
        
    data_dict = datacol.convert_extracted_data(data)
    print(f"\n--- Data of file: {file_name} ---")
    for key, val in data_dict.items():
        print(f"{key}: {val if val else 'Not found'}")
    
    
    print("\n--- Ergebnisse der Berechnung ---")
    immobilie = Gebaeude(baujahr=1970)
    ertragswert_haus = immobilie.immobilienwert_ertragswert(bodenrichtwert=780, grundstuecksflaeche=300, wohnflaeche=300, marktueblicher_mietwert_qm=14.5, faktor_bewirtschaftungskosten=0.2, liegenschaftszins=3, maengel=0, saniert=False)
    print("Der Ertragswert vom Haus betraegt:", round(ertragswert_haus, 2), "€")
    
    restnutzungsdauer_saniert = immobilie.restnutzungsdauer_saniert([True,True,True,False,False,False,True,True])
    print("Restnutzungsdauer nach Sanierung:", round(restnutzungsdauer_saniert, 3), "Jahre")
    ertragswert_haus = immobilie.immobilienwert_ertragswert(bodenrichtwert=780, grundstuecksflaeche=300, wohnflaeche=300, marktueblicher_mietwert_qm=14.5, faktor_bewirtschaftungskosten=0.2, liegenschaftszins=3, maengel=0, saniert=True)
    print("Der Ertragswert vom Haus betraegt:", round(ertragswert_haus, 2), "€")
    
    kaltmiete_unsaniert = immobilie.kaltmiete(wohnflaeche_mieter=100, miete_pro_qm=14.5)
    kaltmiete_saniert = immobilie.kaltmiete_saniert(wohnflaeche_mieter=100, miete_pro_qm=14.5, sanierungskosten=data_dict["Sanierungskosten_BEG"])
    print("Die Kaltmiete für die unsanierte Wohnung beträgt:", round(kaltmiete_unsaniert, 2), "€")
    print("Die neue Kaltmiete nach der Sanierung beträgt:", round(kaltmiete_saniert, 2), "€")
    
    nebenkosten_unsaniert = immobilie.nebenkosten(energiekosten=data_dict["Energiekosten unsaniert"])
    nebenkosten_saniert = immobilie.nebenkosten(energiekosten=data_dict["Energiekosten saniert"])
    print("Die Nebenkosten für die unsanierte Wohnung betragen:", round(nebenkosten_unsaniert, 2), "€")
    print("Die Nebenkosten nach der Sanierung sinken auf:", round(nebenkosten_saniert, 2), "€")
    
except Exception as e:
    print(f"An error occurred: {e}")
    
    

    





