1. Möglichkeit
 Falls die Software in einer IDE betrachtet werden soll, muss das Environment installiert werden. Es enthält alle nötigen Pakete. Außerdem sind im Ordner "External" die Tesseract-OCR Engine und Poppler enthalten. Falls es Fehler bezüglich diesen externen Paketen gibt, könnte eine extra Installation von der jeweiligen Engine sinnvoll sein. Pfade im Code entsprechend anpassen! 

-> main.py ausführen um die Software zu starten!


2. Möglichkeit
Um das Programm ohne eine IDE/Entwicklungsumgebung zu nutzen, das Environment installieren und mittels PyInstaller eine EXE erstellen.

Dazu die ensaklar.spec Datei nutzen.

In der Konsole in diesen Ordner "cd" navigieren und über Befehl "pyinstaller ensaklar.spec" die EXE generieren.

EXE wird in "dist" Ordner in diesem Ordner erstellt und kann dann frei genutzt werden.

Weitere PyInstaller-Anwendungen:

# Test-Ordner im Fenstermodus (ohne Konsole), Befehl:
pyinstaller --noconfirm --clean --onedir --windowed ^
--name Ensaklar_test ^
--collect-all PyQt5 ^
--collect-all cv2 ^
--collect-all reportlab ^
--hidden-import _rapidfuzz_cpp ^
--add-data "external\\tesseract\\tessdata;external\\tesseract\\tessdata" ^
--add-binary "external\\tesseract\\tesseract.exe;external\\tesseract" ^
--add-binary "external\\poppler\\bin;external\\poppler\\bin" ^
main.py

# Test-Ordner mit Debug Konsole, Befehl:
pyinstaller --noconfirm --clean --onedir ^
--name Ensaklar_debug ^
--collect-all PyQt5 ^
--collect-all cv2 ^
--collect-all reportlab ^
--hidden-import _rapidfuzz_cpp ^
--add-data "external\\tesseract\\tessdata;external\\tesseract\\tessdata" ^
--add-binary "external\\tesseract\\tesseract.exe;external\\tesseract" ^
--add-binary "external\\poppler\\bin;external\\poppler\\bin" ^
main.py

--> Für onefile bzw. EXE Erstellung die .spec Datei nutzen
--> mit pyinstaller <ensaklar>.spec erstellen (.spec von onedir auf onefile anpassen)