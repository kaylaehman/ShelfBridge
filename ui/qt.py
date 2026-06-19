"""PyQt5 / PyQt6 compatibility shim.

Calibre 6.x ships PyQt5, 7.x+ ships PyQt6. Critically, Calibre exposes a
``PyQt5.Qt`` module even on PyQt6 builds, but the classes behind it are PyQt6 —
where enum members are *scoped* (``QLineEdit.EchoMode.Password``) rather than
flat (``QLineEdit.Password``). So importing the classes is not enough; every
enum member must be resolved in a way that works under both. ``_scoped`` does
that, and this module exports ready-to-use enum constants the UI imports.
"""
try:  # Calibre exposes PyQt5.Qt (classes may actually be PyQt6)
    from PyQt5.Qt import (  # noqa: F401
        Qt, QApplication, QDialog, QWidget, QTabWidget,
        QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
        QLabel, QPushButton, QLineEdit, QCheckBox, QSpinBox, QComboBox,
        QListWidget, QListWidgetItem, QTextEdit, QPlainTextEdit,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QDialogButtonBox, QGroupBox, QMenu, QThread, pyqtSignal,
    )
except ImportError:  # pure PyQt6
    from PyQt6.QtCore import Qt, QThread, pyqtSignal  # noqa: F401
    from PyQt6.QtWidgets import (  # noqa: F401
        QApplication, QDialog, QWidget, QTabWidget,
        QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
        QLabel, QPushButton, QLineEdit, QCheckBox, QSpinBox, QComboBox,
        QListWidget, QListWidgetItem, QTextEdit, QPlainTextEdit,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QDialogButtonBox, QGroupBox, QMenu,
    )


def _scoped(base, scope, name):
    """Resolve an enum member that may be scoped (PyQt6) or flat (PyQt5)."""
    holder = getattr(base, scope, None)
    if holder is not None and hasattr(holder, name):
        return getattr(holder, name)
    return getattr(base, name)


# Enum constants used by the UI — work under both PyQt5 and PyQt6.
QLineEdit_Password = _scoped(QLineEdit, "EchoMode", "Password")
Qt_UserRole = _scoped(Qt, "ItemDataRole", "UserRole")
Qt_ItemIsUserCheckable = _scoped(Qt, "ItemFlag", "ItemIsUserCheckable")
Qt_Checked = _scoped(Qt, "CheckState", "Checked")
Qt_Unchecked = _scoped(Qt, "CheckState", "Unchecked")
Qt_TextSelectableByMouse = _scoped(Qt, "TextInteractionFlag", "TextSelectableByMouse")
QDialogButtonBox_Ok = _scoped(QDialogButtonBox, "StandardButton", "Ok")
QDialogButtonBox_Cancel = _scoped(QDialogButtonBox, "StandardButton", "Cancel")
