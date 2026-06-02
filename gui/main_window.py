# gui/main_window.py
import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFileDialog, QLabel, QSplitter, QMessageBox, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon

from core.tsk_wrapper import TSKWrapper

class LoadImageThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        
    def run(self):
        try:
            self.progress.emit("Loading image...")
            tsk = TSKWrapper()
            result = tsk.load_image(self.image_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tsk = TSKWrapper()
        self.current_image = None
        self.init_ui()
        self.load_banner()
        
    def init_ui(self):
        self.setWindowTitle("ShellTuga - Forensic Browser 🐢")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Top banner (ASCII turtle)
        self.banner_label = QLabel()
        self.banner_label.setFont(QFont("Courier", 10))
        self.banner_label.setAlignment(Qt.AlignCenter)
        self.banner_label.setStyleSheet("background-color: #2d2d2d; color: #00ff00; padding: 5px;")
        main_layout.addWidget(self.banner_label)
        
        # Buttons bar
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("🐢 Load Disk Image")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_load.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_view)
        self.btn_refresh.setEnabled(False)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        
        # Info label
        self.info_label = QLabel("Ready. Load a forensic image to start.")
        self.info_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.info_label)
        
        # Splitter for tree and details
        splitter = QSplitter(Qt.Horizontal)
        
        # File tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Filesystem Browser")
        self.tree.itemClicked.connect(self.on_item_clicked)
        splitter.addWidget(self.tree)
        
        # Details panel (tabs would be better, but keeping simple)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setFont(QFont("Courier", 10))
        splitter.addWidget(self.details)
        
        splitter.setSizes([600, 600])
        main_layout.addWidget(splitter)
        
    def load_banner(self):
        banner_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "tortuga_banner.txt")
        try:
            with open(banner_path, "r") as f:
                banner = f.read()
        except:
            banner = """
    ───▄▀▀▀▄───────────────
    ───█───█───────────────
    ──▐▌───▐▌──────────────
    ──█────█───────────────
    ShellTuga — 🐢 slow but deep
            """
        self.banner_label.setText(banner)
        
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Disk Image", "", 
            "Disk Images (*.dd *.raw *.img *.e01);;All Files (*.*)"
        )
        if not file_path:
            return
            
        # Show progress
        progress = QProgressDialog("Loading image...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        
        self.thread = LoadImageThread(file_path)
        self.thread.finished.connect(self.on_image_loaded)
        self.thread.error.connect(self.on_load_error)
        self.thread.progress.connect(progress.setLabelText)
        self.thread.finished.connect(progress.close)
        self.thread.finished.connect(self.thread.deleteLater)
        progress.canceled.connect(self.thread.quit)
        self.thread.start()
        
    def on_image_loaded(self, result):
        self.current_image = result
        self.info_label.setText(f"Loaded: {result.get('image_path', 'Unknown')} - {result.get('partition_table', 'N/A')}")
        self.btn_refresh.setEnabled(True)
        self.populate_tree()
        QMessageBox.information(self, "Success", "Image loaded successfully!")
        
    def on_load_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"Failed to load image:\n{error_msg}")
        
    def refresh_view(self):
        if self.current_image:
            self.populate_tree()
            
    def populate_tree(self):
        self.tree.clear()
        if not self.current_image:
            return
            
        # Root item
        root = QTreeWidgetItem(self.tree)
        root.setText(0, f"💾 {os.path.basename(self.current_image['image_path'])}")
        
        # Partitions
        parts = self.current_image.get('partitions', [])
        if not parts:
            item = QTreeWidgetItem(root)
            item.setText(0, "No partitions found or raw image")
            item.setForeground(0, QColor(255, 165, 0))
        else:
            for part in parts:
                part_item = QTreeWidgetItem(root)
                part_item.setText(0, f"📀 Partition {part['index']} - {part['type']} (Offset: {part['offset']})")
                part_item.setData(0, Qt.UserRole, {'type': 'partition', 'offset': part['offset']})
                
        self.tree.expandAll()
        
    def on_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get('type') == 'partition':
            offset = data['offset']
            self.details.clear()
            self.details.append("=== Partition Details ===")
            self.details.append(f"Offset: {offset} bytes")
            self.details.append("\nUse 'Analyze' feature to list files (coming soon...)")
            # Here you would call fls with offset
