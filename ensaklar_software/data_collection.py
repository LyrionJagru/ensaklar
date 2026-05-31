# -*- coding: utf-8 -*-
"""
File for detection of data on imported image/file. 
Specific data from the renovation calculator should be detected.
Forming a part of the input data for the calculations.

@author: jbgru
"""

import os
import sys
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import re
from rapidfuzz import process, fuzz
from pathlib import Path



def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path

# Folgenden relativen Pfade sind für die Wrapper nötig
tesseract_exe = resource_path(r"external\tesseract\tesseract.exe")
tessdata_dir = resource_path(r"external\tesseract\tessdata")

pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
ocr_config = rf'--tessdata-dir "{tessdata_dir}"'

poppler_bin = resource_path(r"external\poppler\bin")



""" Optical Character Recognition OCR mit pytesseract für KfW-Bericht """

def preprocess_image(pil_img):
    """
    Säubert image: Grayscale, Otsu Thresholding (Binarization), Denoising
    """
    # Convert PIL to OpenCV format
    open_cv_image = np.array(pil_img)
    # Convert RGB to BGR
    img = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
    
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Thresholding (removes colored backgrounds like the green/blue headers)
    # cv2.THRESH_OTSU calculates the optimal threshold automatically
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. Denoising
    denoised = cv2.medianBlur(thresh, 3)
    
    return denoised

def ocr_pdf(pdf_path): 
    # Convert PDF pages to images - 300 DPI für OCR Genauigkeit
    pages = convert_from_path(pdf_path, 300, poppler_path=str(poppler_bin))
    
    full_text = ""
    
    # German language and PSM 3 (standard layout) or PSM 1 (sparse text layout)
    standard_txt_config = r'--oem 3 --psm 3 -l deu'
    table_txt_config = r'--oem 3 --psm 1 -l deu'
    
    for i, page_image in enumerate(pages):
        page_num = i + 1
        print(f"Processing Page {page_num}...")
        
        # Handle layout on Page 1 specifically, cutting off all unnecessary white space and text fields
        if page_num == 1:
            print("Detected Page 1: Cropping page for better accuracy....")
            width, height = page_image.size
            
            # Split image into chunks
            chunk_1 = page_image.crop((0, height * 0.4, width * 0.5, height * 0.75))
            # chunk_2 = page_image.crop((0, height * 0.75, width * 0.25, height)) # chunk 2 und 3 gelesene Information derzeit nicht genutzt
            # chunk_3 = page_image.crop((width * 0.25, height * 0.75, width * 0.5, height))
            chunk_4 = page_image.crop((width * 0.5, height * 0.827, width * 0.621, height * 0.865))
            chunk_5 = page_image.crop((width * 0.864, height * 0.846, width, height * 0.885))
            
            page_content = ""
            
            processed_col = preprocess_image(chunk_1)
            page_content += pytesseract.image_to_string(processed_col, config=standard_txt_config)
            # for column in [chunk_2, chunk_3]:
            #     processed_col = preprocess_image(column)
            #     page_content += pytesseract.image_to_string(processed_col, config=sparse_txt_config)
            processed_col = preprocess_image(chunk_4)
            page_content += "\nEnergiekosten unsaniert: " + pytesseract.image_to_string(processed_col, config=table_txt_config)
            processed_col = preprocess_image(chunk_5)
            page_content += "\nEnergiekosten saniert: " + pytesseract.image_to_string(processed_col, config=table_txt_config)
        
        # Handle the side-by-side layout on Page 3 specifically
        elif page_num in range(2, 4, 1):
            print(f"Detected Page {page_num}: Splitting columns for better accuracy...")
            width, height = page_image.size
            
            # Split image vertically in the middle
            left_col = page_image.crop((0, 0, width // 2, height))
            right_col = page_image.crop((width // 2, 0, width, height))
            
            page_content = ""
            for column in [left_col, right_col]:
                processed_col = preprocess_image(column)
                page_content += pytesseract.image_to_string(processed_col, config=table_txt_config)
        
        # Handle the large unnecessary text on Page 4, cutting off lower half
        elif page_num == 4:
            print("Detected Page 4: Cropping page for better accuracy...")
            width, height = page_image.size
            
            # Split image horizontal in the middle to cut off large text
            top_half = page_image.crop((0, height * 0.25, width // 2, height // 2))
            
            page_content = ""
            processed_col = preprocess_image(top_half)
            page_content += pytesseract.image_to_string(processed_col, config=standard_txt_config)
           
        # Skip page 5 as there is no valuable information
        elif page_num == 5:
            break
        
        else:
            # Standard processing for any other pages
            processed_img = preprocess_image(page_image)
            page_content = pytesseract.image_to_string(processed_img, config=standard_txt_config)
        
        full_text += f"\n--- PAGE {page_num} ---\n{page_content}"
        
    return full_text

def find_value_near_keyword(text, keyword, value_pattern=r"[\d\.]+", threshold=80, min_line_length=5, occurrence=1):
    """
    Finds a keyword (fuzzy) n-times and then looks for the nearest pattern (regex) after it.
    Example: keyword="Effektive Kosten", value_pattern=r"[\d\.]+ €"
    """
    # 1. Split text into lines to narrow the search and filter out very short lines
    all_lines = text.split('\n')
    lines = [ln for ln in all_lines if len(ln.strip()) >= min_line_length]
    
    if not lines:
        return None
    
    # 2. Use Fuzzy Matching to find the best matching line for our keyword
    # This handles OCR errors like "Eflektive Kosten" instead of "Effektive"
    matches = process.extract(keyword, lines, scorer=fuzz.partial_ratio, score_cutoff=threshold)
    
    if len(matches) < occurrence:
        print(f"Found only {len(matches)} matches for '{keyword}', need #{occurrence}")
        return None
    
    # 3. Get N-th best match (0 based index)
    best_match = matches[occurrence - 1]
    matched_line = best_match[0]
    print(f"Found #{occurrence}: '{matched_line}' for keyword '{keyword}' (score: {best_match[1]})")
        
    # 4. Use Regex to find the number/price in that line or the next line
    # We look for numbers like 109.000 or 57.865
    match = re.search(value_pattern, matched_line)
    if match:
        return match.group()
        
    return None

def find_keyword(text, keyword, start_keyword=None, threshold=80, min_line_length=5, occurrence=1):
    """
    Checks if a keyword exists (fuzzy) at least n-times in a text and returns True/False.
    """
    # 1. If start_keyword defined split large text into parts, keyword can be searched on GEG/BEG Vorschlag page, after start_keyword
    if start_keyword:
        parts = text.split(start_keyword, 1)
        if len(parts) > 1:
            text = parts[1]
        else:
            print(f"Start Keyword '{start_keyword}' not found in text!")
            return False
    
    # 2. Split text into lines to narrow the search and filter out very short lines
    all_lines = text.split('\n')
    lines = [ln for ln in all_lines if len(ln.strip()) >= min_line_length]
    
    if not lines:
        return False
    
    # 3. Use Fuzzy Matching to find the best matching lines for our keyword
    matches = process.extract(keyword, lines, scorer=fuzz.partial_ratio, score_cutoff=threshold)
    
    # 4. Check if we reached the required number of occurrences
    if len(matches) < occurrence:
        print(f"Found only {len(matches)} matches for '{keyword}', need #{occurrence}")
        return False
    
    # 5. Print the N-th match for debugging purposes
    best_match = matches[occurrence - 1]
    matched_line = best_match[0]
    print(f"Found #{occurrence}: '{matched_line}' for keyword '{keyword}' (score: {best_match[1]})")
        
    return True

def extract_specific_data(full_text):
    """
    Angepasste Extrahierung von gezielten Werten
    """
    print("\nSearching for data!")
    results_str = {}

    # Muster für Euro- und Energiewerte
    #euro_muster = r"[\d\.]+(?:,\d{2})?\s?€"
    # energieverbrauch_muster = r"~?[\d\.]+\s?kWh/a"
    euro_muster = r"\d{1,3}(?:\.\d{3})*\s*€"
    
    # Extrahieren aus vollem Text/String
    # Technische Werte aus Einleitung
    # results_str['Haushaltsstrom'] = find_value_near_keyword(full_text, "Haushaltsstrom:", energieverbrauch_muster)
    # results_str['Heizung & Warmwasser'] = find_value_near_keyword(full_text, "Heizung & Warmwasser", energieverbrauch_muster)
    # results_str['CO2 Ausstoß'] = find_value_near_keyword(full_text, "Ausstoß CO", r"~?[\d\.]+\s?kg/a")
    # results_str['Energiebedarf'] = find_value_near_keyword(full_text, "Endenergiebedarf", r"\d+\s?kWh/")
    # results_str['Energieklasse'] = find_value_near_keyword(full_text, "Energieklasse", r"Energieklasse\s+([A-H]\+?)")
    
    # Finanzielle Kennwerte
    results_str['Energiekosten unsaniert'] = find_value_near_keyword(full_text, "Energiekosten unsaniert", euro_muster)
    results_str['Energiekosten saniert'] = find_value_near_keyword(full_text, "Energiekosten saniert", euro_muster)

    results_str['Sanierungskosten GEG'] = find_value_near_keyword(full_text, "Summe", euro_muster, occurrence=1)
    results_str['Sanierungskosten BEG'] = find_value_near_keyword(full_text, "Summe", euro_muster, occurrence=2)
    
    # Förderungen
    results_str['Handwerker-Steuervorteil-GEG'] = find_value_near_keyword(full_text, "Steuervorteil", euro_muster, occurrence=1)
    
    results_str['Handwerker-Steuervorteil-BEG'] = find_value_near_keyword(full_text, "Steuervorteil", euro_muster, occurrence=2)
    results_str['Heizung Grundfoerderung'] = find_value_near_keyword(full_text, "Heizung Grund", euro_muster, occurrence=1)
    results_str['Heizung Klimageschwindigkeitsbonus'] = find_value_near_keyword(full_text, "Heizung Klimageschwind", euro_muster, occurrence=1)
    results_str['Heizung Einkommensbonus'] = find_value_near_keyword(full_text, "Heizung Einkommen", euro_muster, occurrence=1)
    results_str['Gebaeudehuelle BAFA-Foerderung'] = find_value_near_keyword(full_text, "Einzelmaßnahmen an", euro_muster, occurrence=1)
    results_str['Gebaeudehuelle Tilgungszuschuss KfW'] = find_value_near_keyword(full_text, "Tilgungszuschuss", euro_muster, occurrence=1)
    
    # Sanierungsmaßnahmen in Liste
    dachdammung = find_keyword(full_text, "dachdämmung", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "dachdammung", start_keyword="--- PAGE 3 ---")
    fensteraustausch = find_keyword(full_text, "Fensteraustausch", start_keyword="--- PAGE 3 ---")
    tuerenaustausch = find_keyword(full_text, "Eingangstüren", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Eingangsturen", start_keyword="--- PAGE 3 ---")
    leitungssysteme = find_keyword(full_text, "Dämmung des Heizungs", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Dammung des Heizungs", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "verteilleitungen", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Austausch Heizkreis", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Hydraulischer Abgleich", start_keyword="--- PAGE 3 ---")
    heizungsanlage = find_keyword(full_text, "wärmepumpe", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "warmepumpe", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "ärmepumpe", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "armepumpe", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Fernwärmestation", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Fernwarmestation", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Tausch Pellet­kessel", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Tausch Brenn­stoff", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "zellenheizung", start_keyword="--- PAGE 3 ---")
    außenwaende = find_keyword(full_text, "Außenwanddämmung", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Außenwanddammung", start_keyword="--- PAGE 3 ---")
    kellerdecke = find_keyword(full_text, "Kellerdeckendämmung", start_keyword="--- PAGE 3 ---") or find_keyword(full_text, "Kellerdeckendammung", start_keyword="--- PAGE 3 ---")
    effizienzhaus = find_keyword(full_text, "Effizienzhaus", start_keyword="--- PAGE 3 ---")
    
    # Liste mit Werten wie für Restnutzungsdauer-Funktion gebraucht befüllen
    results_str['Sanierungsmassnahmen'] = [
        leitungssysteme,
        heizungsanlage,
        dachdammung,
        fensteraustausch,
        tuerenaustausch,
        außenwaende,
        kellerdecke,
        effizienzhaus
        ]
    
    print("Data extracted!")
    return results_str

def convert_extracted_data(data_dict):
    """
    Konvertiere alle Strings, die Zahlenwerte abbilden, zu Float/Integer
    """
    results = {}
    
    for key, value in data_dict.items():
        num_str = re.match(r'^(\d{1,3}(?:\.\d{3})*)', str(value))
        if num_str:
            clean_num = num_str.group(1).replace('.', '') # ersetzt Tausender-Punkte mit nichts
            results[key] = int(clean_num)
        else:
            results[key] = value # behält vorigen Wert
            
    print(f"\nData converted!\n{results}")
    return results



if __name__ == "__main__":
    try:
        pfad = r"E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebaeude1.pdf"
        inhalt = ocr_pdf(pfad)
        file_name = os.path.basename(pfad)
        
        print(inhalt)
        
        data = extract_specific_data(inhalt)
            
        data_dict = convert_extracted_data(data)
        print(f"\n--- Data of file: {file_name} ---")
        for key, val in data_dict.items():
            print(f"{key}: {val if val else 'Not found'}")

    except Exception as e:
        print(f"An error occurred: {e}")
