#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShellTuga - Main entry point
Turtle-powered forensic browser for The Sleuth Kit
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ShellTuga")
    app.setOrganizationName("Falconmx1")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())
