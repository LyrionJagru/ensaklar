# -*- coding: utf-8 -*-
"""
Created on Sat Feb  7 16:20:35 2026

@author: jbgru
"""

# import PySide6.QtCore

# # Prints PySide6 version
# print(PySide6.__version__)

# # Prints the Qt version used to compile PySide6
# print(PySide6.QtCore.__version__)

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton

class SimpleApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Set up the Main Window
        self.setWindowTitle("My PyQt5 App")
        self.setGeometry(100, 100, 300, 200)  # (x, y, width, height)

        # 2. Create a Central Widget and Layout
        # QMainWindow requires a "central widget" to hold other widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # 3. Add Widgets
        self.label = QLabel("Hello! Click the button below.")
        self.layout.addWidget(self.label)

        self.button = QPushButton("Click Me!")
        self.layout.addWidget(self.button)

        # 4. Connect Signals to Slots (Events)
        self.button.clicked.connect(self.on_button_click)

    def on_button_click(self):
        self.label.setText("Button Clicked! Welcome to PyQt5.")

# 5. Run the Application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleApp()
    window.show()
    sys.exit(app.exec_())