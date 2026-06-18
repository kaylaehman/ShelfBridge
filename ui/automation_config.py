"""Automation tab widget — triggers, schedule, included services, Run Now."""
from calibre_plugins.shelf_bridge.ui.qt import (
    QWidget, QVBoxLayout, QFormLayout, QCheckBox, QSpinBox, QComboBox,
    QListWidget, QListWidgetItem, QPushButton,
    Qt_UserRole, Qt_ItemIsUserCheckable, Qt_Checked, Qt_Unchecked,
)
from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge.adapters import list_adapters

_INTERVALS = [("Every 15 minutes", 15), ("Every 30 minutes", 30),
              ("Every hour", 60), ("Every 6 hours", 360), ("Daily", 1440)]


class AutomationPanel(QWidget):
    def __init__(self, gui=None, parent=None):
        super().__init__(parent)
        self.gui = gui
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.on_change = QCheckBox("Export when the library changes")
        form.addRow(self.on_change)

        self.debounce = QSpinBox()
        self.debounce.setRange(30, 3600)
        form.addRow("Debounce (seconds):", self.debounce)

        self.on_schedule = QCheckBox("Export on a schedule")
        form.addRow(self.on_schedule)

        self.interval = QComboBox()
        for label, _ in _INTERVALS:
            self.interval.addItem(label)
        form.addRow("Interval:", self.interval)

        self.notify = QCheckBox("Show a notification after auto-export")
        form.addRow(self.notify)

        self.services = QListWidget()
        for cls in list_adapters():
            item = QListWidgetItem(cls.display_name)
            item.setData(Qt_UserRole, cls.service_id)
            item.setFlags(item.flags() | Qt_ItemIsUserCheckable)
            item.setCheckState(Qt_Unchecked)
            self.services.addItem(item)
        form.addRow("Services to include:", self.services)

        self.run_now = QPushButton("Run Now")
        self.run_now.clicked.connect(self._run_now)
        layout.addWidget(self.run_now)

        self.load()

    def load(self):
        self.on_change.setChecked(prefs.get("auto_export_on_change", False))
        self.debounce.setValue(prefs.get("auto_export_debounce_secs", 60))
        self.on_schedule.setChecked(prefs.get("schedule_enabled", False))
        current = prefs.get("schedule_interval_minutes", 60)
        for idx, (_, mins) in enumerate(_INTERVALS):
            if mins == current:
                self.interval.setCurrentIndex(idx)
                break
        self.notify.setChecked(prefs.get("notify_on_auto_export", True))
        enabled = set(prefs.get("enabled_services", []))
        for i in range(self.services.count()):
            item = self.services.item(i)
            checked = item.data(Qt_UserRole) in enabled
            item.setCheckState(Qt_Checked if checked else Qt_Unchecked)

    def save(self):
        prefs["auto_export_on_change"] = self.on_change.isChecked()
        prefs["auto_export_debounce_secs"] = self.debounce.value()
        prefs["schedule_enabled"] = self.on_schedule.isChecked()
        prefs["schedule_interval_minutes"] = _INTERVALS[self.interval.currentIndex()][1]
        prefs["notify_on_auto_export"] = self.notify.isChecked()
        chosen = []
        for i in range(self.services.count()):
            item = self.services.item(i)
            if item.checkState() == Qt_Checked:
                chosen.append(item.data(Qt_UserRole))
        prefs["enabled_services"] = chosen

    def _run_now(self):
        self.save()
        if self.gui is None:
            return
        from calibre_plugins.shelf_bridge.automation.export_runner import run_export_headless
        db = self.gui.current_db.new_api
        summary = run_export_headless(db, reason="run_now")
        from calibre_plugins.shelf_bridge.ui.qt import QMessageBox
        total = sum(r.get("records_exported", 0)
                    for r in summary["results"].values() if isinstance(r, dict))
        QMessageBox.information(self, "ShelfBridge", f"Run Now complete: {total} records exported.")
