"""Export progress dialog.

Runs the headless export on a worker QThread so the GUI never freezes (review
arch C2). Re-extracts books at run time rather than trusting a stale snapshot
(review I9).
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QPlainTextEdit, QThread, pyqtSignal,
)
from calibre_plugins.shelf_bridge.prefs import prefs


class ExportWorker(QThread):
    finished_summary = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, gui, services, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.services = services

    def run(self):
        try:
            from calibre_plugins.shelf_bridge.automation.export_runner import run_export_headless
            db = self.gui.current_db.new_api
            summary = run_export_headless(db, reason="manual", services_override=self.services)
            self.finished_summary.emit(summary)
        except Exception as e:  # pragma: no cover
            self.failed.emit(str(e))


class ExportDialog(QDialog):
    def __init__(self, gui, books=None, parent=None):
        super().__init__(parent or gui)
        self.gui = gui
        self.setWindowTitle("ShelfBridge — Export")
        layout = QVBoxLayout(self)

        services = prefs.get("enabled_services", []) or [prefs.get("default_service", "goodreads")]
        self.services = services
        layout.addWidget(QLabel("Services: " + ", ".join(services)))

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.run_btn = QPushButton("Run Export")
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self._worker = None

    def _run(self):
        self.run_btn.setEnabled(False)
        self.log.appendPlainText("Exporting…")
        self._worker = ExportWorker(self.gui, self.services, self)
        self._worker.finished_summary.connect(self._on_summary)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_summary(self, summary):
        self.log.appendPlainText(f"Total books: {summary.get('total_books', 0)}")
        for svc, res in summary.get("results", {}).items():
            if res.get("skipped"):
                self.log.appendPlainText(f"  {svc}: skipped — {res.get('reason')}")
            elif res.get("success"):
                self.log.appendPlainText(
                    f"  {svc}: {res.get('records_exported', 0)} -> {res.get('destination')}")
            else:
                self.log.appendPlainText(f"  {svc}: FAILED — {res.get('errors')}")
        self.run_btn.setEnabled(True)

    def _on_failed(self, msg):
        self.log.appendPlainText(f"Export error: {msg}")
        self.run_btn.setEnabled(True)
