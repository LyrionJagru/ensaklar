# -*- coding: utf-8 -*-
"""
File for detection of data on imported image/file. 
Specific data from the renovation calculator should be detected.
Forming a part of the input data for the calculations.


object/class vs. function oriented code

- objects/classes are great for modelling real-world objects and modifiying those with methods.
- functions are great for data modification and a bit less complicated 

@author: jbgru
"""

# import tensorflow as tf
# import cv2
# import pymupdf
# import pprint

"""
KfW: 
- hat keinen Text der gelesen werden kann
- besteht rein aus Images, sowie jede Seite ist 

interhyp:
- hat teilweise TExt der gelesen werden kann

Wohnglück:
- ist lesbar da so gut wie alles Text aber chaotisch (Bezüge von Parametern zu Werten ist Chaos)
"""

# %% Funktioniert für wohnglück
import fitz  # PyMuPDF
import re
from pathlib import Path

def clean_page_text(raw: str) -> str:
    if not raw:
        return ""

    # 1. Weiche Umbrüche in Wörtern entfernen:
    #    "Wasserw\närmepumpe" -> "Wasserwärmepumpe"
    raw = re.sub(r"(\w)[\r\n]+(\w)", r"\1 \2", raw)

    # 2. Mehrfache Leerzeichen und Tabs normalisieren
    raw = re.sub(r"[ \t]+", " ", raw)

    # 3. Überflüssige Leerzeilen entfernen
    lines = [l.strip() for l in raw.splitlines()]
    lines = [l for l in lines if l]  # leere Zeilen raus
    return "\n".join(lines)

def extract_pdf_pretty(path: str | Path) -> str:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {path.resolve()}")

    doc = fitz.open(str(path))
    pages = []

    for page_index, page in enumerate(doc, start=1):
        # "text" ist bei deiner Datei geeignet; wenn nichts kommt, "blocks" probieren
        raw = page.get_text("text")
        if not raw:
            raw = page.get_text("blocks")

        cleaned = clean_page_text(raw)
        pages.append(f"--- SEITE {page_index} ---\n{cleaned}")

    return "\n\n".join(pages)


if __name__ == "__main__":
    # Achte darauf, dass der Pfad genau zu deiner Datei passt
    pdf_path = "E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\wohnglück-Gebäude2.pdf"  # ggf. Pfad anpassen (ohne Umlaut)
    text = extract_pdf_pretty(pdf_path)
    print(text)



# %% Optical Character REcognition OCR mit pytesseract für KfW

import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image

# Dieser Pfad ist notwendig, damit Tesseract als PATH gefunden werden kann
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(pil_img):
    """
    Cleans the image: Grayscale, Otsu Thresholding (Binarization), and Denoising.
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
    # Convert PDF pages to images (300 DPI is critical for OCR accuracy)
    pages = convert_from_path(pdf_path, 300)
    
    full_text = ""
    
    # German language and PSM 3 (standard layout)
    # PSM 6 is also good if you have single blocks of text
    custom_config = r'--oem 3 --psm 3 -l deu'
    
    for i, page_image in enumerate(pages):
        page_num = i + 1
        print(f"Processing Page {page_num}...")
        
        # Handle layout on Page 1 specifically, cutting off all unnecessary white space and text fields
        if page_num == 1:
            print("Detected Page 1: Cropping page for better accuracy....")
            width, height = page_image.size
            
            # Split image into chunks
            chunk_1 = page_image.crop((0, height * 0.4, width // 2, height))
            chunk_2 = page_image.crop((width // 2, height * 0.75, width, height))
            
            page_content = ""
            for column in [chunk_1, chunk_2]:
                processed_col = preprocess_image(column)
                page_content += pytesseract.image_to_string(processed_col, config=custom_config)
        
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
                page_content += pytesseract.image_to_string(processed_col, config=custom_config)
        
        # Handle the large unnecessary text on Page 4, cutting off lower half
        elif page_num == 4:
            print("Detected Page 4: Cropping page for better accuracy...")
            width, height = page_image.size
            
            # Split image horizontal in the middle to cut off large text
            top_half = page_image.crop((0, height * 0.25, width // 2, height // 2))
            
            page_content = ""
            processed_col = preprocess_image(top_half)
            page_content += pytesseract.image_to_string(processed_col, config=custom_config)
           
        # Skip page 5 as there is no valuable information
        elif page_num == 5:
            break
        
        else:
            # Standard processing for other pages
            processed_img = preprocess_image(page_image)
            page_content = pytesseract.image_to_string(processed_img, config=custom_config)
        
        full_text += f"\n--- PAGE {page_num} ---\n{page_content}"
        
    return full_text

# Usage
try:
    content = ocr_pdf("E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")
    print(content)
    # with open("extracted_text_improved.txt", "w", encoding="utf-8") as f:
    #     f.write(content)
    print("Extraction complete!")
except Exception as e:
    print(f"An error occurred: {e}")

#%%

# Dieser Pfad ist notwendig, damit Tesseract als PATH gefunden werden kann
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_pdf(pdf_path):
    # Convert PDF pages to images
    pages = convert_from_path(pdf_path, 300) # 300 DPI for high quality
    
    full_text = ""
    for i, page_image in enumerate(pages):
        print(f"OCR-ing Page {i+1}...")
        # Use German language pack (deu) since the document is in German
        text = pytesseract.image_to_string(page_image, lang='deu')
        full_text += f"\n--- PAGE {i+1} ---\n{text}"
        
    return full_text

# Usage
content = ocr_pdf("E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")
print(content)

"""
Liefert Ergebnisse!!!!!
"""

# %% Optical Character REcognition OCR mit pytesseract und PyMuPDF

# import os
# Pfad der tessdata variable zu sprach ordnern setzen bevor pymupdf gennutzt wird
# os.environ["TESSDATA_PREFIX"] = "C:\Program Files\Tesseract-OCR\tessdata"

import pymupdf

pdf = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")
#print(pdf.metadata)

# First, generate a pixmap object from a pdf page and save as png-file in dc
page0 = pdf.load_page(0)
pix_object0 = page0.get_pixmap()

extractable_pdf = pymupdf.open("pdf", pix_object0.pdfocr_tobytes(language="deu", tessdata=r"C:\Program Files\Tesseract-OCR\tessdata"))

extractable_page = extractable_pdf.load_page(0)

text = extractable_page.get_text("text", sort=True)
print(text)

"""
Liefert noch keine nützlichen Infos - Text wird nur zum Teil erkannt und oft auch falsch/Kauderwelsch!
"""


# %% Import pdf file and extract images
import pymupdf
from PIL import Image
import io
from IPython.display import display

pdf = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")

image = pdf.get_page_images(0)
for img in image:
    # to print image information: (xref_table reference number, type, width, height etc.)
    print(img) 
    
    # structure the information and the image type
    extracted = pdf.extract_image(img[0])
    print("ext:", extracted["ext"], "width:", extracted["width"], "height:", extracted["height"])

    # create a pillow image that can be displayed
    pil_image = Image.open(io.BytesIO(extracted["image"]))
    display(pil_image)
    

# %% alternative Methode for image extraction
import pymupdf
from PIL import Image
import io
from IPython.display import display

pdf = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")

# checking length of xref_table
lenXREF = pdf.xref_length()

# looping through the length of the xref_table and checking for type = images and extracting those
for xref in range(1, lenXREF):
    
    if pdf.xref_get_key(xref, "Subtype")[1] == "/Image":
        
        imgdata = pdf.extract_image(xref)
        
        pil_image = Image.open(io.BytesIO(imgdata["image"]))
        display(pil_image)


# %% Import pdf file and crop as specific area where text should be extracted from
import pymupdf

pdf = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\wohnglück-Gebäude2.pdf")

page = pdf.load_page(0)

# extrahiere zwei Rechtecke in denen die Begriffe gefunden werden
cropstart = page.search_for("Immobiliendaten")
cropend = page.search_for("Ausstoß")

for rect in cropstart:
    print(rect)

for rect in cropend:
    print(rect)

# erstelle Koordinaten einen neuen größeren Rechtecks
# Koordinaten können einfach modifiziert werden, um das Rechteck größer /kleiner zu machen
rx0 = cropstart[0].x0
ry0 = cropstart[0].y0

rx1 = cropend[0].x1 + 250
ry1 = cropend[0].y1

cr = pymupdf.Rect(rx0, ry0, rx1, ry1)

# nutze neues Rechteck um einen Ausschnitt des Textes zu machen, mittels "clip=", mit "sort=True" kann die natürliche Lesrichtung hergestellt werden
diagram = page.get_text(clip=cr, sort=True)
print(diagram)


# %% Import pdf file, check for text and image blocks as well as fonts used
# When NO text is used OCR (Optical Character Recognition) needs to be performed before extraction
import pymupdf

pdf = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")

txtblocks = 0
imgblocks = 0
docfonts = []

for page in pdf:
    text = page.get_text("dict")
    for block in text["blocks"]:
        if block["type"] == 0:
            txtblocks += 1
        elif block["type"] == 1:
            imgblocks += 1
    pagefonts = page.get_fonts()
    for font in pagefonts:
        if font[3] not in tuple(docfonts):
            docfonts.append(font[3])

print("Text blocks:", txtblocks, "\nImage blocks:", imgblocks, "\nFonts in pdf:", len(docfonts))
for font in docfonts:
    print(font)
    
pdf.close()


"""
ERGEBNISSE:
    
# KfW:          Text blocks: 0, Image blocks: 4, Fonts in pdf: 14   -> keinen TExt, nur Images
# wohnglück:    Text blocks: 98, Image blocks: 7, Fonts in pdf: 14  -> viel von beidem, aber viel Information im Text
# interhyp:     Text blocks: 43, Image blocks: 8, Fonts in pdf: 2   -> dito, aber auf viel Info in Images
"""

# %% Import pdf file page, create pix_object and save as png file
import pymupdf

kfw_bericht = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\KfW-Gebäude1.pdf")

# Generate a pixmap object from a pdf page and save as png-file in dc
page0 = kfw_bericht.load_page(0)
pix_object0 = page0.get_pixmap()
pix_object0.save("test.png") # other image types possible than png


# %% Import pdf file and read as json
import pymupdf

kfw_bericht = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\wohnglück-Gebäude2.pdf")
page = kfw_bericht.load_page(0)
text = page.get_text("json")
print(text)


# %% Import pdf file and search for specific text
import pymupdf

kfw_bericht = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\wohnglück-Gebäude2.pdf")
page = kfw_bericht.load_page(0)
areas = page.search_for("wohnglück")
print(areas)
# results in a rectangle list in areas


# %% Import pdf file and extract all text from pages
import pymupdf

kfw_bericht = pymupdf.open(filename="E:\Github_Repos\MA_Thesis\Sanierungsrechner_Ergebnisse\wohnglück-Gebäude2.pdf")

# Extract text from all pages
full_text = ""
for page_num in range(len(kfw_bericht)):
    page = kfw_bericht.load_page(page_num)  # or doc[page_num]
    text = page.get_text("text", sort=True)
    full_text += f"--- Page {page_num + 1} ---\n{text}\n\n"

print(full_text)

# Close the document
kfw_bericht.close()


# to run the above code as a script in here we need the following phrase. It prevents that the class/objects or functions from this file when used somewhere else run the following code.    
# if __name__ == "__main__":
#     sanierungsrechner_ergebnisse()
    
        