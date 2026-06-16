"""PyQt5 / PyQt6 compatibility shim.

Calibre 6.x ships PyQt5, 7.x ships PyQt6 (which splits classes across QtWidgets /
QtCore / QtGui). Importing from here gives the UI modules one stable surface and
avoids repeating the try/except in every file.
"""
try:  # PyQt5 (Calibre 6.x) — everything lives under PyQt5.Qt
    from PyQt5.Qt import (  # noqa: F401
        Qt, QApplication, QDialog, QWidget, QTabWidget,
        QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
        QLabel, QPushButton, QLineEdit, QCheckBox, QSpinBox, QComboBox,
        QListWidget, QListWidgetItem, QTextEdit, QPlainTextEdit,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QDialogButtonBox, QGroupBox, QThread, pyqtSignal,
    )
    QLineEdit_Password = QLineEdit.Password
except ImportError:  # PyQt6 (Calibre 7.x)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal  # noqa: F401
    from PyQt6.QtWidgets import (  # noqa: F401
        QApplication, QDialog, QWidget, QTabWidget,
        QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
        QLabel, QPushButton, QLineEdit, QCheckBox, QSpinBox, QComboBox,
        QListWidget, QListWidgetItem, QTextEdit, QPlainTextEdit,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QDialogButtonBox, QGroupBox,
    )
    QLineEdit_Password = QLineEdit.EchoMode.Password
