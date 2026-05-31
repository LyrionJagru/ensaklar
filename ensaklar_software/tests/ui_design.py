# -*- coding: utf-8 -*-
"""
File for UI creation and pdf export of the tool using PySide6 packages.

@author: jbgru
"""
    
import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
)
import data_calculations


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Immobilien-Berechnung")

        # Widgets
        self.describtion_label = QLabel("Gib das Baujahr der Immobilie ein, um den Sachwert abzuschätzen.")
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Baujahr eingeben...")

        self.run_button = QPushButton("Funktion ausführen")
        self.result_label = QLabel("Ergebnis erscheint hier")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.describtion_label)
        layout.addWidget(self.input_edit)
        layout.addWidget(self.run_button)
        layout.addWidget(self.result_label)
        self.setLayout(layout)

        # Signal → Slot: Button-Klick ruft Methode auf
        self.run_button.clicked.connect(self.immobilienwert)


    def immobilienwert(self):
        # Baujahr abfragen und in Int umwandeln
        baujahr = int(self.input_edit.text())
        
        # Immobilienwert Berechnung
        eigentuemer = data_calculations.Stakeholder(baujahr)
        #Köln Deutz an TH, Bodenrichtwert laut BORIS-D an der TH 1590€
        sachwert_haus1 = eigentuemer.immobilienwert_sachwert(bodenrichtwert=1590, grundstuecksflaeche=100, regelherstellungskosten=735, bruttogrundflaeche=300, marktanpassungsfaktor=1.3, saniert=False)
        #Köln Kalk Bodenrichtwert
        sachwert_haus2 = eigentuemer.immobilienwert_sachwert(930, 100, 735, 300, 1.3, False)
        
        # String mit Ergebnissen erstellen und result_label den Str übergeben
        ergebnis = "\nDer Sachwert von Haus1 betraegt: " + str(round(sachwert_haus1, 2)) + "€" + "\nDer Sachwert von Haus2 betraegt: " + str(round(sachwert_haus2, 2)) + "€"
        self.result_label.setText(ergebnis)



if __name__ == "__main__":
    # Sichere App-Erzeugung, sodass nach Windowschließen ein neuer Prozess gestartet werden kann
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(True)

    window = MainWindow()
    window.resize(600, 400)
    window.show()

    sys.exit(app.exec())

