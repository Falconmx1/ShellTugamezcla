# gui/main_window.py
import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFileDialog, QLabel, QSplitter, QMessageBox, QProgressDialog,
    QTabWidget, QDialog, QLineEdit, QCheckBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QTextCursor

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

class RecoverFileThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, image_path, offset, inode, output_path):
        super().__init__()
        self.image_path = image_path
        self.offset = offset
        self.inode = inode
        self.output_path = output_path
        
    def run(self):
        tsk = TSKWrapper()
        success, msg = tsk.recover_file(self.image_path, self.offset, self.inode, self.output_path)
        self.finished.emit(success, msg)

class HexViewDialog(QDialog):
    def __init__(self, hex_data, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Hex View - {file_name}")
        self.setGeometry(200, 200, 900, 600)
        
        layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier", 10))
        self.text_edit.setPlainText(hex_data)
        layout.addWidget(self.text_edit)
        
        # Copy button
        btn_copy = QPushButton("📋 Copy to Clipboard")
        btn_copy.clicked.connect(self.copy_hex)
        layout.addWidget(btn_copy)
        
        self.setLayout(layout)
    
    def copy_hex(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "Copied", "Hex data copied to clipboard")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tsk = TSKWrapper()
        self.current_image = None
        self.current_offset = 0
        self.current_inode_map = {}  # Map tree items to inodes
        self.init_ui()
        self.load_banner()
        
    def init_ui(self):
        self.setWindowTitle("ShellTuga - Forensic Browser 🐢")
        self.setGeometry(100, 100, 1400, 900)
        
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
        
        self.btn_deleted = QPushButton("🗑️ Show Only Deleted")
        self.btn_deleted.clicked.connect(self.show_deleted_files)
        self.btn_deleted.setEnabled(False)
        self.btn_deleted.setStyleSheet("background-color: #ff9800;")
        
        self.btn_search = QPushButton("🔍 Hex Search")
        self.btn_search.clicked.connect(self.show_hex_search)
        self.btn_search.setEnabled(False)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_deleted)
        btn_layout.addWidget(self.btn_search)
        btn_layout.addStretch()
        
        # Info label
        self.info_label = QLabel("Ready. Load a forensic image to start.")
        self.info_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.info_label)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # File browser tab
        self.browser_tab = QWidget()
        browser_layout = QVBoxLayout(self.browser_tab)
        
        # Splitter for tree and details
        splitter = QSplitter(Qt.Horizontal)
        
        # File tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Filesystem Browser")
        self.tree.itemClicked.connect(self.on_item_clicked)
        splitter.addWidget(self.tree)
        
        # Details panel
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setFont(QFont("Courier", 10))
        splitter.addWidget(self.details)
        
        splitter.setSizes([600, 600])
        browser_layout.addWidget(splitter)
        
        # Recovered files tab
        self.recovery_tab = QWidget()
        recovery_layout = QVBoxLayout(self.recovery_tab)
        
        self.recovery_list = QTreeWidget()
        self.recovery_list.setHeaderLabel("Deleted Files Ready for Recovery")
        self.recovery_list.itemClicked.connect(self.on_recovery_item_clicked)
        recovery_layout.addWidget(self.recovery_list)
        
        self.btn_recover = QPushButton("💾 Recover Selected File")
        self.btn_recover.clicked.connect(self.recover_selected_file)
        self.btn_recover.setEnabled(False)
        self.btn_recover.setStyleSheet("background-color: #2196F3; font-weight: bold;")
        recovery_layout.addWidget(self.btn_recover)
        
        self.tab_widget.addTab(self.browser_tab, "📂 File Browser")
        self.tab_widget.addTab(self.recovery_tab, "🗑️ Deleted Files")
        
        main_layout.addWidget(self.tab_widget)
        
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
            "Disk Images (*.dd *.raw *.img *.e01 *.001);;All Files (*.*)"
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
        self.btn_deleted.setEnabled(True)
        self.btn_search.setEnabled(True)
        self.populate_tree()
        self.load_deleted_files()
        QMessageBox.information(self, "Success", "Image loaded successfully!")
        
    def on_load_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"Failed to load image:\n{error_msg}")
        
    def refresh_view(self):
        if self.current_image:
            self.populate_tree()
            self.load_deleted_files()
            
    def populate_tree(self):
        self.tree.clear()
        self.current_inode_map = {}
        
        if not self.current_image:
            return
            
        # Root item
        root = QTreeWidgetItem(self.tree)
        root.setText(0, f"💾 {os.path.basename(self.current_image['image_path'])}")
        
        # Partitions
        parts = self.current_image.get('partitions', [])
        if not parts:
            item = QTreeWidgetItem(root)
            item.setText(0, "⚠️ No partitions found (raw image mode)")
            item.setForeground(0, QColor(255, 165, 0))
            # Still allow browsing raw image
            self.load_partition_contents(root, 0)
        else:
            for part in parts:
                part_item = QTreeWidgetItem(root)
                part_item.setText(0, f"📀 Partition {part['index']} - {part['type']} (Offset: {part['offset']} bytes)")
                part_item.setData(0, Qt.UserRole, {'type': 'partition', 'offset': part['offset'], 'index': part['index']})
                # Load contents on demand
                self.load_partition_contents(part_item, part['offset'])
                
        self.tree.expandToDepth(1)
        
    def load_partition_contents(self, parent_item, offset):
        """Load files from a partition recursively"""
        try:
            files = self.tsk.list_directory(self.current_image['image_path'], offset)
            if isinstance(files, dict) and 'error' in files:
                error_item = QTreeWidgetItem(parent_item)
                error_item.setText(0, f"❌ Error: {files['error']}")
                error_item.setForeground(0, QColor(255, 0, 0))
                return
                
            for file_info in files:
                file_item = QTreeWidgetItem(parent_item)
                name = file_info['name'] if file_info['name'] else f"[Unnamed inode {file_info['inode']}]"
                
                # Mark deleted files
                if file_info['deleted']:
                    file_item.setText(0, f"🗑️ {name} (DELETED)")
                    file_item.setForeground(0, QColor(255, 0, 0))
                else:
                    file_item.setText(0, f"{file_info['type']} {name}")
                    
                file_item.setData(0, Qt.UserRole, {
                    'type': 'file',
                    'inode': file_info['inode'],
                    'offset': offset,
                    'deleted': file_info['deleted']
                })
                self.current_inode_map[file_info['inode']] = file_item
                
        except Exception as e:
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Error loading: {str(e)}")
            
    def load_deleted_files(self):
        """Load only deleted files into recovery tab"""
        self.recovery_list.clear()
        
        if not self.current_image:
            return
            
        parts = self.current_image.get('partitions', [])
        if not parts:
            parts = [{'offset': 0, 'index': 0, 'type': 'Raw'}]
            
        for part in parts:
            try:
                offset = part['offset']
                files = self.tsk.get_deleted_files(self.current_image['image_path'], offset)
                
                if isinstance(files, dict) and 'error' in files:
                    continue
                    
                for file_info in files:
                    if file_info['deleted']:
                        item = QTreeWidgetItem(self.recovery_list)
                        name = file_info['name'] if file_info['name'] else f"deleted_inode_{file_info['inode']}"
                        item.setText(0, f"🗑️ {name}")
                        item.setData(0, Qt.UserRole, {
                            'inode': file_info['inode'],
                            'offset': offset,
                            'name': name,
                            'partition': part['index']
                        })
                        item.setForeground(0, QColor(255, 0, 0))
            except Exception as e:
                print(f"Error loading deleted from partition {part['index']}: {e}")
                
    def on_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        if data.get('type') == 'partition':
            offset = data['offset']
            self.details.clear()
            self.details.append("=== Partition Details ===")
            self.details.append(f"Offset: {offset} bytes ({offset // 512} sectors)")
            self.details.append("\n📂 Double-click on files to view metadata")
            self.details.append("🔍 Right-click for hex view or recovery")
            
        elif data.get('type') == 'file':
            inode = data['inode']
            offset = data['offset']
            deleted = data.get('deleted', False)
            
            # Get metadata
            metadata = self.tsk.get_file_metadata(
                self.current_image['image_path'], 
                offset, 
                inode
            )
            
            self.details.clear()
            if deleted:
                self.details.append("⚠️ DELETED FILE ⚠️\n")
            self.details.append(metadata)
            self.details.append("\n" + "="*50)
            self.details.append("Actions available:")
            self.details.append("• Right-click on file → View Hex")
            self.details.append("• Right-click on file → Recover")
            
            # Store current selection for context menu
            self.current_selected_item = item
            
    def on_recovery_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data:
            self.current_recovery_data = data
            self.btn_recover.setEnabled(True)
            
    def recover_selected_file(self):
        if not hasattr(self, 'current_recovery_data'):
            QMessageBox.warning(self, "Warning", "No file selected")
            return
            
        data = self.current_recovery_data
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Recovered File", 
            f"recovered_{data['name']}", 
            "All Files (*.*)"
        )
        
        if not save_path:
            return
            
        progress = QProgressDialog("Recovering file...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        
        self.recover_thread = RecoverFileThread(
            self.current_image['image_path'],
            data['offset'],
            data['inode'],
            save_path
        )
        self.recover_thread.finished.connect(lambda s, m: self.on_recovery_finished(s, m, progress))
        self.recover_thread.start()
        
    def on_recovery_finished(self, success, message, progress_dialog):
        progress_dialog.close()
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Recovery Failed", message)
            
    def show_deleted_files(self):
        """Switch to deleted files tab and refresh"""
        self.tab_widget.setCurrentIndex(1)
        self.load_deleted_files()
        
    def show_hex_search(self):
        """Show hex search dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Hex Search")
        dialog.setGeometry(400, 400, 500, 200)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Enter hex pattern (e.g., 'FF D8 FF' for JPEG header):"))
        self.hex_input = QLineEdit()
        layout.addWidget(self.hex_input)
        
        btn_search = QPushButton("🔍 Search")
        btn_search.clicked.connect(lambda: self.perform_hex_search(dialog))
        layout.addWidget(btn_search)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def perform_hex_search(self, dialog):
        pattern = self.hex_input.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Warning", "Enter a hex pattern")
            return
            
        # Search in first partition for simplicity
        if not self.current_image['partitions']:
            offset = 0
        else:
            offset = self.current_image['partitions'][0]['offset']
            
        results = self.tsk.search_hex_pattern(
            self.current_image['image_path'],
            offset,
            pattern
        )
        
        dialog.close()
        
        # Show results
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("Hex Search Results")
        result_dialog.setGeometry(300, 300, 800, 500)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setFont(QFont("Courier", 10))
        text_edit.setPlainText(results)
        layout.addWidget(text_edit)
        
        result_dialog.setLayout(layout)
        result_dialog.exec_()
        
    def contextMenuEvent(self, event):
        """Right-click context menu for hex view"""
        if hasattr(self, 'current_selected_item'):
            data = self.current_selected_item.data(0, Qt.UserRole)
            if data and data.get('type') == 'file':
                menu = self.menuBar().createContextMenu(self)
                
                hex_action = menu.addAction("🔍 View Hex")
                hex_action.triggered.connect(self.view_hex)
                
                recover_action = menu.addAction("💾 Recover File")
                recover_action.triggered.connect(self.recover_current_file)
                
                menu.exec_(event.globalPos())
                
    def view_hex(self):
        data = self.current_selected_item.data(0, Qt.UserRole)
        if data and data.get('type') == 'file':
            hex_data = self.tsk.get_hex_view(
                self.current_image['image_path'],
                data['offset'],
                data['inode']
            )
            
            dialog = HexViewDialog(hex_data, data.get('name', 'file'), self)
            dialog.exec_()
            
    def recover_current_file(self):
        data = self.current_selected_item.data(0, Qt.UserRole)
        if data and data.get('type') == 'file':
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Recovered File", 
                f"recovered_{data.get('name', 'file')}", 
                "All Files (*.*)"
            )
            
            if save_path:
                progress = QProgressDialog("Recovering...", "Cancel", 0, 0, self)
                self.recover_thread = RecoverFileThread(
                    self.current_image['image_path'],
                    data['offset'],
                    data['inode'],
                    save_path
                )
                self.recover_thread.finished.connect(lambda s, m: self.on_recovery_finished(s, m, progress))
                self.recover_thread.start()
