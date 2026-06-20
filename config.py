"""Config UI.

``ConfigWidget`` is the tabbed configuration body, reusable both as Calibre's
"Customize plugin" widget (Preferences → Plugins) and inside ``ConfigDialog``,
the modal opened from the toolbar's "Configure Services…" menu item.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QWidget, QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox,
    QDialogButtonBox_Ok, QDialogButtonBox_Cancel,
)
from calibre_plugins.shelf_bridge.ui.service_config import ALL_PANELS
from calibre_plugins.shelf_bridge.ui.automation_config import AutomationPanel
from calibre_plugins.shelf_bridge.ui.export_config import ExportPanel


class ConfigWidget(QWidget):
    """The tabbed configuration body. Call :meth:`save_settings` to persist."""

    def __init__(self, gui=None, parent=None):
        super().__init__(parent)
        self.gui = gui
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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

        self.export_panel = ExportPanel(gui)
        self.tabs.addTab(self.export_panel, self.export_panel.title)
        self._panels.append(self.export_panel)

    def save_settings(self):
        for panel in self._panels:
            if hasattr(panel, "save"):
                panel.save()


class ConfigDialog(QDialog):
    """Modal wrapper used by the toolbar 'Configure Services…' menu item."""

    def __init__(self, gui, action_spec=None, parent=None):
        super().__init__(parent or gui)
        self.gui = gui
        self.setWindowTitle("ShelfBridge — Configure Services")
        self.resize(560, 480)
        layout = QVBoxLayout(self)

        self.widget = ConfigWidget(gui, self)
        layout.addWidget(self.widget)

        buttons = QDialogButtonBox(QDialogButtonBox_Ok | QDialogButtonBox_Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.widget.save_settings()
        self.accept()
