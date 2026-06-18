"""Preferences dialog — a QTabWidget with one tab per service plus Automation
and Field Mapping. On accept, every panel writes to prefs / credential store.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox,
    QDialogButtonBox_Ok, QDialogButtonBox_Cancel,
)
from calibre_plugins.shelf_bridge.ui.service_config import ALL_PANELS
from calibre_plugins.shelf_bridge.ui.automation_config import AutomationPanel
from calibre_plugins.shelf_bridge.ui.field_mapping import FieldMappingPanel


class ConfigDialog(QDialog):
    def __init__(self, gui, action_spec=None, parent=None):
        super().__init__(parent or gui)
        self.gui = gui
        self.setWindowTitle("ShelfBridge — Configure Services")
        self.resize(560, 480)
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._panels = []
        for panel_cls in ALL_PANELS:
            panel = panel_cls()
            self.tabs.addTab(panel, panel.title)
            self._panels.append(panel)

        self.automation = AutomationPanel(gui)
        self.tabs.addTab(self.automation, "Automation")
        self._panels.append(self.automation)

        self.mapping = FieldMappingPanel()
        self.tabs.addTab(self.mapping, "Field Mapping")
        self._panels.append(self.mapping)

        buttons = QDialogButtonBox(QDialogButtonBox_Ok | QDialogButtonBox_Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        for panel in self._panels:
            if hasattr(panel, "save"):
                panel.save()
        self.accept()
