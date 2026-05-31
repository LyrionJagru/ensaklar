# -*- coding: utf-8 -*-
"""
File for UI creation and pdf export of the tool using PyQt5 and ReportLab packages.

@author: jbgru
"""
    
import sys
import os
import io
import math
from datetime import datetime, date
from operator import add, sub
from itertools import accumulate
from PyQt5.QtChart import (QChart, QChartView, QLineSeries, QBarSet, QBarSeries, 
                           QStackedBarSeries, QBarCategoryAxis, QCategoryAxis)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QStandardPaths, QRectF, 
                          QBuffer, QIODevice, QCoreApplication, QProcess)
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QFont, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTextEdit, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QGroupBox, QFormLayout, QGridLayout, 
                             QProgressBar, QLineEdit, QComboBox, QMessageBox,
                             QCheckBox, QDoubleSpinBox, QSpinBox)
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Image, Spacer, 
                                PageBreak, KeepTogether, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
import data_collection
import data_calculations



class OCRWorker(QThread):
    """Thread to handle heavy OCR tasks without freezing the UI."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)

    def __init__(self, datei_pfad):
        super().__init__()
        self.datei_pfad = datei_pfad

    def run(self):
        self.progress.emit("Konvertiere PDF und erkenne Dateninhalt...")
        inhalt = data_collection.ocr_pdf(self.datei_pfad)
        
        data = data_collection.extract_specific_data(inhalt)
            
        data_dict = data_collection.convert_extracted_data(data)
        
        results = {"rohtext": inhalt,
                   "daten_str": data,
                   "daten_int": data_dict}
        
        self.finished.emit(results)
        


class EnsaklarApp(QMainWindow):
    BETRACHTUNGSZEITRAUM = 20 # Zeitraum in Jahren für Diagramme
    INFLATION = 0.021 # Inflationsprognose der Bundesbank (Verbraucherpreisentwicklung)
    BESTANDSMIETEN_ENTWICKLUNG = 0.02 # Verbraucherpreis-Index für Wohnen/Mieten DSTATIS
    ENERGIEPREIS_ENTWICKLUNG = 0.04 # Verbraucherpreis-Index für Strom, Gas und andere Brennstoffe DSTATIS
    
    def __init__(self):
        """Master-Funktion für das gesamte Layout"""
        super().__init__()
        self.setWindowIcon(QIcon('window_icons/app_icon.ico'))
        self.setWindowTitle("Ensaklar")
        self.resize(1920, 1080)
        
        # Zentrale Info-Box
        self.info_header = QLabel()
        self.info_header.setStyleSheet("""
            color: black;
            border: 2px solid #5b9bd5;
            border-radius: 6px;
            padding: 10px;
        """) # "background-color: #d0e8ff;"
        self.info_header.setWordWrap(True)
        self.info_header.setTextFormat(Qt.RichText)
        self.info_header.setText(
            "<p style='margin-bottom:0.1pt;'><span style='font-size:12pt;'>Haben Sie schon eine Sanierung Ihres Gebäudes mit dem KfW-Sanierungsrechner berechnet? Falls nicht, tun Sie dies <a href='https://sanierungsrechner.kfw.de/'>hier</a>.<\span></p>"
            "<span style='font-size:8pt;'><br><b>Achtung:</b> Für eine genauere Berechnung der Sanierungskennwerte sollte <b>keine</b> PV-Anlage als Maßnahme im KfW-Sanierungsrechner ausgewählt sein!<\span>"
        )
        self.info_header.setOpenExternalLinks(True)
        
        # Linke Spalte: Eingabefelder und Info-Links
        self.left_panel = QVBoxLayout()
        self.setup_ocr_reader_group()
        self.setup_ocr_output_tabs()
        self.setup_correction_input_group()
        self.setup_manual_input_group()
        self.setup_programm_control_buttons_group()
        
        # Rechte Spalte: Ausgabe Rechenergebnisse und Diagramme
        self.right_panel = QVBoxLayout()
        self.setup_calculation_results_group()
        self.setup_results_chart_tabs()
        self.setup_end_group()
        
        # beide Spalten kombinieren
        self.column_layout = QHBoxLayout()
        self.column_layout.addLayout(self.left_panel, 2)
        self.column_layout.addLayout(self.right_panel, 3)
        
        # Infobox oben und Spalten darunter kombinieren
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.info_header)
        main_layout.addLayout(self.column_layout)
        
        # Main Layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Master-Daten-Halter
        self.input_data_dict = {}
        self.result_data_dict = {}
        
    # UI-Gruppen/Felder
    def setup_ocr_reader_group(self):
        """Gruppe für die pdf-Datei Auswahl und OCR-Start"""
        group = QGroupBox("1. PDF-Eingabe und Datenerkennung")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            font-size: 10pt;
        }
        """)    
        layout = QFormLayout(group)
        
        self.btn_browse = QPushButton("PDF Datei auswählen")
        self.btn_browse.clicked.connect(self.open_file)
        self.lbl_file = QLabel("Keine Datei ausgewählt")
        
        self.btn_process = QPushButton("Datenerkennung starten")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.do_analysis)
        self.btn_process.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        
        self.p_bar = QProgressBar()
        self.p_bar.setVisible(False)
        self.p_bar.setStyleSheet("QProgressBar::chunk {background-color: #3498db;}")
        
        layout.addRow(self.btn_browse)
        layout.addRow(self.lbl_file)
        layout.addRow(self.btn_process)
        layout.addRow(self.p_bar)
        self.left_panel.addWidget(group)
        
    def setup_ocr_output_tabs(self):
        """Gruppe für die Ausgabe vom OCR in Rohtext und spezifische Daten"""
        tabs = QTabWidget()
        
        # Tab 1: Extrahierte Daten Tabelle
        self.data_table = QTableWidget(0, 2)
        self.data_table.setHorizontalHeaderLabels(["Parameter", "Wert"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Tab 2: Rohtext OCR
        self.raw_text_display = QTextEdit()
        self.raw_text_display.setReadOnly(True)
        
        tabs.addTab(self.data_table, "Datentabelle")
        tabs.addTab(self.raw_text_display, "Rohtext (OCR)")
        self.left_panel.addWidget(tabs)
    
    def setup_correction_input_group(self):
        """Gruppe zur Eingabe von Korrekturen für die Daten-Tabelle"""
        group = QGroupBox("2. Korrektur der Datentabelle")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            font-size: 10pt;
        }
        """)  
        layout = QGridLayout(group)
        
        # 1. Key Auswahl Dropdown Menu
        self.correct_ocr_dropdown = QComboBox()
        # Mit Keys aus Results füllen
        initial_keys = [
            '-- Noch kein OCR durchgeführt --'
        ]
        self.correct_ocr_dropdown.addItems(initial_keys)
        self.correct_ocr_dropdown.setEditable(True) # Neue Keys können manuell hinzugefügt werden
        
        self.correct_ocr_data_value = QLineEdit()
        self.correct_ocr_data_value.setPlaceholderText("z.B. 150")
        # The 0, 0 means start at Row 0, Column 0.
        layout.addWidget(QLabel("Parameter auswählen:"), 0, 0)
        layout.addWidget(self.correct_ocr_dropdown, 0, 1)
        layout.addWidget(QLabel("Wert eingeben:"), 0, 2)
        layout.addWidget(self.correct_ocr_data_value, 0, 3)
        
        # Button, um Erkannte Daten zu korrigieren
        self.btn_data_correction = QPushButton("Wert korrigieren")
        self.btn_data_correction.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        self.btn_data_correction.clicked.connect(self.update_corrected_data)
        # The 1, 4 means it takes up 1 row but spans across 4 columns
        layout.addWidget(self.btn_data_correction, 1, 0, 1, 4)
        
        self.left_panel.addWidget(group)
        
    def setup_manual_input_group(self):
        """Gruppe für die Eingabe von extra benötigten Daten (Miete, Bodenwert etc.) und Daten, die nicht erkannt wurden"""
        tabs = QTabWidget()
        
        # TAB 1
        tab1 = QWidget()
        tab1_layout = QGridLayout(tab1)
        
        # extra benötigte Daten (Mietspiegel, tatsächliche Miete, Bodenwert, Baujahr, Wohnflaeche etc.)
        info_label_tab1 = QLabel("Die folgenden Parameter sind nötig für die Berechnung. Achten Sie auf die Info-Links und Tooltips, falls etwas unklar ist.")
        tab1_layout.addWidget(info_label_tab1, 0, 0, 1, 4, alignment=Qt.AlignLeft)
        # Info-Zeile bestimmten Platz geben
        tab1_layout.setRowMinimumHeight(0, 50)
        
        # Spalte links
        self.manual_baujahr = QLineEdit()
        self.manual_baujahr.setPlaceholderText("z.B. 1975")
        
        self.manual_mietspiegel = QLineEdit()
        self.manual_mietspiegel.setPlaceholderText("z.B. 15")
        
        self.manual_miete_check = QCheckBox("Zu zahlende Miete vorhanden?")
        self.manual_tatsaechliche_miete = QLineEdit()
        self.manual_tatsaechliche_miete.setPlaceholderText("Tatsächliche Miete pro m²")
        self.manual_tatsaechliche_miete.setEnabled(self.manual_miete_check.isChecked())
        self.manual_miete_check.toggled.connect(self.manual_tatsaechliche_miete.setEnabled)
        
        self.manual_bodenrichtwert = QLineEdit()
        self.manual_bodenrichtwert.setPlaceholderText("z.B. 1200")
        
        self.manual_wohneinheiten = QLineEdit()
        self.manual_wohneinheiten.setPlaceholderText("z.B. 3")

        # Reihe 1, Spalte 0 & 1
        tab1_layout.addWidget(QLabel("Baujahr (oder Jahr Kernsanierung):"), 1, 0)
        tab1_layout.addWidget(self.manual_baujahr, 1, 1)
        # Reihe 2, Spalte 0 & 1
        mietspiegel = QLabel('<a href="https://mietspiegeltabelle.de/mietspiegel-staedte/">Mietspiegel (€/m²):</a>')
        mietspiegel.setOpenExternalLinks(True)
        mietspiegel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        mietspiegel.setToolTip("Unter diesem Link können Sie den Mietspiegel Ihres Ortes finden.")
        tab1_layout.addWidget(mietspiegel, 2, 0)
        tab1_layout.addWidget(self.manual_mietspiegel, 2, 1)
        # Reihe 3, Spalte 0 & 1
        tab1_layout.addWidget(self.manual_miete_check, 3, 0)
        tab1_layout.addWidget(self.manual_tatsaechliche_miete, 3, 1)
        # Reihe 4, Spalte 0 & 1
        bodenrichtwert = QLabel('<a href="https://www.bodenrichtwerte-boris.de/boris-d/index.html?lang=de">Bodenrichtwert (€/m²):</a>')
        bodenrichtwert.setOpenExternalLinks(True)
        bodenrichtwert.setTextInteractionFlags(Qt.TextBrowserInteraction)
        bodenrichtwert.setToolTip("Unter diesem Link können Sie den Bodenrichtwert Ihrer PLZ finden.")
        tab1_layout.addWidget(bodenrichtwert, 4, 0)
        tab1_layout.addWidget(self.manual_bodenrichtwert, 4, 1)
        # Reihe 5, Spalte 0 & 1
        tab1_layout.addWidget(QLabel("Wohneinheiten Gebäude:"), 5, 0)
        tab1_layout.addWidget(self.manual_wohneinheiten, 5, 1)

        # Spalte rechts
        self.manual_wohnflaeche = QLineEdit()
        self.manual_wohnflaeche.setPlaceholderText("z.B. 150")
        
        self.manual_teilwohnflaeche_check = QCheckBox("Teilwohnfläche betrachten")
        self.manual_eigentum_teilvermietet_check = QCheckBox("Eigentum: Teil selbst bewohnt, Teil vermietet")
        self.manual_eigentum_teilvermietet_check.setToolTip("Bei diesem Fall wird eine Kombi-Amortisation aus Nettokaltmiete und eingesparten Nebenkosten erstellt."
                                                                "\nAußerdem sind die angezeigten Miet- und Nebenkosten auf den vermieteten Teil bezogen."
                                                                "\nNebenkosten für den selbst bewohnten Teil werden im 'Amortisation Nebenkosteneinsparung' Tab angezeigt.")
        
        self.manual_teilwohnflaeche = QLineEdit()
        self.manual_teilwohnflaeche.setPlaceholderText("z.B. Fläche einer Wohneinheit")
        self.manual_teilwohnflaeche_check.toggled.connect(self.on_teilflaeche_checkbox_toggled)
        self.manual_eigentum_teilvermietet_check.toggled.connect(self.on_teilflaeche_checkbox_toggled)
        self.on_teilflaeche_checkbox_toggled()
        
        self.manual_grundstueck = QLineEdit()
        self.manual_grundstueck.setPlaceholderText("z.B. 400")
        
        self.manual_grundstuecksart = QComboBox()
        self.options_grundstuecksart = {"Ein- oder Zweifamilienhaus": 1, "Wohneigentum": 2, "Mietwohnung/-en": 3}
        self.manual_grundstuecksart.addItems(self.options_grundstuecksart.keys())
        
        self.manual_mietkappungsgrenze = QComboBox()
        self.options_mietkappungsgrenze = {"abgesenkte Kappungsgrenze": 0.15, "kein Sonderfall": 0.2} # "Gebiet mit Mietpreisbremse": 0.1 für Mietentwicklung nicht relevant nur Neuvermietung
        self.manual_mietkappungsgrenze.addItems(self.options_mietkappungsgrenze.keys())
        
        # Reihe 1, Spalte 2 & 3
        tab1_layout.addWidget(QLabel("Wohnfläche (m²):"), 1, 2)
        tab1_layout.addWidget(self.manual_wohnflaeche, 1, 3)
        # Reihe 2, Spalte 2 & 3
        tab1_layout.addWidget(self.manual_teilwohnflaeche_check, 2, 2)
        tab1_layout.addWidget(self.manual_eigentum_teilvermietet_check, 2, 3)
        # Reihe 3, Spalte 2 & 3
        tab1_layout.addWidget(QLabel("Teilwohnfläche (m²):"), 3, 2)
        tab1_layout.addWidget(self.manual_teilwohnflaeche, 3, 3)
        # Reihe 4, Spalte 2 & 3
        tab1_layout.addWidget(QLabel("Grundstücksfläche (m²):"), 4, 2)
        tab1_layout.addWidget(self.manual_grundstueck, 4, 3)
        # Reihe 5, Spalte 2 & 3
        tab1_layout.addWidget(QLabel("Grundstücksart wählen:"), 5, 2)
        tab1_layout.addWidget(self.manual_grundstuecksart, 5, 3)
        # Reihe 6, Spalte 2 & 3
        mietkappungsgrenze = QLabel('<a href="https://mieterbund.de/service/mieterschutzverordnungen/kappungsgrenze/">Mietkappungsgrenze vorhanden?</a>')
        mietkappungsgrenze.setOpenExternalLinks(True)
        mietkappungsgrenze.setTextInteractionFlags(Qt.TextBrowserInteraction)
        mietkappungsgrenze.setToolTip("Unter diesem Link können Sie überprüfen, ob Ihre Ort eine abgesenkte Kappungsgrenze hat. Diese verändert die Mietpreisentwicklung.")
        tab1_layout.addWidget(mietkappungsgrenze, 6, 2)
        tab1_layout.addWidget(self.manual_mietkappungsgrenze, 6, 3)
        
        # Zeile zwischen Eingabefeldern und Buttons leeren Platz füllen lassen
        tab1_layout.setRowStretch(tab1_layout.rowCount(), 1) # Zeile nach letzer Zeile und Verhältnis 1
        
        # TAB 2
        tab2 = QWidget()
        tab2_layout = QGridLayout(tab2)
        
        info_label_tab2 = QLabel("Hier können Sie Kennwerte zu einer Finanzierung der Sanierung angeben.\nWerden keine Kennwerte angegeben wird die Investition zu 100% eigen-finanziert berechnet.")
        tab2_layout.addWidget(info_label_tab2, 0, 0, 1, 4, alignment=Qt.AlignLeft)

        self.manual_financial_check = QCheckBox("Kennwerte für die Finanzierung hinterlegen?")
        self.manual_financial_check.setChecked(False)
        tab2_layout.addWidget(self.manual_financial_check, 1, 0, 1, 4, alignment=Qt.AlignLeft)
        self.manual_financial_check.toggled.connect(self.toggle_manual_kredit)
        
        self.manual_kreditsumme = QSpinBox()
        self.manual_kreditsumme.setRange(0, 10000000)
        self.manual_kreditsumme.setSingleStep(1000)
        self.manual_kreditsumme.setSuffix(" €")
        self.manual_kreditsumme.setValue(0)
        self.manual_kreditsumme.setEnabled(False)
        
        self.manual_kredit_zinssatz = QDoubleSpinBox()
        self.manual_kredit_zinssatz.setRange(0.0, 100.0)
        self.manual_kredit_zinssatz.setSuffix(" % pro Jahr")
        self.manual_kredit_zinssatz.setSingleStep(0.5)
        self.manual_kredit_zinssatz.setValue(0)
        self.manual_kredit_zinssatz.setEnabled(False)
        
        self.manual_kredit_laufzeit = QSpinBox()
        self.manual_kredit_laufzeit.setRange(12, 360)
        self.manual_kredit_laufzeit.setSuffix(" Monate")
        self.manual_kredit_laufzeit.setSingleStep(12)
        self.manual_kredit_laufzeit.setValue(12)
        self.manual_kredit_laufzeit.setEnabled(False)
        
        # self.manual_kredit_blabla = QDoubleSpinBox()
        # self.manual_kredit_blabla.setRange(0.0, 100.0)
        # self.manual_kredit_blabla.setSuffix(" % pro Jahr")
        # self.manual_kredit_blabla.setSingleStep(0.5)
        # self.manual_kredit_blabla.setValue(self.BESTANDSMIETEN_ENTWICKLUNG * 100)
        # self.manual_kredit_blabla.setEnabled(False)
        
        tab2_layout.addWidget(QLabel("Kreditsumme:"), 2, 0)
        tab2_layout.addWidget(self.manual_kreditsumme, 2, 1)
        tab2_layout.addWidget(QLabel("Effektiver Jahreszins:"), 3, 0)
        tab2_layout.addWidget(self.manual_kredit_zinssatz, 3, 1)
        
        tab2_layout.addWidget(QLabel("Laufzeit:"), 2, 2)
        tab2_layout.addWidget(self.manual_kredit_laufzeit, 2, 3)
        # tab2_layout.addWidget(QLabel("blablabla:"), 3, 2)
        # tab2_layout.addWidget(self.manual_kredit_blabla, 3, 3)
        
        # Info-Zeile und Checkbox mehr Platz geben
        tab2_layout.setRowMinimumHeight(0, 50)
        tab2_layout.setRowMinimumHeight(1, 30)
        # Letzte Zeile leeren Platz füllen lassen
        tab2_layout.setRowStretch(tab2_layout.rowCount(), 1)
        
        # TAB 3
        tab3 = QWidget()
        tab3_layout = QGridLayout(tab3)
        info_label_tab3 = QLabel("Hier können Sie die Preisentwicklungsfaktoren und den Betrachtungszeitraum individuell für Ihren Fall anpassen.\nDie hinterlegten Parameterwerte sind in Grau in den Eingabefelder zu sehen.")
        tab3_layout.addWidget(info_label_tab3, 0, 0, 1, 4, alignment=Qt.AlignLeft)

        self.manual_factors_check = QCheckBox("Faktoren individuell anpassen?")
        self.manual_factors_check.setChecked(False)
        tab3_layout.addWidget(self.manual_factors_check, 1, 0, 1, 4, alignment=Qt.AlignLeft)
        self.manual_factors_check.toggled.connect(self.toggle_manual_factors)
        
        self.manual_inflation = QDoubleSpinBox()
        self.manual_inflation.setRange(0.0, 100.0)
        self.manual_inflation.setSuffix(" % pro Jahr")
        self.manual_inflation.setSingleStep(0.5)
        self.manual_inflation.setValue(self.INFLATION * 100)
        self.manual_inflation.setEnabled(False)
        
        self.manual_energiepreisentwicklung = QDoubleSpinBox()
        self.manual_energiepreisentwicklung.setRange(0.0, 100.0)
        self.manual_energiepreisentwicklung.setSuffix(" % pro Jahr")
        self.manual_energiepreisentwicklung.setSingleStep(0.5)
        self.manual_energiepreisentwicklung.setValue(self.ENERGIEPREIS_ENTWICKLUNG * 100)
        self.manual_energiepreisentwicklung.setEnabled(False)
        
        self.manual_mietpreisentwicklung = QDoubleSpinBox()
        self.manual_mietpreisentwicklung.setRange(0.0, 100.0)
        self.manual_mietpreisentwicklung.setSuffix(" % pro Jahr")
        self.manual_mietpreisentwicklung.setSingleStep(0.5)
        self.manual_mietpreisentwicklung.setValue(self.BESTANDSMIETEN_ENTWICKLUNG * 100)
        self.manual_mietpreisentwicklung.setEnabled(False)
        
        self.manual_betrachtungszeitraum = QSpinBox()
        self.manual_betrachtungszeitraum.setRange(1, 100)
        self.manual_betrachtungszeitraum.setSuffix(" Jahre")
        self.manual_betrachtungszeitraum.setValue(self.BETRACHTUNGSZEITRAUM)
        self.manual_betrachtungszeitraum.setEnabled(False)
        
        tab3_layout.addWidget(QLabel("Inflation pro Jahr:"), 2, 0)
        tab3_layout.addWidget(self.manual_inflation, 2, 1)
        tab3_layout.addWidget(QLabel("Energiepreisentwicklung:"), 3, 0)
        tab3_layout.addWidget(self.manual_energiepreisentwicklung, 3, 1)
        
        tab3_layout.addWidget(QLabel("Preisentwicklung Mieten:"), 2, 2)
        tab3_layout.addWidget(self.manual_mietpreisentwicklung, 2, 3)
        tab3_layout.addWidget(QLabel("Betrachtungszeitraum Diagramme:"), 3, 2)
        tab3_layout.addWidget(self.manual_betrachtungszeitraum, 3, 3)
        
        # Info-Zeile und Checkbox mehr Platz geben
        tab3_layout.setRowMinimumHeight(0, 50)
        tab3_layout.setRowMinimumHeight(1, 30)
        # Letzte Zeile leeren Platz füllen lassen
        tab3_layout.setRowStretch(tab2_layout.rowCount(), 1)
        
        # Tabs zu Widget und Panel hinzufügen 
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        tabs.tabBar().setFont(font)
        tabs.addTab(tab1, "3. Gebäudedaten")
        tabs.addTab(tab2, "4. Finanzierung")
        tabs.addTab(tab3, "5. Anpassung Zeitraum und Preisentwicklung")
        self.left_panel.addWidget(tabs)
        
    def setup_programm_control_buttons_group(self):
        """Gruppe für die zwei Buttons: Werte in Datentabelle übernehmen, Berechnung durchführen"""
        group = QWidget()
        layout = QGridLayout(group)
        
        # Button, um benötigte Dateneingabe für Berechnung hinzuzufügen und Berechnung durchzuführen
        self.btn_apply_extra_data = QPushButton("Werte übernehmen und Berechnung durchführen")
        self.btn_apply_extra_data.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply_extra_data.clicked.connect(self.update_additional_data)
        self.btn_apply_extra_data.clicked.connect(self.update_calculation_results)
        layout.addWidget(self.btn_apply_extra_data, 7, 0, 1, 4)
        
        # Button, um Berechnung durchzuführen
        # self.btn_apply_extra_data = QPushButton("2. Berechnung durchführen")
        # self.btn_apply_extra_data.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        # self.btn_apply_extra_data.clicked.connect(self.update_calculation_results)
        # layout.addWidget(self.btn_apply_extra_data, 7, 2, 1, 2)
        
        self.left_panel.addWidget(group)

    def setup_calculation_results_group(self):
        """Gruppe zum Ausgeben der Rechenergebnisse für Immobilienwert, Kaltmiete und Nebenkosten in saniert und unsaniert"""
        group = QGroupBox("Kennwerte")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            font-size: 10pt;
        }
        """) 
        layout = QGridLayout(group)
        
        self.calc_property_value_old = QLabel("0,00 €")
        self.calc_property_value_old.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.calc_property_value_renovated = QLabel("0,00 €")
        self.calc_property_value_renovated.setStyleSheet("font-weight: bold; color: #3498db;")
        self.calc_rent_old = QLabel("0,00 €")
        self.calc_rent_old.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.calc_rent_renovated = QLabel("0,00 €")
        self.calc_rent_renovated.setStyleSheet("font-weight: bold; color: #3498db;")
        self.calc_additional_costs_old = QLabel("0,00 €")
        self.calc_additional_costs_old.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.calc_additional_costs_renovated = QLabel("0,00 €")
        self.calc_additional_costs_renovated.setStyleSheet("font-weight: bold; color: #3498db;")
        self.sanierungskosten_beg = QLabel("0,00 €")
        self.sanierungskosten_beg.setStyleSheet("font-weight: bold;")
        self.foerdersumme_beg = QLabel("0,00 €")
        self.foerdersumme_beg.setStyleSheet("font-weight: bold;")
        self.investment_sum_beg = QLabel("0,00 €")
        self.investment_sum_beg.setStyleSheet("font-weight: bold;")
        self.sanierungskosten_geg = QLabel("0,00 €")
        # self.sanierungskosten_geg.setStyleSheet("font-weight: bold;")
        self.foerdersumme_geg = QLabel("0,00 €")
        # self.foerdersumme_geg.setStyleSheet("font-weight: bold;")
        self.investment_sum_geg = QLabel("0,00 €")
        # self.investment_sum_geg.setStyleSheet("font-weight: bold;")
        info_feld = QLabel("Folgende Diagramme beziehen sich nur auf BEG-Vorschlag, da für GEG-Vorschlag keine Energiekosten-Einsparung vorhanden ist.")
        info_feld.setAlignment(Qt.AlignLeft)
        info_feld.setStyleSheet("color: grey; font-size: 8pt; padding: 1px;")
        self.miteigentumsanteil_investition = QLabel("")
        self.miteigentumsanteil_investition.setAlignment(Qt.AlignLeft)
        self.miteigentumsanteil_investition.hide()
        self.label_nebenkosten_eigentuemer = QLabel("")
        self.label_nebenkosten_eigentuemer.setAlignment(Qt.AlignLeft)
        self.label_nebenkosten_eigentuemer.hide()
        
        # Layout
        layout.addWidget(QLabel("Immobilienwert unsaniert:"), 0, 0)
        layout.addWidget(self.calc_property_value_old, 0, 1)
        layout.addWidget(QLabel("Immobilienwert saniert:"), 1, 0)
        layout.addWidget(self.calc_property_value_renovated, 1, 1)
        layout.addWidget(QLabel("Bruttokaltmiete unsaniert:"), 0, 2)
        layout.addWidget(self.calc_rent_old, 0, 3)
        layout.addWidget(QLabel("Bruttokaltmiete saniert:"), 1, 2)
        layout.addWidget(self.calc_rent_renovated, 1, 3)
        layout.addWidget(QLabel("Nebenkosten unsaniert:"), 0, 4)
        layout.addWidget(self.calc_additional_costs_old, 0, 5)
        layout.addWidget(QLabel("Nebenkosten saniert:"), 1, 4)
        layout.addWidget(self.calc_additional_costs_renovated, 1, 5)
        layout.addWidget(QLabel("Sanierungskosten BEG:"), 2, 0)
        layout.addWidget(self.sanierungskosten_beg, 2, 1)
        layout.addWidget(QLabel("Fördersumme BEG:"), 2, 2)
        layout.addWidget(self.foerdersumme_beg, 2, 3)
        layout.addWidget(QLabel("Investitionssumme BEG:"), 2, 4)
        layout.addWidget(self.investment_sum_beg, 2, 5)
        layout.addWidget(QLabel("Sanierungskosten GEG:"), 3, 0)
        layout.addWidget(self.sanierungskosten_geg, 3, 1)
        layout.addWidget(QLabel("Fördersumme GEG:"), 3, 2)
        layout.addWidget(self.foerdersumme_geg, 3, 3)
        layout.addWidget(QLabel("Investitionssumme GEG:"), 3, 4)
        layout.addWidget(self.investment_sum_geg, 3, 5)
        layout.addWidget(info_feld, 4, 0, 1, 6)
        layout.addWidget(self.label_nebenkosten_eigentuemer, 5, 0, 1, 6)
        layout.addWidget(self.miteigentumsanteil_investition, 6, 0, 1, 6)
        
        self.right_panel.addWidget(group)

    def setup_results_chart_tabs(self):
        """Tabs für Diagramme zu Darstellung der Kosten-/Einnahmeentwicklung über Zeit"""
        self.chart_tabs = QTabWidget()
        
        # Tab 1: Mieteinnahmen/Kaltmiete Entwicklung Vermieter - Balkendiagramm
        self.chart_view_landlord = QChartView()
        self.chart_view_landlord.setRenderHint(QPainter.Antialiasing)
        
        # Tab 2: Mietausgaben/Warmmiete Entwicklung Mieter - Balkendiagramm
        self.chart_view_renter = QChartView()
        self.chart_view_renter.setRenderHint(QPainter.Antialiasing)
        
        # Tab 3: Amortisation der Investition über Nettokaltmieten - Balkendiagramm
        self.chart_view_investment_rent = QChartView()
        self.chart_view_investment_rent.setRenderHint(QPainter.Antialiasing)
        
        # Tab 4: Amortisation der Investition über Nebenkosteneinsparung - Balkendiagramm
        self.chart_view_investment_energycost = QChartView()
        self.chart_view_investment_energycost.setRenderHint(QPainter.Antialiasing)
        
        # Bedingter Tab 5: Kombi-Amortisation bei Teileigennutzung Eigentümer - Kombi aus Nettokaltmieten und Nebenkosten Eigentümer
        self.chart_view_combi_energycost_rent = QChartView()
        self.chart_view_combi_energycost_rent.setRenderHint(QPainter.Antialiasing)
        
        # Bedingter Tab 6: Ergebnisse der Kreditrechnung für ein Annuitätendarlehen
        self.tab6_kreditrechnung = QWidget()
        self.tab6_layout = QGridLayout(self.tab6_kreditrechnung)
        self.widget_fremdkapital_quote = QLabel("")
        self.widget_fremdkapital_quote.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.widget_eigenkapital_quote = QLabel("")
        self.widget_eigenkapital_quote.setStyleSheet("font-weight: bold; color: #3498db;")
        self.widget_annuitaet = QLabel("")
        self.widget_annuitaet.setStyleSheet("font-weight: bold;")
        self.widget_zinsaufwand = QLabel("")
        self.widget_zinsaufwand.setStyleSheet("font-weight: bold;")
        self.widget_gesamtaufwand = QLabel("")
        self.widget_gesamtaufwand.setStyleSheet("font-weight: bold;")
        self.tab6_layout.addWidget(QLabel("Fremdkapitalquote:"), 0, 0)
        self.tab6_layout.addWidget(self.widget_fremdkapital_quote, 0, 1)
        self.tab6_layout.addWidget(QLabel("Eigenkapitalquote:"), 1, 0)
        self.tab6_layout.addWidget(self.widget_eigenkapital_quote, 1, 1)
        self.tab6_layout.addWidget(QLabel("Annuität:"), 0, 2)
        self.tab6_layout.addWidget(self.widget_annuitaet, 0, 3)
        self.tab6_layout.addWidget(QLabel("Zinsaufwand:"), 0, 4)
        self.tab6_layout.addWidget(self.widget_zinsaufwand, 0, 5)
        self.tab6_layout.addWidget(QLabel("Gesamtaufwand Kredit:"), 1, 4)
        self.tab6_layout.addWidget(self.widget_gesamtaufwand, 1, 5)
        self.tab6_layout.setRowStretch(self.tab6_layout.rowCount(), 1)

        # Tabs hinzufügen
        font = QFont()
        font.setBold(True)
        font.setPointSize(8)
        self.chart_tabs.tabBar().setFont(font)
        self.chart_tabs.addTab(self.chart_view_landlord, "Kaltmiet-Entwicklung")
        self.chart_tabs.addTab(self.chart_view_renter, "Warmmiet-Entwicklung")
        self.chart_tabs.addTab(self.chart_view_investment_rent, "Amortisation Nettokaltmieten")
        self.chart_tabs.addTab(self.chart_view_investment_energycost, "Amortisation Nebenkosteneinsparung")
        
        self.right_panel.addWidget(self.chart_tabs)
        
    def setup_end_group(self):
        """Endgruppe (unten rechts) für Reset-Button und pdf-Ausgabe der Ergebnisse"""
        group = QGroupBox()
        layout = QGridLayout(group)
        
        self.btn_reset_programm = QPushButton("Programm zurücksetzen")
        self.btn_reset_programm.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        self.btn_reset_programm.clicked.connect(self.reset_programm)
        layout.addWidget(self.btn_reset_programm, 1, 0, 1, 2)
        
        self.btn_print_results = QPushButton("Als Pdf-Datei exportieren")
        self.btn_print_results.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px;")
        self.btn_print_results.clicked.connect(self.pdf_export)
        layout.addWidget(self.btn_print_results, 1, 3, 1, 2)
        
        self.right_panel.addWidget(group)
        


    # Aktionen, Events
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "PDF öffnen", "", "PDF Files (*.pdf)")
        if file_path:
            self.lbl_file.setText(os.path.basename(file_path))
            self.selected_file = file_path
            self.btn_process.setEnabled(True)

    def do_analysis(self):
        self.p_bar.setVisible(True)
        self.p_bar.setRange(0, 0) # Pulsing animation
        self.ocr_worker = OCRWorker(self.selected_file)
        self.ocr_worker.finished.connect(self.handle_ocr_results)
        self.ocr_worker.start()

    def handle_ocr_results(self, results):
        self.p_bar.setVisible(False)
        # 1. Update Rohtext (OCR)
        self.raw_text_display.setText(results["rohtext"])
        # 2. Update Master-Daten-Halter
        self.input_data_dict = results["daten_int"] # "daten_int" geht, wenn int Datentyp in str in refresh_tabe_ui() umgewandelt wird
        # 3. Füge Drop-Down Menüoptionen hinzu, als Keys aus data_dict
        self.correct_ocr_dropdown.clear()
        self.correct_ocr_dropdown.addItems(list(self.input_data_dict.keys()))
        # 4. Zeige Daten in Erkannte Daten Tabelle
        self.refresh_table_ui()
        
    def refresh_table_ui(self):
        self.data_table.setRowCount(len(self.input_data_dict))
        for i, (k, v) in enumerate(self.input_data_dict.items()):
            self.data_table.setItem(i, 0, QTableWidgetItem(k))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(v))) # in den Klammern kann ein Datenformat festgelegt werden, nach welchem gesucht und angepasst wird: f"{v} kW"
        
    def update_corrected_data(self):
        """Update Master-Daten-Halter basierend auf Dropdown Auswahl und Eingabe"""
        key = self.correct_ocr_dropdown.currentText().strip()
        raw_val = self.correct_ocr_data_value.text().strip()
    
        if not key or not raw_val:
            print("Fehler: Parameter oder Wert fehlt.")
            return
    
        # Datentypumwandlung Logik
        clean_val = raw_val.replace(',', '.')
        
        try:
            # Als nummer speichern
            if "." in clean_val:
                processed_val = float(clean_val)
            else:
                processed_val = int(clean_val)
        except ValueError:
            # Falls keine nummer -> str
            processed_val = raw_val
    
        # Dict updaten
        self.input_data_dict[key] = processed_val
        
        # Feedback erfolgreich
        print(f"Update erfolgreich: {key} -> {processed_val}")
        self.correct_ocr_data_value.clear() # Nach Update Feld leeren
        self.refresh_table_ui()
        
    def update_additional_data(self):
        """Logik, um manuelle Eingaben dem Master-Daten-Halter hinzuzufügen und in Erkannte Daten tabelle anzuzeigen"""
        # 1. Manuell eingegebene Daten aus den Feldern in mapping
        manual_inputs_mapping = {
            "Baujahr": self.manual_baujahr,
            "Mietspiegel": self.manual_mietspiegel,
            "Miete": self.manual_tatsaechliche_miete,
            "Bodenrichtwert": self.manual_bodenrichtwert,
            "Wohnflaeche": self.manual_wohnflaeche,
            "Teilwohnflaeche": self.manual_teilwohnflaeche,
            "Grundstuecksflaeche": self.manual_grundstueck,
            "Wohnungsanzahl": self.manual_wohneinheiten,
            }
        
        # Prüfen ob Checkbox gesetzt wurde
        miete_is_active = self.manual_miete_check.isChecked()
        if self.manual_teilwohnflaeche_check.isChecked() or self.manual_eigentum_teilvermietet_check.isChecked():
            teilwohnflaeche_is_active = True
        else: 
            teilwohnflaeche_is_active = False
        is_active_dict = {"Miete": miete_is_active, "Teilwohnflaeche": teilwohnflaeche_is_active}
        
        # 2. Durch das mapping iterieren
        for key, widget in manual_inputs_mapping.items():
            
            # Abhängig von Checkbox und Eintrag Key aus input_data_dict entfernen
            if key in is_active_dict and is_active_dict[key] is False:
                self.input_data_dict.pop(key, None)
                # continue damit die Keys im restlichen Code übersprungen werden
                continue
            
            user_text = widget.text().strip()
        
            # Nur durchführen wenn etwas eingegeben wurde
            if user_text:
                # Saubere numerische Ziffern "1000,50" -> "1000.50" und "1000.50" unverändert
                clean_val = user_text.replace(',', '.')
                
                try:
                    # Als nummer speichern
                    if "." in clean_val:
                        self.input_data_dict[key] = float(clean_val)
                    else:
                        self.input_data_dict[key] = int(clean_val)
                except ValueError:
                    # Falls keine nummer -> str
                    self.input_data_dict[key] = user_text
        
        # 3. Dropdown Menü mit Integer Dict-Einträgen
        option_text = self.manual_grundstuecksart.currentText()
        option_int = self.options_grundstuecksart[option_text]
        self.input_data_dict["Grundstuecksart"] = option_int
        option_text = self.manual_mietkappungsgrenze.currentText()
        option_int = self.options_mietkappungsgrenze[option_text]
        self.input_data_dict["Kappungsgrenze"] = option_int

        # 4. UI updaten
        print(f"Aktualisierte Daten: {self.input_data_dict}\n")
        self.refresh_table_ui()
        
    def on_teilflaeche_checkbox_toggled(self):
        # Bestimmung welche Checkbox die Funktion auslöst
        sender = self.sender()
        
        # Entweder-Oder der Checkboxen
        if sender == self.manual_teilwohnflaeche_check and self.manual_teilwohnflaeche_check.isChecked():
            self.manual_eigentum_teilvermietet_check.setChecked(False)
            
        elif sender == self.manual_eigentum_teilvermietet_check and self.manual_eigentum_teilvermietet_check.isChecked():
            self.manual_teilwohnflaeche_check.setChecked(False)
    
        # Lineedit bei einer Checkbox zulassen
        any_checked = self.manual_teilwohnflaeche_check.isChecked() or self.manual_eigentum_teilvermietet_check.isChecked()
        self.manual_teilwohnflaeche.setEnabled(any_checked)
        
    def toggle_manual_kredit(self, checked):
        # SpinBoxes aktivieren wenn Haken gesetzt
        self.manual_kreditsumme.setEnabled(checked)
        self.manual_kredit_zinssatz.setEnabled(checked)
        self.manual_kredit_laufzeit.setEnabled(checked)
        # self.manual_kredit_blabla.setEnabled(checked)
        # Wenn Haken nicht gesetzt oder entfernt wird -> Werte auf Standard zurücksetzen
        if not checked:
            self.manual_kreditsumme.setValue(0)
            self.manual_kredit_zinssatz.setValue(0)
            self.manual_kredit_laufzeit.setValue(0)
            # self.manual_kredit_blabla.setValue(blabla)
            
    def return_manual_kredit(self):
        kreditsumme = self.manual_kreditsumme.value()
        jahreszins = self.manual_kredit_zinssatz.value() / 100.0
        laufzeit = self.manual_kredit_laufzeit.value()
        
        return kreditsumme, jahreszins, laufzeit
    
    def toggle_manual_factors(self, checked):
        # SpinBoxes aktivieren wenn Haken gesetzt
        self.manual_inflation.setEnabled(checked)
        self.manual_energiepreisentwicklung.setEnabled(checked)
        self.manual_mietpreisentwicklung.setEnabled(checked)
        self.manual_betrachtungszeitraum.setEnabled(checked)
        # Wenn Haken nicht gesetzt oder entfernt wird -> Werte auf Standard zurücksetzen
        if not checked:
            self.manual_inflation.setValue(self.INFLATION * 100)
            self.manual_energiepreisentwicklung.setValue(self.ENERGIEPREIS_ENTWICKLUNG * 100)
            self.manual_mietpreisentwicklung.setValue(self.BESTANDSMIETEN_ENTWICKLUNG * 100)
            self.manual_betrachtungszeitraum.setValue(self.BETRACHTUNGSZEITRAUM)
            
    def return_manual_factors(self):
        # Da die Spinboxes immer zurückgesetzt werden wenn der Haken nicht gesetzt ist, wird immer der korrekte Wert ausgegeben
        # Daher reicht es den Wert des Feldes abzufragen, ohne die Klassenvariablen abfragen zu müssen
        inflation = self.manual_inflation.value() / 100.0
        energiepreisentwicklung = self.manual_energiepreisentwicklung.value() / 100.0
        mietpreisentwicklung = self.manual_mietpreisentwicklung.value() / 100.0
        betrachtungszeitraum = self.manual_betrachtungszeitraum.value()
        
        return inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum

    def update_calculation_results(self):
        """Funktion für den 'Berechnung starten' Knopf"""
        data = self.input_data_dict
        gebaeude = data_calculations.Gebaeude(data["Baujahr"])
        
        # Vorrechnungen
        umlegbare_sanierungskosten = gebaeude.umlageberechtigte_sanierungskosten(daten=data, sanierungskosten=data["Sanierungskosten BEG"])
        
        # Gesamtfläche wird berechnet (im Fall einer Teilwohnfäche/Miteigentumsanteil wird unten angepasst)
        if "Miete" in data and self.manual_miete_check.isChecked() is True:
            miete_pro_qm_saniert = gebaeude.mietanpassung_saniert(wohnflaeche_mieter=data["Wohnflaeche"], miete_pro_qm=data["Miete"], sanierungskosten=umlegbare_sanierungskosten)
            
            
            # ... und Gesamtfläche berechnet werden soll
            # 1. Immobilien Ertragswert            
            ertragswert_unsaniert = gebaeude.immobilienwert_ertragswert(bodenrichtwert=data["Bodenrichtwert"], grundstuecksflaeche=data["Grundstuecksflaeche"], 
                                                                        wohnflaeche=data["Wohnflaeche"], miete_qm=data["Miete"], 
                                                                        grundstuecksart=data["Grundstuecksart"], anzahl_wohnungen=data["Wohnungsanzahl"], 
                                                                        maengel=0, saniert=False)
            ertragswert_saniert = gebaeude.immobilienwert_ertragswert(bodenrichtwert=data["Bodenrichtwert"], grundstuecksflaeche=data["Grundstuecksflaeche"], 
                                                                      wohnflaeche=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert, 
                                                                      grundstuecksart=data["Grundstuecksart"], anzahl_wohnungen=data["Wohnungsanzahl"], 
                                                                      maengel=0, saniert=True, sanierungsbestandteile_data=data["Sanierungsmassnahmen"])
            # 2. Bruttokaltmiete
            bruttokaltmiete_unsaniert = gebaeude.bruttokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=data["Miete"])
            bruttokaltmiete_saniert = gebaeude.bruttokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert)
            # 3. umlagefähige Betriebskosten
            betriebskosten = gebaeude.betriebskosten_jahr(data["Wohnflaeche"])
            # 4. Nettokaltmiete
            nettokaltmiete_unsaniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=data["Miete"]) * 12
            nettokaltmiete_saniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert) * 12
            nettokaltmiete_mietspiegel = gebaeude.nettokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=data["Mietspiegel"]) * 12     
            # 5. Nebenkosten
            nebenkosten_unsaniert = gebaeude.nebenkosten(data["Energiekosten unsaniert"])
            nebenkosten_saniert = gebaeude.nebenkosten(data["Energiekosten saniert"])
                
        # Berechnung wenn nur Mietspiegel und nicht tatsächlich gezahlte Miete vorhanden
        else:
            miete_pro_qm_saniert = gebaeude.mietanpassung_saniert(wohnflaeche_mieter=data["Wohnflaeche"], miete_pro_qm=data["Mietspiegel"], sanierungskosten=umlegbare_sanierungskosten)
        
            # Gesamtfläche wird berechnet (im Fall einer Teilwohnfäche/Miteigentumsanteil wird unten angepasst)
            # 1. Immobilien Ertragswert
            ertragswert_unsaniert = gebaeude.immobilienwert_ertragswert(bodenrichtwert=data["Bodenrichtwert"], grundstuecksflaeche=data["Grundstuecksflaeche"], 
                                                                        wohnflaeche=data["Wohnflaeche"], miete_qm=data["Mietspiegel"], 
                                                                        grundstuecksart=data["Grundstuecksart"], anzahl_wohnungen=data["Wohnungsanzahl"], 
                                                                        maengel=0, saniert=False)
            ertragswert_saniert = gebaeude.immobilienwert_ertragswert(bodenrichtwert=data["Bodenrichtwert"], grundstuecksflaeche=data["Grundstuecksflaeche"], 
                                                                      wohnflaeche=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert, 
                                                                      grundstuecksart=data["Grundstuecksart"], anzahl_wohnungen=data["Wohnungsanzahl"], 
                                                                      maengel=0, saniert=True, sanierungsbestandteile_data=data["Sanierungsmassnahmen"])
            # 2. Bruttokaltmiete
            bruttokaltmiete_unsaniert = gebaeude.bruttokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=data["Mietspiegel"])
            bruttokaltmiete_saniert = gebaeude.bruttokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert)
            # 3. umlagefähige Betriebskosten
            betriebskosten = gebaeude.betriebskosten_jahr(data["Wohnflaeche"])
            # 4. Nettokaltmiete
            nettokaltmiete_unsaniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=data["Mietspiegel"]) * 12
            nettokaltmiete_saniert = gebaeude.nettokaltmiete(wohnflaeche_mieter=data["Wohnflaeche"], miete_qm=miete_pro_qm_saniert) * 12
            # 5. Nebenkosten
            nebenkosten_unsaniert = gebaeude.nebenkosten(data["Energiekosten unsaniert"])
            nebenkosten_saniert = gebaeude.nebenkosten(data["Energiekosten saniert"])
        
        # Anpassung für Teilwohnfläche mittels Miteigentumanteil im Fall einer Eigentümergesellschaft (im Fall eines Mieter kann analog angewendet werden)
        if "Teilwohnflaeche" in data and self.manual_teilwohnflaeche_check.isChecked() is True:
            # Miteigentumsanteil regelt die Aufteilung der Werte und Kosten (über Wohnfläche wird dadurch ebenfalls der Anteil am Grundstück bestimmt)
            miteigentumsanteil = data["Teilwohnflaeche"] / data["Wohnflaeche"]
            # 1. Immobilien Ertragswert            
            ertragswert_unsaniert = miteigentumsanteil * ertragswert_unsaniert
            ertragswert_saniert = miteigentumsanteil * ertragswert_saniert
            # 2. Bruttokaltmiete
            bruttokaltmiete_unsaniert = miteigentumsanteil * bruttokaltmiete_unsaniert
            bruttokaltmiete_saniert = miteigentumsanteil * bruttokaltmiete_saniert
            # 3. umlagefähige Betriebskosten
            betriebskosten = miteigentumsanteil * betriebskosten
            # 4. Nettokaltmiete
            nettokaltmiete_unsaniert = miteigentumsanteil * nettokaltmiete_unsaniert
            nettokaltmiete_saniert = miteigentumsanteil * nettokaltmiete_saniert
            try:
                nettokaltmiete_mietspiegel = miteigentumsanteil * nettokaltmiete_mietspiegel
            except NameError:
                pass
            # 5. Nebenkosten
            nebenkosten_unsaniert = miteigentumsanteil * nebenkosten_unsaniert
            nebenkosten_saniert = miteigentumsanteil * nebenkosten_saniert
            
        # Anpassung für Eigentümer-genutzte Wohnfläche vorhanden und die Restfläche wird vermietet
        elif "Teilwohnflaeche" in data and self.manual_eigentum_teilvermietet_check.isChecked() is True:
            # Mietflächenanteil dazu, um entsprechende Mietwerte anzupassen
            miteigentumsanteil = data["Teilwohnflaeche"] / data["Wohnflaeche"]
            mietflaechenanteil = 1 - miteigentumsanteil
            # 1. Immobilien Ertragswert            
            # bleibt unverändert, da hier der Fall, dass Eigentümer gesamtes Haus besitzt
            # 2. Bruttokaltmiete
            bruttokaltmiete_unsaniert = mietflaechenanteil * bruttokaltmiete_unsaniert
            bruttokaltmiete_saniert = mietflaechenanteil * bruttokaltmiete_saniert
            # 3. umlagefähige Betriebskosten
            betriebskosten = mietflaechenanteil * betriebskosten
            # 4. Nettokaltmiete
            nettokaltmiete_unsaniert = mietflaechenanteil * nettokaltmiete_unsaniert
            nettokaltmiete_saniert = mietflaechenanteil * nettokaltmiete_saniert
            try:
                nettokaltmiete_mietspiegel = mietflaechenanteil * nettokaltmiete_mietspiegel
            except NameError:
                pass
            # 5. Nebenkosten
            nebenkosten_unsaniert = mietflaechenanteil * nebenkosten_unsaniert
            nebenkosten_saniert = mietflaechenanteil * nebenkosten_saniert
            
        else:
            pass
        
        # 6. Warmiete
        warmmiete_unsaniert = bruttokaltmiete_unsaniert + nebenkosten_unsaniert
        warmmiete_saniert = bruttokaltmiete_saniert + nebenkosten_saniert
        
        # 7. Gesamtförderung
        gesamtfoerderung_beg = gebaeude.foederung_beg(daten=data)
        gesamtfoerderung_geg = gebaeude.foederung_geg(daten=data)
        
        # 8. Investitionssumme
        investition_beg = data["Sanierungskosten BEG"] - gesamtfoerderung_beg
        investition_geg = data["Sanierungskosten GEG"] - gesamtfoerderung_geg
        
        # 9. Kreditrechnung - Annuitätendarlehen
        if self.manual_financial_check.isChecked() is True:
            kreditsumme, jahreszins, laufzeit = self.return_manual_kredit()
            fremdkapital_quote, eigenkapital_quote, annuitaet, zinsaufwand_kredit, gesamtaufwand_kredit = gebaeude.kreditrechnung(daten=data, sanierungskosten=data["Sanierungskosten BEG"],
                                                                                                                    kreditsumme=kreditsumme, jahreszins=jahreszins, laufzeit=laufzeit)
        
        # UI Update
        self.calc_property_value_old.setText(self.zahlen_deutsch(f"{ertragswert_unsaniert:,.2f} €"))
        self.calc_property_value_renovated.setText(self.zahlen_deutsch(f"{ertragswert_saniert:,.2f} €"))
        self.calc_rent_old.setText(self.zahlen_deutsch(f"{bruttokaltmiete_unsaniert:,.2f} €/Monat"))
        self.calc_rent_renovated.setText(self.zahlen_deutsch(f"{bruttokaltmiete_saniert:,.2f} €/Monat"))
        self.calc_additional_costs_old.setText(self.zahlen_deutsch(f"{nebenkosten_unsaniert:,.2f} €/Monat"))
        self.calc_additional_costs_renovated.setText(self.zahlen_deutsch(f"{nebenkosten_saniert:,.2f} €/Monat"))
        self.sanierungskosten_beg.setText(self.zahlen_deutsch(f"{data['Sanierungskosten BEG']:,.2f} €"))
        self.foerdersumme_beg.setText(self.zahlen_deutsch(f"{gesamtfoerderung_beg:,.2f} €"))
        self.investment_sum_beg.setText(self.zahlen_deutsch(f"{investition_beg:,.2f} €"))
        self.sanierungskosten_geg.setText(self.zahlen_deutsch(f"{data['Sanierungskosten GEG']:,.2f} €"))
        self.foerdersumme_geg.setText(self.zahlen_deutsch(f"{gesamtfoerderung_geg:,.2f} €"))
        self.investment_sum_geg.setText(self.zahlen_deutsch(f"{investition_geg:,.2f} €"))
        
        if "Teilwohnflaeche" in data and self.manual_teilwohnflaeche_check.isChecked() is True:
            teil_investition = round(miteigentumsanteil * investition_beg, 2)
            text = self.zahlen_deutsch(f"Miteigentumsanteil an der Investition: <b>{teil_investition:,.2f} €</b>")
            self.miteigentumsanteil_investition.setText(text)
            self.miteigentumsanteil_investition.setVisible(True)
            self.result_data_dict.update({"teilinvestition": teil_investition})
        else:
            self.miteigentumsanteil_investition.setVisible(False)
        
        self.result_data_dict.update({"ertragswert_unsaniert": ertragswert_unsaniert, "ertragswert_saniert": ertragswert_saniert, 
                                      "bruttokaltmiete_unsaniert": bruttokaltmiete_unsaniert, "bruttokaltmiete_saniert": bruttokaltmiete_saniert, 
                                      "nettokaltmiete_unsaniert": nettokaltmiete_unsaniert, "nettokaltmiete_saniert": nettokaltmiete_saniert, 
                                      "nebenkosten_unsaniert": nebenkosten_unsaniert, "nebenkosten_saniert": nebenkosten_saniert,
                                      "warmmiete_unsaniert": warmmiete_unsaniert, "warmmiete_saniert": warmmiete_saniert,
                                      "gesamtfoerderung_beg": gesamtfoerderung_beg, "investition_beg": investition_beg,
                                      "gesamtfoerderung_geg": gesamtfoerderung_geg, "investition_geg": investition_geg,
                                      "miete_pro_qm_saniert": miete_pro_qm_saniert, "betriebskosten": betriebskosten})
        
        if "Miete" in data and self.manual_miete_check.isChecked() is True:
            self.result_data_dict.update({"nettokaltmiete_mietspiegel": nettokaltmiete_mietspiegel})
            
        if self.manual_financial_check.isChecked() is True:
            self.result_data_dict.update({"fremdkapital_quote": fremdkapital_quote, "eigenkapital_quote": eigenkapital_quote,
                                          "annuitaet": annuitaet, "zinsaufwand_kredit": zinsaufwand_kredit, 
                                          "gesamtaufwand_kredit": gesamtaufwand_kredit})
        
        self.update_rent_income_chart()
        self.update_rent_expense_chart()
        self.update_roi_rent_chart()
        self.update_roi_energycost_chart()
        self.update_combi_roi_chart()
        self.update_kreditrechnung_tab()

    def update_rent_income_chart(self):
        """Tab 1: Mieteinnahmen Entwicklung Vermieter - Balkendiagramm"""
        input_data = self.input_data_dict
        result_data = self.result_data_dict
        inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum = self.return_manual_factors()
        
        # 1. Datensätze erstellen
        set_betriebskosten_saniert = QBarSet("umlagefähige Betriebskosten - saniert")
        set_nettokaltmiete_saniert = QBarSet("Nettokaltmiete - saniert")
        set_betriebskosten_unsaniert = QBarSet("umlagefähige Betriebskosten - unsaniert")
        set_nettokaltmiete_unsaniert = QBarSet("Nettokaltmiete - unsaniert")
        
        set_betriebskosten_saniert.setColor(QColor("#f39845"))  # 8e44ad
        set_nettokaltmiete_saniert.setColor(QColor("#3498db"))
        set_betriebskosten_unsaniert.setColor(QColor("#f39845").lighter(150))
        set_nettokaltmiete_unsaniert.setColor(QColor("#3498db").lighter(150))
        
        # 1.1 Datensatz Betriebkosten - Mieterhöhung durch Anpassung der Betriebskosten (jedes Jahr)
        # Mieterhöhung durch Sanierung ist im 2. Wert index[1] schon berücksichtigt!
        betr_kosten_reihe = [result_data["betriebskosten"]]
        for x in range(1, betrachtungszeitraum + 1):
            betr_kosten_reihe.append(round(result_data["betriebskosten"] * ((1 + inflation) ** x), 2))
        
        # 1.2 Datensatz Nettokaltmiete - Mieterhöhung durch Anpassung an ortsübliche Vergleichsmiete (alle 3 Jahre)
        # Preisentwicklung ortsübliche Vergleichsmiete/ Mietspiegel Faktoren
        anstiegsfaktoren = []
        for x in range(betrachtungszeitraum):
            anstiegsfaktoren.append((1 + mietpreisentwicklung) ** x)
        # Prüfen, ob Kappungsgrenze innerhalb 3-Jahreszeitraum durch Mietpreisentwicklung (Neue Verträge) überschritten wird
        diff_kappungsgrenze = input_data["Kappungsgrenze"] - ((anstiegsfaktoren[3] / anstiegsfaktoren[0]) - 1)
        
        # reelle Miete wurde eingegeben
        if "Miete" in input_data and self.manual_miete_check.isChecked() is True:
            # SANIERTE Nettokaltmiete Reihen
            quotient_saniertmiete_mietspiegel = result_data["miete_pro_qm_saniert"] / input_data["Mietspiegel"]
            # <1: sanierte miete < mietspiegel; >1: sanierte miete > mietspiegel
            
            # sanierte Miete > Mietspiegel
            if quotient_saniertmiete_mietspiegel > 1:
                # Prüfung, in welchem Jahr die ortsübliche Vergleichsmiete das Niveau der Miete nach Sanierung überschreitet und eine Mieterhöhung möglich ist
                jahr_anstieg_mgl = next((index for index, faktor in enumerate(anstiegsfaktoren) if faktor > quotient_saniertmiete_mietspiegel), None)
                if jahr_anstieg_mgl is None:
                    # Stellt sicher, dass Datensatz-Erstellung unten funktioniert
                    jahr_anstieg_mgl = betrachtungszeitraum
                
                nettokaltmiete_reihe_saniert = []
                for x in range(jahr_anstieg_mgl):
                    nettokaltmiete_reihe_saniert.append(result_data["nettokaltmiete_saniert"])
                for x in range(jahr_anstieg_mgl, betrachtungszeitraum):
                    relative_x = x - jahr_anstieg_mgl
                    if diff_kappungsgrenze > 0:
                        # hier "%" weil alle 3 Jahre faktor neu berechnet mit x == entsprechendes Jahr
                        if relative_x % 3 == 0:
                            faktor = (1 + mietpreisentwicklung) ** x
                            mietniveau = result_data["nettokaltmiete_mietspiegel"] * faktor
                        nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
                    elif diff_kappungsgrenze < 0:
                        # hier "//" weil alle 3 Jahre Faktor + 1 [0, 0, 0, 1, 1, 1, 2, 2, 2 etc.]
                        dreijahresblock = relative_x // 3
                        faktor = ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
                        mietniveau = (result_data["nettokaltmiete_mietspiegel"] * ((1 + mietpreisentwicklung) ** jahr_anstieg_mgl)) * faktor
                        nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
                
            # sanierte Miete < Mietspiegel
            elif quotient_saniertmiete_mietspiegel <= 1:
                # Prüfen: Erreicht Anstieg mit Kappungsgrenze Niveau von Mietspiegel: Ja/Nein? Wenn ja wann? Ist immer eine Vielzahl von 3, da in 3er Blöcken erhöht wird
                anstiegsfaktoren_bis_mietspiegel = []
                for x in range(betrachtungszeitraum):
                    dreijahresblock = x // 3
                    faktor = quotient_saniertmiete_mietspiegel * ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
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
                    mietniveau = result_data["nettokaltmiete_saniert"] * ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
                    nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
                # wird nicht ausgeführt wenn jahr_mietspiegel_erreicht == betrachtungszeitraum
                for x in range(jahr_mietspiegel_erreicht, betrachtungszeitraum):
                    if x % 3 == 0:
                        faktor = (1 + mietpreisentwicklung) ** x
                        mietniveau = result_data["nettokaltmiete_mietspiegel"] * faktor
                    nettokaltmiete_reihe_saniert.append(round(mietniveau, 2))
            
            # UNSANIERTE Nettokaltmiete Reihen
            quotient_miete_mietspiegel = input_data["Miete"] / input_data["Mietspiegel"]
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
                    nettokaltmiete_reihe_unsaniert.append(result_data["nettokaltmiete_unsaniert"])
                for x in range(jahr_anstieg_mgl, betrachtungszeitraum):
                    relative_x = x - jahr_anstieg_mgl
                    if diff_kappungsgrenze > 0:
                        # hier "%" weil alle 3 Jahre faktor neu berechnet mit x == entsprechendes Jahr
                        if relative_x % 3 == 0:
                            faktor = (1 + mietpreisentwicklung) ** x
                            mietniveau = result_data["nettokaltmiete_mietspiegel"] * faktor
                        nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
                    elif diff_kappungsgrenze < 0:
                        # hier "//" weil alle 3 Jahre Faktor + 1 [0, 0, 0, 1, 1, 1, 2, 2, 2 etc.]
                        dreijahresblock = relative_x // 3
                        faktor = ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
                        mietniveau = (result_data["nettokaltmiete_mietspiegel"] * ((1 + mietpreisentwicklung) ** jahr_anstieg_mgl)) * faktor
                        nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
                
            # Unsaniert und reelle Miete < Mietspiegel
            elif quotient_miete_mietspiegel <= 1:
                # Prüfen: Erreicht Anstieg mit Kappungsgrenze Niveau von Mietspiegel: Ja/Nein? Wenn ja wann? Ist immer eine Vielzahl von 3, da in 3er Blöcken erhöht wird
                anstiegsfaktoren_bis_mietspiegel = []
                for x in range(betrachtungszeitraum):
                    dreijahresblock = x // 3
                    faktor = quotient_miete_mietspiegel * ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
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
                    mietniveau = result_data["nettokaltmiete_unsaniert"] * ((1 + input_data["Kappungsgrenze"]) ** dreijahresblock)
                    nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))
                # wird nicht ausgeführt wenn jahr_mietspiegel_erreicht == betrachtungszeitraum
                for x in range(jahr_mietspiegel_erreicht, betrachtungszeitraum):
                    if x % 3 == 0:
                        faktor = (1 + mietpreisentwicklung) ** x
                        mietniveau = result_data["nettokaltmiete_mietspiegel"] * faktor
                    nettokaltmiete_reihe_unsaniert.append(round(mietniveau, 2))

        # nur Mietspiegel wurde angegeben
        else:
            anstiegsfaktor_sanierung = result_data["miete_pro_qm_saniert"] / input_data["Mietspiegel"]
            jahr_anstieg_mgl = next((index for index, faktor in enumerate(anstiegsfaktoren) if faktor > anstiegsfaktor_sanierung), None)
            # Redundanz: Anstiegsjahr Index überprüfen
            if jahr_anstieg_mgl is None:
                # Stellt sicher, dass Datensatz-Erstellung unten funktioniert, wenn Anstiegsjahr außerhalb Betrachtungszeitraum
                jahr_anstieg_mgl = betrachtungszeitraum
            else:
                pass
            
            # saniert Datensatz generieren, welcher im nächsten Schritt basierend auf wann ein Mietanstieg möglich ist angepasst wird
            nettokaltmiete_reihe_saniert = []
            for x in range(jahr_anstieg_mgl):
                nettokaltmiete_reihe_saniert.append(result_data["nettokaltmiete_saniert"])
            for x in range(betrachtungszeitraum - jahr_anstieg_mgl):
                nettokaltmiete_reihe_saniert.append(result_data["nettokaltmiete_unsaniert"])
            
            # Ab dem Jahr, wo ein Anstieg zur Vergleichsmiete möglich ist, alle 3 Jahre Miete erhöhen und überprüfen, dass die Kappungsgrenze nicht überstiegen wird
            if jahr_anstieg_mgl < betrachtungszeitraum:
                if diff_kappungsgrenze > 0:
                    index = jahr_anstieg_mgl
                    faktor = anstiegsfaktoren[index]
                    for dreijahresblock_start in range(jahr_anstieg_mgl, betrachtungszeitraum, 3):
                        dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
                        # Ganzen 3er Jahresblock mit Anstiegsfaktor multiplizieren
                        nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende] = [round(v * faktor, 2) for v in nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende]]
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
                        neue_nettokaltmiete_kappgrenze = letzter_nettokaltmiete_wert * ((1 + input_data["Kappungsgrenze"]) ** zaehler)
                        nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende] = [round((v - v) + neue_nettokaltmiete_kappgrenze, 2) for v in nettokaltmiete_reihe_saniert[dreijahresblock_start:dreijahresblock_ende]]
                        zaehler += 1
            
            # unsaniert Datensatz
            nettokaltmiete_reihe_unsaniert = []
            for x in range(betrachtungszeitraum):
                nettokaltmiete_reihe_unsaniert.append(result_data["nettokaltmiete_unsaniert"])
                
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
            # bei überschreiten der kappungsgrenze Miete_unsaniert mit Kappungsgrenze multiplizieren
            elif diff_kappungsgrenze < 0:
                zaehler = 1
                for dreijahresblock_start in range(0, betrachtungszeitraum, 3):
                    dreijahresblock_ende = min(dreijahresblock_start + 3, betrachtungszeitraum)
                    nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende] = [round(v * ((1 + input_data["Kappungsgrenze"]) ** zaehler), 2) for v in nettokaltmiete_reihe_unsaniert[dreijahresblock_start:dreijahresblock_ende]]
                    zaehler += 1
            
        # damit Jahr 0 bzw. der Ausgangsfall angezeigt wird und Diagrammbeschriftung funktioniert
        nettokaltmiete_reihe_unsaniert.insert(0, result_data["nettokaltmiete_unsaniert"])
        nettokaltmiete_reihe_saniert.insert(0, result_data["nettokaltmiete_unsaniert"])
        
        # nettokaltmiete Datenreihe global machen für Amortisations Diagramm
        self.nettokaltmiete_reihe_saniert_global = nettokaltmiete_reihe_saniert
        self.nettokaltmiete_reihe_unsaniert_global = nettokaltmiete_reihe_unsaniert
        
        # Addieren beiden Datenreihen: Nettokaltmiete + Betriebskosten für Warmmiete Diagramm
        self.bruttokaltmiete_reihe_saniert = list(map(add, nettokaltmiete_reihe_saniert, betr_kosten_reihe))
        self.bruttokaltmiete_reihe_unsaniert = list(map(add, nettokaltmiete_reihe_unsaniert, betr_kosten_reihe))
        
        # Werte in QBarSet/Datensätzen aufnehmen
        # Daten interleaving -> sodass mehrere Balken nebeneinander in einem StackedBarChart sein können
        # Pro Datenpunkt nehmen wir 4 Werte auf [Daten A, Daten B, leer Spalte, leere Spalte]
        for x in range(betrachtungszeitraum + 1):
            set_betriebskosten_saniert.append([betr_kosten_reihe[x], 0, 0, 0])
            set_nettokaltmiete_saniert.append([nettokaltmiete_reihe_saniert[x], 0, 0, 0])
            set_betriebskosten_unsaniert.append([0, betr_kosten_reihe[x], 0, 0])
            set_nettokaltmiete_unsaniert.append([0, nettokaltmiete_reihe_unsaniert[x], 0, 0])

        # 2. Daten zu Serien hinzufügen
        series_saniert = QStackedBarSeries()
        series_saniert.append(set_nettokaltmiete_saniert)
        series_saniert.append(set_betriebskosten_saniert)
        series_saniert.setBarWidth(1.5)

        series_unsaniert = QStackedBarSeries()
        series_unsaniert.append(set_nettokaltmiete_unsaniert)
        series_unsaniert.append(set_betriebskosten_unsaniert)
        series_unsaniert.setBarWidth(1.5)
        
        # 3. Diagramm aufsetzen
        chart = QChart()
        chart.addSeries(series_saniert)
        chart.addSeries(series_unsaniert)
        chart.setTitle(f"Entwicklung Kaltmiete über {betrachtungszeitraum} Jahre")
        titel = chart.titleFont()
        titel.setBold(True)
        titel.setPointSize(12)
        chart.setTitleFont(titel)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 4. X-Achse aufsetzen mit Jahren
        jahreszahl = date.today().year #jetziges Jahr
        # jahreszahl = 0
        years = []
        for x in range(betrachtungszeitraum + 1):
            years.append(str(jahreszahl))
            jahreszahl += 1
        axis_x = QCategoryAxis()
        axis_x.setTitleText("Jahre")
        axis_x.setStartValue(-1)
        max_x = ((len(years) - 1) * 4) + 2.5
        axis_x.setRange(-1, max_x)
        for x, year in enumerate(years):
            # die Beschriftung wird exakt in die Mitte der kombinierten Balken positioniert
            # Jahr 1: -1 bis 2 (Mitte 0.5)
            # Jahr 2:  2 bis 5 (Mitte 3.5) usw.
            # automatisch wird die Mitte der definierten Spanne gelabelt
            axis_x.append(str(year), x * 4 + 2.5)
        axis_x.setGridLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series_saniert.attachAxis(axis_x)
        series_unsaniert.attachAxis(axis_x)
        
        # 5. Y-Achse aufsetzen mit €
        # axis_y = QValueAxis()
        # axis_y.setTickCount(11)
        axis_y = QCategoryAxis()
        axis_y.setTitleText("Bruttokaltmiete pro Jahr in €")
        # Dynamische Achse auf max. Wert und 10.000er gerundet
        max_betriebskosten_1 = max(betr_kosten_reihe)
        max_nettokaltmiete_1 = max(nettokaltmiete_reihe_saniert)
        max_wert_1 = max_nettokaltmiete_1 + max_betriebskosten_1
        max_betriebskosten_2 = max(betr_kosten_reihe)
        max_nettokaltmiete_2 = max(nettokaltmiete_reihe_unsaniert)
        max_wert_2 = max_nettokaltmiete_2 + max_betriebskosten_2
        if max_wert_1 > max_wert_2:
            max_wert = max_wert_1
        else: 
            max_wert = max_wert_2
        max_wert_gerundet = math.ceil(max_wert / 10000) * 10000
        axis_y.setRange(0, max_wert_gerundet)
        axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        tick_count = 11
        step = max_wert_gerundet / (tick_count - 1)
        for i in range(tick_count):
            val = i * step
            label_str = self.zahlen_deutsch(f"{val:,.2f}")
            axis_y.append(label_str, val)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series_saniert.attachAxis(axis_y)
        series_unsaniert.attachAxis(axis_y)
        
        # 6. in UI anzeigen
        chart.legend().setVisible(True) 
        chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view_landlord.setChart(chart)
        
    def update_rent_expense_chart(self):
        """Tab 2: Mietausgaben/Warmmiete Entwicklung Mieter - Balkendiagramm """   
        result_data = self.result_data_dict
        inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum = self.return_manual_factors()

        # 1. Datensätze erstellen
        set_bruttokaltmiete_saniert = QBarSet("Bruttokaltmiete - saniert")
        set_nebenkosten_saniert = QBarSet("Nebenkosten - saniert")
        set_bruttokaltmiete_unsaniert = QBarSet("Bruttokaltmiete - unsaniert")
        set_nebenkosten_unsaniert = QBarSet("Nebenkosten - unsaniert")
        
        set_bruttokaltmiete_saniert.setColor(QColor("#e74c3c"))
        set_nebenkosten_saniert.setColor(QColor("#0c757d")) # f39845
        set_bruttokaltmiete_unsaniert.setColor(QColor("#e74c3c").lighter(160))
        set_nebenkosten_unsaniert.setColor(QColor("#0c757d").lighter(160))
        
        # 1. Datenreihen generieren
        bruttokaltmiete_pro_monat_reihe_saniert = [(jahr / 12) for jahr in self.bruttokaltmiete_reihe_saniert]
        bruttokaltmiete_pro_monat_reihe_unsaniert = [(jahr / 12) for jahr in self.bruttokaltmiete_reihe_unsaniert]
        nebenkosten_reihe_saniert = [round(result_data["nebenkosten_unsaniert"], 2), round(result_data["nebenkosten_saniert"], 2)]
        for x in range(1, betrachtungszeitraum):
            nebenkosten_reihe_saniert.append(round(nebenkosten_reihe_saniert[1] * ((1 + energiepreisentwicklung) ** x), 2))
        nebenkosten_reihe_unsaniert = [round(result_data["nebenkosten_unsaniert"], 2)]
        for x in range(betrachtungszeitraum):
            nebenkosten_reihe_unsaniert.append(round(nebenkosten_reihe_unsaniert[0] * ((1 + energiepreisentwicklung) ** x), 2))
        
        # Nebenkosten Datenreihe global machen für Amortisations Diagramm
        self.nebenkosten_reihe_saniert_global = nebenkosten_reihe_saniert
        self.nebenkosten_reihe_unsaniert_global = nebenkosten_reihe_unsaniert
        
        # Werte in QBarSet/Datensätzen aufnehmen
        # Daten interleaving -> sodass mehrere Balken nebeneinander in einem StackedBarChart sein können
        # Pro Datenpunkt nehmen wir 4 Werte auf [Daten A, Daten B, leer Spalte, leere Spalte]
        for x in range(betrachtungszeitraum + 1):
            set_bruttokaltmiete_saniert.append([bruttokaltmiete_pro_monat_reihe_saniert[x], 0, 0, 0])
            set_nebenkosten_saniert.append([nebenkosten_reihe_saniert[x], 0, 0, 0])
            set_bruttokaltmiete_unsaniert.append([0, bruttokaltmiete_pro_monat_reihe_unsaniert[x], 0, 0])
            set_nebenkosten_unsaniert.append([0, nebenkosten_reihe_unsaniert[x], 0, 0])
        
        # 2. Daten zur Serie hinzufügen
        series_saniert = QStackedBarSeries()
        series_saniert.append(set_bruttokaltmiete_saniert)
        series_saniert.append(set_nebenkosten_saniert)
        series_saniert.setBarWidth(1.5)

        series_unsaniert = QStackedBarSeries()
        series_unsaniert.append(set_bruttokaltmiete_unsaniert)
        series_unsaniert.append(set_nebenkosten_unsaniert)
        series_unsaniert.setBarWidth(1.5)
        
        # 3. Diagramm aufsetzen
        chart = QChart()
        chart.addSeries(series_saniert)
        chart.addSeries(series_unsaniert)
        chart.setTitle(f"Entwicklung Warmmiete über {betrachtungszeitraum} Jahre")
        titel = chart.titleFont()
        titel.setBold(True)
        titel.setPointSize(12)
        chart.setTitleFont(titel)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 4. X-Achse aufsetzen mit Jahren
        jahreszahl = date.today().year #jetziges Jahr
        # jahreszahl = 0
        years = []
        for x in range(betrachtungszeitraum + 1):
            years.append(str(jahreszahl))
            jahreszahl += 1
        axis_x = QCategoryAxis()
        axis_x.setTitleText("Jahre")
        axis_x.setStartValue(-1)
        max_x = ((len(years) - 1) * 4) + 2.5
        axis_x.setRange(-1, max_x)
        for x, year in enumerate(years):
            # die Beschriftung wird exakt in die Mitte der kombinierten Balken positioniert
            # Jahr 1: -1 bis 2 (Mitte 0.5)
            # Jahr 2:  2 bis 5 (Mitte 3.5) usw.
            # automatisch wird die Mitte der definierten Spanne gelabelt
            axis_x.append(str(year), x * 4 + 2.5)
        axis_x.setGridLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series_saniert.attachAxis(axis_x)
        series_unsaniert.attachAxis(axis_x)
        
        # 5. Y-Achse aufsetzen mit €
        axis_y = QCategoryAxis()
        axis_y.setTitleText("Warmmiete pro Monat in €")
        # Dynamische Achse auf max. Wert und 1.000er gerundet
        max_bruttokaltmiete_1 = max(bruttokaltmiete_pro_monat_reihe_saniert)
        max_nebenkosten_1 = max(nebenkosten_reihe_saniert)
        max_wert_1 = max_bruttokaltmiete_1 + max_nebenkosten_1
        max_bruttokaltmiete_2 = max(bruttokaltmiete_pro_monat_reihe_unsaniert)
        max_nebenkosten_2 = max(nebenkosten_reihe_unsaniert)
        max_wert_2 = max_bruttokaltmiete_2 + max_nebenkosten_2
        if max_wert_1 > max_wert_2:
            max_wert = max_wert_1
        else: 
            max_wert = max_wert_2
        # axis_y.setRange(0, math.ceil(max_wert / 1000) * 1000)
        # axis_y.setTickCount(11)
        max_wert_gerundet = math.ceil(max_wert / 1000) * 1000
        axis_y.setRange(0, max_wert_gerundet)
        axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        tick_count = 11
        step = max_wert_gerundet / (tick_count - 1)
        for i in range(tick_count):
            val = i * step
            label_str = self.zahlen_deutsch(f"{val:,.2f}")
            axis_y.append(label_str, val)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series_saniert.attachAxis(axis_y)
        series_unsaniert.attachAxis(axis_y)
        
        # 6. in UI anzeigen
        chart.legend().setVisible(True) 
        chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view_renter.setChart(chart)
        
    def update_roi_rent_chart(self):
        """Tab 3: Amortisation der Investition über Nettokaltmieten - Balkendiagramm"""
        inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum = self.return_manual_factors()

        # 1. Datensatz erstellen
        set_roi = QBarSet("Investition")
        set_amortisation = QBarSet("kumulierte Differenz der sanierten zu unsanierten Jahresmieten")
        
        if self.manual_financial_check.isChecked() is True and self.manual_teilwohnflaeche_check.isChecked() is False:
            investition = self.result_data_dict["investition_beg"] + self.result_data_dict["zinsaufwand_kredit"]
        elif self.manual_financial_check.isChecked() is True and self.manual_teilwohnflaeche_check.isChecked() is True:
            investition = self.result_data_dict["teilinvestition"] + self.result_data_dict["zinsaufwand_kredit"]
        elif self.manual_financial_check.isChecked() is False and self.manual_teilwohnflaeche_check.isChecked() is True:
            investition = self.result_data_dict["teilinvestition"]
        else:
            investition = self.result_data_dict["investition_beg"]
        investitions_reihe = [investition]
        for x in range(betrachtungszeitraum):
            investitions_reihe.append(0)
        
        # kann 1. Index Null weglassen, da sowieso immer 0 durch beides im unsanierten Zustand in Reihen
        amortisation_reihe = []
        # Akkumulieren der Differenz der sanierten zur unsanierten Nettokaltmiete über die Jahre
        diff_nettokaltmieten_reihe = list(map(sub, self.nettokaltmiete_reihe_saniert_global, self.nettokaltmiete_reihe_unsaniert_global))
        nettokaltmiete_reihe_akkumuliert = list(accumulate(diff_nettokaltmieten_reihe))
        amortisation_reihe.extend(nettokaltmiete_reihe_akkumuliert)
        
        # Werte in QBarSet aufnehmen
        set_roi.append(investitions_reihe)
        set_amortisation.append(amortisation_reihe)
        
        set_roi.setColor(QColor("#e74c3c"))
        set_amortisation.setColor(QColor("#95a5a6"))

        # 2. Daten zur Serie hinzufügen
        series = QBarSeries()
        series.append(set_roi)
        series.append(set_amortisation)
        
        # 3. horizontale Line einfügen, um Amortisation gut zu erkennen
        invest_linie = QLineSeries()
        invest_linie.append(0, investitions_reihe[0])
        invest_linie.append(betrachtungszeitraum, investitions_reihe[0])
        invest_linie.setPen(QPen(QColor("#e74c3c"), 2, Qt.DashLine))
        invest_linie.setName("Investitionssumme")
        
        # 4. Diagramm aufsetzen
        chart = QChart()
        chart.addSeries(series)
        chart.addSeries(invest_linie)
        chart.setTitle("Amortisation der Investition über Nettokaltmieten bei Vermietung")
        titel = chart.titleFont()
        titel.setBold(True)
        titel.setPointSize(12)
        chart.setTitleFont(titel)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 5. X-Achse aufsetzen mit Jahren
        jahreszahl = date.today().year #jetziges Jahr
        # jahreszahl = 0
        years = []
        for x in range(betrachtungszeitraum + 1):
            years.append(str(jahreszahl))
            jahreszahl += 1
        
        axis_x = QBarCategoryAxis()
        axis_x.setTitleText("Jahre")
        axis_x.append(years)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        invest_linie.attachAxis(axis_x)
        
        # 6. Y-Achse aufsetzen mit €
        axis_y = QCategoryAxis()
        axis_y.setTitleText("in €")
        # Dynamische Achse: Vergleich ob Investitions- oder Amortisationsreihe größer sind und auf 10.000er gerundet
        max_roi = max(investitions_reihe)
        max_amortisation = max(amortisation_reihe)
        if max_roi < max_amortisation:
            max_wert = max_amortisation
        else:
            max_wert = max_roi
        # axis_y.setRange(0, math.ceil(max_wert / 10000) * 10000)
        # axis_y.setTickCount(11)
        max_wert_gerundet = math.ceil(max_wert / 10000) * 10000
        axis_y.setRange(0, max_wert_gerundet)
        axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        tick_count = 11
        step = max_wert_gerundet / (tick_count - 1)
        for i in range(tick_count):
            val = i * step
            label_str = self.zahlen_deutsch(f"{val:,.2f}")
            axis_y.append(label_str, val)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        invest_linie.attachAxis(axis_y)
        
        # 7. in UI anzeigen
        chart.legend().setVisible(True) 
        chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view_investment_rent.setChart(chart)
        
    def update_roi_energycost_chart(self):
        """Tab 4: Amortisation der Investition über Nebenkosteneinsparung - Balkendiagramm"""
        inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum = self.return_manual_factors()

        # 1. Datensatz erstellen
        set_roi = QBarSet("Investition")
        set_amortisation = QBarSet("kumulierte Differenz der sanierten zu unsanierten Nebenkosten")
        
        if self.manual_financial_check.isChecked() is True and self.manual_teilwohnflaeche_check.isChecked() is False:
            investition = self.result_data_dict["investition_beg"] + self.result_data_dict["zinsaufwand_kredit"]
        elif self.manual_financial_check.isChecked() is True and self.manual_teilwohnflaeche_check.isChecked() is True:
            investition = self.result_data_dict["teilinvestition"] + self.result_data_dict["zinsaufwand_kredit"]
        elif self.manual_financial_check.isChecked() is False and self.manual_teilwohnflaeche_check.isChecked() is True:
            investition = self.result_data_dict["teilinvestition"]
        else:
            investition = self.result_data_dict["investition_beg"]
        investitions_reihe = [investition]
        for x in range(betrachtungszeitraum):
            investitions_reihe.append(0)
        
        # kann 1. Index Null weglassen, da sowieso immer 0 durch beides im unsanierten Zustand in Reihen
        amortisation_reihe = []
        
        # Bedingte Anzeige der Nebenkosten, die vom Eigentümer getragen werden, wenn Eigentümer Teilwohnfläche bezieht
        if "Teilwohnflaeche" in self.input_data_dict and self.manual_eigentum_teilvermietet_check.isChecked() is True:
            eigentuemeranteil = self.input_data_dict["Teilwohnflaeche"] / self.input_data_dict["Wohnflaeche"]
            nebenkosten_eigentuemer_unsaniert = round((self.input_data_dict["Energiekosten unsaniert"] * eigentuemeranteil) / 12, 2)
            nebenkosten_eigentuemer_saniert = round((self.input_data_dict["Energiekosten saniert"] * eigentuemeranteil) / 12, 2)
            text = (
                "Vom Eigentümer getragene Nebenkosten " +
                self.zahlen_deutsch(f"<font color='#c0392b'><b>unsaniert {nebenkosten_eigentuemer_unsaniert:,.2f} €/Monat</b></font> und ") +
                self.zahlen_deutsch(f"<font color='#2980b9'><b>saniert {nebenkosten_eigentuemer_saniert:,.2f} €/Monat</b></font>")
            )
            self.label_nebenkosten_eigentuemer.setText(text)
            self.label_nebenkosten_eigentuemer.setVisible(True)
            nebenkosten_projahr_reihe_saniert = [nebenkosten_eigentuemer_unsaniert * 12, nebenkosten_eigentuemer_saniert * 12]
            for x in range(1, betrachtungszeitraum):
                nebenkosten_projahr_reihe_saniert.append(round(nebenkosten_projahr_reihe_saniert[1] * ((1 + energiepreisentwicklung) ** x), 2))
            nebenkosten_projahr_reihe_unsaniert = [nebenkosten_eigentuemer_unsaniert * 12]
            for x in range(betrachtungszeitraum):
                nebenkosten_projahr_reihe_unsaniert.append(round(nebenkosten_projahr_reihe_unsaniert[0] * ((1 + energiepreisentwicklung) ** x), 2))
            # Akkumulieren der Differenz der sanierten zur unsanierten Nettokaltmiete über die Jahre
            diff_nebenkosten_reihe = list(map(sub, nebenkosten_projahr_reihe_unsaniert, nebenkosten_projahr_reihe_saniert))
            nebenkosten_reihe_akkumuliert = list(accumulate(diff_nebenkosten_reihe))
            amortisation_reihe.extend(nebenkosten_reihe_akkumuliert)
        else:
            self.label_nebenkosten_eigentuemer.setVisible(False)
            nebenkosten_projahr_reihe_saniert = [x * 12 for x in self.nebenkosten_reihe_saniert_global]
            nebenkosten_projahr_reihe_unsaniert = [x * 12 for x in self.nebenkosten_reihe_unsaniert_global]
            # Akkumulieren der Differenz der sanierten zur unsanierten Nettokaltmiete über die Jahre
            diff_nebenkosten_reihe = list(map(sub, nebenkosten_projahr_reihe_unsaniert, nebenkosten_projahr_reihe_saniert))
            nebenkosten_reihe_akkumuliert = list(accumulate(diff_nebenkosten_reihe))
            amortisation_reihe.extend(nebenkosten_reihe_akkumuliert)
        
        # Werte in QBarSet aufnehmen
        set_roi.append(investitions_reihe)
        set_amortisation.append(amortisation_reihe)
        
        set_roi.setColor(QColor("#e74c3c"))
        set_amortisation.setColor(QColor("#95a5a6"))

        # 2. Daten zur Serie hinzufügen
        series = QBarSeries()
        series.append(set_roi)
        series.append(set_amortisation)
        
        # 3. horizontale Line einfügen, um Amortisation gut zu erkennen
        invest_linie = QLineSeries()
        invest_linie.append(0, investitions_reihe[0])
        invest_linie.append(betrachtungszeitraum, investitions_reihe[0])
        invest_linie.setPen(QPen(QColor("#e74c3c"), 2, Qt.DashLine))
        invest_linie.setName("Investitionssumme")
        
        # 4. Diagramm aufsetzen
        chart = QChart()
        chart.addSeries(series)
        chart.addSeries(invest_linie)
        chart.setTitle("Amortisation der Investition über Nebenkosteneinsparung bei selbstgenutztem Eigentum")
        titel = chart.titleFont()
        titel.setBold(True)
        titel.setPointSize(12)
        chart.setTitleFont(titel)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 5. X-Achse aufsetzen mit Jahren
        jahreszahl = date.today().year #jetziges Jahr
        # jahreszahl = 0
        years = []
        for x in range(betrachtungszeitraum + 1):
            years.append(str(jahreszahl))
            jahreszahl += 1
        
        axis_x = QBarCategoryAxis()
        axis_x.setTitleText("Jahre")
        axis_x.append(years)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        invest_linie.attachAxis(axis_x)
        
        # 6. Y-Achse aufsetzen mit €
        axis_y = QCategoryAxis()
        axis_y.setTitleText("in €")
        # Dynamische Achse: Vergleich ob Investitions- oder Amortisationsreihe größer sind und auf 10.000er gerundet
        max_roi = max(investitions_reihe)
        max_amortisation = max(amortisation_reihe)
        if max_roi < max_amortisation:
            max_wert = max_amortisation
        else:
            max_wert = max_roi
        # axis_y.setRange(0, math.ceil(max_wert / 10000) * 10000)
        # axis_y.setTickCount(11)
        max_wert_gerundet = math.ceil(max_wert / 10000) * 10000
        axis_y.setRange(0, max_wert_gerundet)
        axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        tick_count = 11
        step = max_wert_gerundet / (tick_count - 1)
        for i in range(tick_count):
            val = i * step
            label_str = self.zahlen_deutsch(f"{val:,.2f}")
            axis_y.append(label_str, val)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        invest_linie.attachAxis(axis_y)
        
        # 7. in UI anzeigen
        chart.legend().setVisible(True) 
        chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view_investment_energycost.setChart(chart)
        
    def update_combi_roi_chart(self):
        """Tab 5: Kombi-Amortisation der Investition über Nettokaltmieten und Nebenkosten des Eigentümers kombiniert - Balkendiagramm"""
        inflation, energiepreisentwicklung, mietpreisentwicklung, betrachtungszeitraum = self.return_manual_factors()
        
        # Diagramm Tab nur anzeigen, wenn Haken gesetzt
        tab_index = self.chart_tabs.indexOf(self.chart_view_combi_energycost_rent)
        if self.manual_eigentum_teilvermietet_check.isChecked() is True:
            # Falls Haken gesetzt aber Tab ist nicht da (-1), Tabs hinzufügen
            if tab_index == -1:
                self.chart_tabs.addTab(self.chart_view_combi_energycost_rent, "Kombi-Amortisation bei Teileigennutzung Eigentümer")
       
            # 1. Datensatz erstellen
            set_roi = QBarSet("Investition")
            set_amortisation = QBarSet("kumulierte Differenz der sanierten zu unsanierten Jahresmieten")
            
            if self.manual_financial_check.isChecked() is True:
                investition =  self.result_data_dict["investition_beg"] + self.result_data_dict["zinsaufwand_kredit"]
            else:
                investition = self.result_data_dict["investition_beg"]
            investitions_reihe = [investition]
            for x in range(betrachtungszeitraum):
                investitions_reihe.append(0)
            
            # kann 1. Index Null weglassen, da sowieso immer 0 durch beides im unsanierten Zustand in Reihen
            amortisation_nettokaltmieten_reihe = []
            # Akkumulieren der Differenz der sanierten zur unsanierten Nettokaltmiete über die Jahre
            diff_nettokaltmieten_reihe = list(map(sub, self.nettokaltmiete_reihe_saniert_global, self.nettokaltmiete_reihe_unsaniert_global))
            nettokaltmiete_reihe_akkumuliert = list(accumulate(diff_nettokaltmieten_reihe))
            amortisation_nettokaltmieten_reihe.extend(nettokaltmiete_reihe_akkumuliert)
            
            # Erstellung nur Eigentümer Nebenkosten Reihe
            amortisation_nebenkosten_reihe = []
            teil_nebenkosten_eigentuemer_faktor = self.input_data_dict["Teilwohnflaeche"] / self.input_data_dict["Wohnflaeche"]
            nebenkosten_eigentuemer_unsaniert = round((self.input_data_dict["Energiekosten unsaniert"] * teil_nebenkosten_eigentuemer_faktor) / 12, 2)
            nebenkosten_eigentuemer_saniert = round((self.input_data_dict["Energiekosten saniert"] * teil_nebenkosten_eigentuemer_faktor) / 12, 2)
            nebenkosten_projahr_reihe_saniert = [nebenkosten_eigentuemer_unsaniert * 12, nebenkosten_eigentuemer_saniert * 12]
            for x in range(1, betrachtungszeitraum):
                nebenkosten_projahr_reihe_saniert.append(round(nebenkosten_projahr_reihe_saniert[1] * ((1 + energiepreisentwicklung) ** x), 2))
            nebenkosten_projahr_reihe_unsaniert = [nebenkosten_eigentuemer_unsaniert * 12]
            for x in range(betrachtungszeitraum):
                nebenkosten_projahr_reihe_unsaniert.append(round(nebenkosten_projahr_reihe_unsaniert[0] * ((1 + energiepreisentwicklung) ** x), 2))
            # Akkumulieren der Differenz der sanierten zur unsanierten Nettokaltmiete über die Jahre
            diff_nebenkosten_reihe = list(map(sub, nebenkosten_projahr_reihe_unsaniert, nebenkosten_projahr_reihe_saniert))
            nebenkosten_reihe_akkumuliert = list(accumulate(diff_nebenkosten_reihe))
            amortisation_nebenkosten_reihe.extend(nebenkosten_reihe_akkumuliert)
            
            # addieren beider Amortisationen zusammen
            amortisation_reihe = list(map(add, amortisation_nettokaltmieten_reihe, amortisation_nebenkosten_reihe))
            
            # Werte in QBarSet aufnehmen
            set_roi.append(investitions_reihe)
            set_amortisation.append(amortisation_reihe)
            
            set_roi.setColor(QColor("#e74c3c"))
            set_amortisation.setColor(QColor("#95a5a6"))
    
            # 2. Daten zur Serie hinzufügen
            series = QBarSeries()
            series.append(set_roi)
            series.append(set_amortisation)
            
            # 3. horizontale Line einfügen, um Amortisation gut zu erkennen
            invest_linie = QLineSeries()
            invest_linie.append(0, investitions_reihe[0])
            invest_linie.append(betrachtungszeitraum, investitions_reihe[0])
            invest_linie.setPen(QPen(QColor("#e74c3c"), 2, Qt.DashLine))
            invest_linie.setName("Investitionssumme")
            
            # 4. Diagramm aufsetzen
            chart = QChart()
            chart.addSeries(series)
            chart.addSeries(invest_linie)
            chart.setTitle("Amortisation der Investition über Kombination aus Nettokaltmieten und eigene Nebenkosten Eigentümer")
            titel = chart.titleFont()
            titel.setBold(True)
            titel.setPointSize(12)
            chart.setTitleFont(titel)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            
            # 5. X-Achse aufsetzen mit Jahren
            jahreszahl = date.today().year #jetziges Jahr
            # jahreszahl = 0
            years = []
            for x in range(betrachtungszeitraum + 1):
                years.append(str(jahreszahl))
                jahreszahl += 1
            
            axis_x = QBarCategoryAxis()
            axis_x.setTitleText("Jahre")
            axis_x.append(years)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            invest_linie.attachAxis(axis_x)
            
            # 6. Y-Achse aufsetzen mit €
            axis_y = QCategoryAxis()
            axis_y.setTitleText("in €")
            # Dynamische Achse: Vergleich ob Investitions- oder Amortisationsreihe größer sind und auf 10.000er gerundet
            max_roi = max(investitions_reihe)
            max_amortisation = max(amortisation_reihe)
            if max_roi < max_amortisation:
                max_wert = max_amortisation
            else:
                max_wert = max_roi
            max_wert_gerundet = math.ceil(max_wert / 10000) * 10000
            axis_y.setRange(0, max_wert_gerundet)
            axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
            tick_count = 11
            step = max_wert_gerundet / (tick_count - 1)
            for i in range(tick_count):
                val = i * step
                label_str = self.zahlen_deutsch(f"{val:,.2f}")
                axis_y.append(label_str, val)
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            invest_linie.attachAxis(axis_y)
            
            # 7. in UI anzeigen
            chart.legend().setVisible(True) 
            chart.legend().setAlignment(Qt.AlignBottom)
            self.chart_view_combi_energycost_rent.setChart(chart)
        
        else:
            # Falls kein Haken gesetzt und Tab ist da, Tab entfernen
            if tab_index != -1:
                self.chart_tabs.removeTab(tab_index)
                
    def update_kreditrechnung_tab(self):
        """Tab 6: Ergebnisse der Kreditrechnung anzeigen"""
        result_data = self.result_data_dict
                
        # Diagramm Tab nur anzeigen, wenn Haken gesetzt
        tab_index = self.chart_tabs.indexOf(self.tab6_kreditrechnung)
        if self.manual_financial_check.isChecked() is True:
            # Falls Haken gesetzt aber Tab ist nicht da (-1), Tabs hinzufügen
            if tab_index == -1:
                self.chart_tabs.addTab(self.tab6_kreditrechnung, "Annuitätendarlehen")
                
            self.widget_fremdkapital_quote.setText(self.zahlen_deutsch(f"{result_data['fremdkapital_quote']:,.2f} %"))
            self.widget_eigenkapital_quote.setText(self.zahlen_deutsch(f"{result_data['eigenkapital_quote']:,.2f} %"))
            self.widget_annuitaet.setText(self.zahlen_deutsch(f"{result_data['annuitaet']:,.2f} €"))
            self.widget_zinsaufwand.setText(self.zahlen_deutsch(f"{result_data['zinsaufwand_kredit']:,.2f} €"))
            self.widget_gesamtaufwand.setText(self.zahlen_deutsch(f"{result_data['gesamtaufwand_kredit']:,.2f} €"))
        else:
            # Falls kein Haken gesetzt und Tab ist da, Tab entfernen
            if tab_index != -1:
                self.chart_tabs.removeTab(tab_index)
            
    def pdf_export(self):
        """Berechnungsergebnisse als PDF exportieren"""
        try:
            # Nutzer den Speicherort wählen lassen
            default_path = QStandardPaths.writableLocation(
                QStandardPaths.DocumentsLocation
            )
            zeitpunkt = datetime.now().strftime('%d%m%Y_%H%M')
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Bericht speichern",
                os.path.join(default_path, f"Ensaklar_bericht_{zeitpunkt}.pdf"),
                "PDF Files (*.pdf)"
            )
            if not file_path:  # Nutzer hat abgebrochen
                return
            
            # Daten zusammenstellen
            input_data = self.input_data_dict
            if input_data['Grundstuecksart'] == 1:
                grundstueck = "Ein- oder Zweifamilienhaus"
            elif input_data['Grundstuecksart'] == 2:
                grundstueck = "Wohneigentum"
            else:
                grundstueck = "Mietwohnung/-en"
            if input_data['Kappungsgrenze'] == 0.15:
                kappungsgrenze = "Gebiet mit abgesenkter Kappungsgrenze"
            else:
                kappungsgrenze = "keine Sonderregelung vorhanden"
            input_table_data = [
                ["Gebäude-Parameter", "Wert"],
                ["Baujahr (oder Jahr Kernsanierung)", f"{input_data['Baujahr']}"],
                ["Mietspiegel", self.zahlen_deutsch(f"{input_data['Mietspiegel']:,.2f}") + " €/m²"],
                ["Bodenrichtwert", self.zahlen_deutsch(f"{input_data['Bodenrichtwert']:,.2f}") + " €/m²"],
                ["Gesamtwohnfläche", self.zahlen_deutsch(f"{input_data['Wohnflaeche']:,.2f}") + " m²"],
                ["Anzahl Wohneinheiten", f"{input_data['Wohnungsanzahl']}"],
                ["Grundstücksfläche", self.zahlen_deutsch(f"{input_data['Grundstuecksflaeche']:,.2f}") + " m²"],
                ["Grundstücksart", grundstueck],
                ["Mietkappungsgrenze", kappungsgrenze],
                ]
            if self.manual_miete_check.isChecked() is True:
                input_table_data.append(["Reelle Miete", self.zahlen_deutsch(f"{input_data['Miete']:,.2f}") + " €/m²"])
            if self.manual_teilwohnflaeche_check.isChecked() is True:
                input_table_data.append(["Betrachtete Teilwohnfläche", self.zahlen_deutsch(f"{input_data['Teilwohnflaeche']:,.2f}") + " m²"])
            
            result_data = self.result_data_dict
            result_table_data = [
                ["Ergebnis-Parameter", "unsanierter Zustand", "nach Sanierung", "Einheit"],
                ["Immobilienwert", self.zahlen_deutsch(f"{result_data['ertragswert_unsaniert']:,.2f}"), self.zahlen_deutsch(f"{result_data['ertragswert_saniert']:,.2f}"), "€"],
                ["Kaltmiete", self.zahlen_deutsch(f"{result_data['bruttokaltmiete_unsaniert']:,.2f}"), self.zahlen_deutsch(f"{result_data['bruttokaltmiete_saniert']:,.2f}"), "€/Monat"],
                ["Neben- bzw. Energiekosten", self.zahlen_deutsch(f"{result_data['nebenkosten_unsaniert']:,.2f}"), self.zahlen_deutsch(f"{result_data['nebenkosten_saniert']:,.2f}"), "€/Monat"],
                ]
            
            kosten_data = [
                ["Vorraussichtliche Gesamtkosten der Sanierung:", self.zahlen_deutsch(f"{input_data['Sanierungskosten BEG']:,.2f}") + " €"],
                ["Vorraussichtliche Gesamtförderung:", self.zahlen_deutsch(f"{result_data['gesamtfoerderung_beg']:,.2f}") + " €"],
                ["Angesetzte Investitionssumme:", self.zahlen_deutsch(f"{result_data['investition_beg']:,.2f}") + " €"],
            ]
            if self.manual_teilwohnflaeche_check.isChecked() is True:
                kosten_data.append(["Miteigentumsanteil an der Investition:", self.zahlen_deutsch(f"{result_data['teilinvestition']:,.2f}") + " €"])
            
            kredit_data = []
            if self.manual_financial_check.isChecked() is True:
                kreditsumme, jahreszins, laufzeit = self.return_manual_kredit()
                jahreszins_prozent = jahreszins * 100
                kredit_data.append(["Kreditsumme:", self.zahlen_deutsch(f"{kreditsumme:,.2f}") + " €"])
                kredit_data.append(["Laufzeit:", self.zahlen_deutsch(f"{laufzeit:,.2f}") + " Monate"])
                kredit_data.append(["Effektiver Jahreszins:", self.zahlen_deutsch(f"{jahreszins_prozent:,.2f}") + " % pro Jahr"])
                kredit_data.append(["Annuität:", self.zahlen_deutsch(f"{result_data['annuitaet']:,.2f}") + " €"])
                kredit_data.append(["Zinsaufwand:", self.zahlen_deutsch(f"{result_data['zinsaufwand_kredit']:,.2f}") + " €"])
                kredit_data.append(["Gesamtaufwand Kredit:", self.zahlen_deutsch(f"{result_data['gesamtaufwand_kredit']:,.2f}") + " €"])
            
            bericht_items = [
                {
                    "diagramm": self.chart_view_landlord,
                    "titel": "Entwicklung der Kaltmiete",
                    "text": """In diesem Diagramm ist die Entwicklung der Kaltmiete über die nächsten Jahre zu sehen. 
                    Die prognostizierte Entwicklung basiert auf der aktuellen Gesetzeslage sowie den erwartbaren 
                    Verbraucherpreisen. Es werden drei Möglichkeiten zur Mieterhöhung und deren legalen zeitlichen Intervallen 
                    berücksichtigt: durch Modernisierung, eine Anpassung an die Vergleichsmiete und die Umlegung von steigenden Betriebskosten."""
                },
                {
                    "diagramm": self.chart_view_renter,
                    "titel": "Entwicklung der Warmiete",
                    "text": """Dieses Diagramm zeigt die Entwicklung der Warmmiete für Mieter. Dazu werden die Bruttokaltmiete (siehe Diagramm 1)
                    und Nebenkosten bzw. Energiekosten dargestellt. Die Nebenkosten werden mittels der erwartbaren Energiepreisentwicklung modelliert."""
                },
                {
                    "diagramm": self.chart_view_investment_rent,
                    "titel": "Armortisation der Investition über Nettokaltmieten",
                    "text": """Dieses Diagramm zeigt die Amortisation der Investitionskosten über die extra Mieteinnahmen. 
                    Dazu ist der Unterschied zwischen den Nettokaltmieten im unsanierten und sanierten Zustand kumuliert dargestellt."""
                },
                {
                    "diagramm": self.chart_view_investment_energycost,
                    "titel": "Armortisation der Investition über Nebenkosteneinsparung",
                    "text": """Dieses Diagramm zeigt die Amortisation der Investitionskosten über die eingesparten Nebenkosten. 
                    Dazu sind die eingesparten Nebenkosten der betrachteten Wohnfläche kumuliert dargestellt."""
                }
            ]
            if self.manual_eigentum_teilvermietet_check.isChecked() is True:
                bericht_items.append({
                        "diagramm": self.chart_view_combi_energycost_rent,
                        "titel": "Kombi-Armortisation der Investition über Nettokaltmieten und Nebenkosteneinsparung",
                        "text": """Dieses Diagramm zeigt die Amortisation der Investitionskosten für den Fall, wenn der 
                        Eigentümer im Gebäude lebt und einen Teil vermietet. Dazu sind die eingesparten Nebenkosten der 
                        Wohnfläche des Eigentums mit den Nettokaltmieten der vermieteten Fläche kumuliert dargestellt."""
                    })
            
            # ReportLab PDF bauen
            doc = SimpleDocTemplate(file_path)
            styles = getSampleStyleSheet()
            story = []
            open_buffers = []
            
            safe_width = doc.width
            
            # Titel und Intro
            title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1a1a1a',
            spaceAfter=30,
            alignment=TA_CENTER
            )
            story.append(Paragraph("Ergebnisbericht Ensaklar", title_style))
            zeitpunkt = datetime.now().strftime('%d.%m.%Y %H:%M')
            intro_text = f"""
            Dieser Bericht enthält die Ergebnisse und Visualisierungen aus Ensaklar vom  
            {zeitpunkt}. Im Folgenden finden Sie die Rahmenparameter Ihres Gebäudes 
            sowie die daraus resultierenden Ergebnisse.
            """
            story.append(Paragraph(intro_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Eingabeparameter Tabelle erstellen
            input_table = Table(input_table_data, colWidths=[safe_width * 0.5, safe_width * 0.5])
            input_table.setStyle(TableStyle([
                # Titelzeile
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                # Inhalt
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                # Ausrichtung
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                # Abwechselnde Zeilenfarben
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                # Rahmen
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(input_table)
            story.append(Spacer(1, 10))
            
            # Ergebnis Tabelle erstellen
            # Spalten passend anordnen
            col_widths = [safe_width * 0.4, safe_width * 0.25, safe_width * 0.25, safe_width * 0.1]
            results_table = Table(result_table_data, colWidths=col_widths)
            
            # Tabellenstil anpassen
            # Koordinaten in ReportLab (Spalte, Reihe). (-1, -1) gleich ganz am Ende.
            table_style = TableStyle([
                # Titelzeile
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                # Inhalt
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                # Ausrichtung
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Spalte 1 linksbündig
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Spalte 2 mittig
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Spalte 3 mittig
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),   # Spalte 4 rechtsbündig
                # Abwechselnde Zeilenfarben
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                # Rahmen
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ])
            results_table.setStyle(table_style)
            story.append(results_table)
            
            # Investitionssumme und Förderung als Tabelle hinzufügen
            story.append(Spacer(1, 20))
            kosten_table = Table(kosten_data, colWidths=[safe_width * 0.75, safe_width * 0.25])
            kosten_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.red),
                ('TEXTCOLOR', (1, 1), (1, 1), colors.green),
                ('TEXTCOLOR', (1, 2), (1, 2), colors.red),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(kosten_table)
            
            # Kreditrechnung als Tabelle hinzufügen
            story.append(Spacer(1, 10))
            if self.manual_financial_check.isChecked() is True:
                kredit_table = Table(kredit_data, colWidths=[safe_width * 0.75, safe_width * 0.25])
                kredit_table.setStyle(TableStyle([
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(kredit_table)
            
            # Diagramme auf neuer Seite starten lassen
            story.append(PageBreak())
            
            # Für die perfekte Größenanpassung der Diagramme auf einer A4 Seite
            chart_width = doc.width * 0.95
            
            # 4. Loop für Diagramme 
            for item in bericht_items:
                # Image buffer generieren
                img_buffer, aspect_ratio = self.get_chart_python_buffer(item["diagramm"])
                open_buffers.append(img_buffer) # Save reference so we can close it later
                
                # ReportLab Image erstellen
                chart_height = chart_width * aspect_ratio
                rl_image = Image(img_buffer, width=chart_width, height=chart_height)
                rl_image.hAlign = 'CENTER'

                # Block mit allen Infos erstellen. KeepTogether damit alle zusammen bleiben und nicht auf unterschiedlichen Seiten
                chart_block = [
                    Paragraph(item["titel"], styles['Heading2']),
                    Spacer(1, 5),
                    rl_image,
                    Spacer(1, 10),
                    Paragraph(item["text"], styles['Normal']),
                    Spacer(1, 20) # Platz vor nächstem Diagramm
                ]
                # Zum PDF hinzufügen
                story.append(KeepTogether(chart_block))
            
            # PDF generieren
            doc.build(
                story, 
                onFirstPage=self.fusszeile_pdf, 
                onLaterPages=self.fusszeile_pdf
                )
            
            # Rückmeldung, ob erfolgreich
            QMessageBox.information(
                self,
                "Export erfolgreich",
                f"PDF wurde gespeichert:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export fehlgeschlagen",
                f"Fehler während Export: {str(e)}"
            )
        finally:
            # alle Buffer müssen zum Schluss geschlossen werden damit RAM frei wird
            for buf in open_buffers:
                buf.close()
                
    def get_chart_python_buffer(self, chart_view):
        """Wandelt QChartView in ein in-memory PNG python buffer."""
        # genaue Größe des Diagramms auslesen
        scene = chart_view.scene()
        source_rect = scene.sceneRect()
        
        # aspect ratio dynamisch
        aspect_ratio = source_rect.height() / source_rect.width()
        hi_res_width = 1920
        hi_res_height = int(hi_res_width * aspect_ratio)
        
        # Canvas mit gleicher Größe erstellen
        high_res_image = QImage(hi_res_width, hi_res_height, QImage.Format_ARGB32)
        high_res_image.fill(Qt.white)

        # Diagramm auf Canvas mit gleicher Größe setzen
        painter = QPainter(high_res_image)
        painter.setRenderHint(QPainter.Antialiasing)
        target_rect = QRectF(0, 0, hi_res_width, hi_res_height)
        scene.render(painter, target_rect, source_rect)
        painter.end()
        
        # Qt Memory Buffer
        q_buffer = QBuffer()
        q_buffer.open(QIODevice.ReadWrite)
        high_res_image.save(q_buffer, "PNG")

        # Zu Python io.BytesIO
        python_buffer = io.BytesIO(q_buffer.data())
        python_buffer.seek(0)
        
        q_buffer.close() # Qt buffer schließen
        return python_buffer, aspect_ratio
    
    def fusszeile_pdf(self, canvas, doc):
        """Fußzeile mit Seitenzahl und Export-Quellen Beschreibung"""
        canvas.saveState() # Save the current drawing state

        # Fußzeile Font, Größe und Text
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.dimgrey)
        page_number_text = f"Seite {canvas.getPageNumber()}"
        report_name_text = "Ergebnisse aus Ensaklar"

        # Seitenbreite sodass die Fußzeile passt
        page_width = doc.pagesize[0]

        # leichte graue Linie hinzufügen
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(0.5)
        # Position 50 vom Seitenende
        canvas.line(doc.leftMargin, 50, page_width - doc.rightMargin, 50)

        # Text, Position 35 vom Seitenende sowie links und rechts aligned
        canvas.drawString(doc.leftMargin, 35, report_name_text) 
        canvas.drawRightString(page_width - doc.rightMargin, 35, page_number_text)

        canvas.restoreState()
        
    def reset_programm(self):
        """Startet das Programm neu im initialen Zustand"""
        QCoreApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)
        
    def zahlen_deutsch(self, string):
        """Passt die Schreibweise von Ziffern/Nummern/Zahlen von 100,000.00 auf die deutsche Schreibweise 100.000,00 an"""
        string_angepasst = string.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return string_angepasst
        


if __name__ == "__main__":
    # Damit das Programm-Icon auch in der Taskbar angezeigt wird
    try:
        import ctypes
        myappid = 'ensaklar.app.jgrunenb'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except (ImportError, AttributeError):
        pass  # Not on Windows, skip
    
    # Sichere App-Erzeugung, sodass nach Windowschließen ein neuer Prozess gestartet werden kann
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(True)

    window = EnsaklarApp()
    window.show()

    sys.exit(app.exec())

