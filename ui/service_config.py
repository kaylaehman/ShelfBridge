"""Per-service credential / settings panels for the config dialog.

Each panel exposes ``load()`` and ``save()``. Secret fields are read from and
written to the OS credential store via ``auth.credential_store`` — never the
plain prefs file. Test/Authorize buttons call the adapter directly.
"""
import os

from calibre_plugins.shelf_bridge.ui.qt import (
    Qt, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QGroupBox, QLineEdit_Password,
)
from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge.auth import credential_store


class _BasePanel(QWidget):
    service_id = ""
    title = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.form = QFormLayout(self)
        self.build()
        self.load()

    def build(self):
        raise NotImplementedError

    def load(self):
        pass

    def save(self):
        pass

    # helpers ----------------------------------------------------------------
    def _password_field(self):
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit_Password)
        return edit

    def _test_button(self):
        btn = QPushButton("Test Connection")
        btn.clicked.connect(self._run_test)
        return btn

    def _run_test(self):
        from calibre_plugins.shelf_bridge.adapters import get_adapter
        self.save()  # persist current values first
        adapter = get_adapter(self.service_id, prefs)
        ok, msg = adapter.test_connection()
        box = QMessageBox.information if ok else QMessageBox.warning
        box(self, f"{self.title} — Test Connection", msg)


class GoodreadsPanel(_BasePanel):
    service_id = "goodreads"
    title = "Goodreads / StoryGraph"

    def build(self):
        self.path = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        holder = QWidget()
        holder.setLayout(row)
        self.form.addRow("Goodreads CSV output path:", holder)
        self.sg_path = QLineEdit()
        self.form.addRow("StoryGraph CSV output path:", self.sg_path)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Choose CSV output", "catalog.csv", "CSV (*.csv)")
        if path:
            self.path.setText(path)

    def load(self):
        self.path.setText(prefs.get("goodreads_output_path", ""))
        self.sg_path.setText(prefs.get("storygraph_output_path", ""))

    def save(self):
        prefs["goodreads_output_path"] = self.path.text().strip()
        prefs["storygraph_output_path"] = self.sg_path.text().strip()


class HardcoverPanel(_BasePanel):
    service_id = "hardcover"
    title = "Hardcover"

    def build(self):
        self.token = self._password_field()
        self.form.addRow("API token:", self.token)
        self.form.addRow("", self._test_button())

    def load(self):
        self.token.setText(credential_store.get_secret("hardcover_token", prefs) or "")

    def save(self):
        credential_store.set_secret("hardcover_token", self.token.text().strip(), prefs)


class OneDrivePanel(_BasePanel):
    service_id = "onedrive"
    title = "OneDrive"

    def build(self):
        self.client_id = QLineEdit()
        self.path = QLineEdit()
        self.form.addRow("Client ID:", self.client_id)
        self.form.addRow("OneDrive path (.csv):", self.path)
        self.status = QLabel()
        self.form.addRow("Status:", self.status)
        row = QHBoxLayout()
        self.auth_btn = QPushButton("Authorize")
        self.auth_btn.clicked.connect(self._authorize)
        row.addWidget(self.auth_btn)
        revoke = QPushButton("Revoke")
        revoke.clicked.connect(self._revoke)
        row.addWidget(revoke)
        row.addWidget(self._test_button())
        holder = QWidget()
        holder.setLayout(row)
        self.form.addRow("", holder)

    def load(self):
        self.client_id.setText(prefs.get("onedrive_client_id", ""))
        self.path.setText(prefs.get("onedrive_path", "/Calibre/catalog.csv"))
        self._refresh_status()

    def save(self):
        prefs["onedrive_client_id"] = self.client_id.text().strip()
        prefs["onedrive_path"] = self.path.text().strip() or "/Calibre/catalog.csv"

    def _refresh_status(self):
        authorized = bool(credential_store.get_secret("onedrive_token", prefs))
        self.status.setText("Authorized" if authorized else "Not authorized")
        self.auth_btn.setText("Re-Authorize" if authorized else "Authorize")

    def _authorize(self):
        self.save()
        from calibre_plugins.shelf_bridge.ui.device_auth import run_device_auth
        ok, msg = run_device_auth(self, self.client_id.text().strip())
        (QMessageBox.information if ok else QMessageBox.warning)(self, "OneDrive Authorization", msg)
        self._refresh_status()

    def _revoke(self):
        credential_store.delete_secret("onedrive_token", prefs)
        self._refresh_status()


ALL_PANELS = [GoodreadsPanel, HardcoverPanel, OneDrivePanel]
