"""Preferences dialog — a QTabWidget with one tab per service plus Automation,
Field Mapping, and Agent settings. On accept, every panel writes to prefs /
credential store.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QDialogButtonBox, QLineEdit_Password,
)
from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge.auth import credential_store
from calibre_plugins.shelf_bridge.ui.service_config import ALL_PANELS
from calibre_plugins.shelf_bridge.ui.automation_config import AutomationPanel
from calibre_plugins.shelf_bridge.ui.field_mapping import FieldMappingPanel


class _AgentPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.enabled = QCheckBox("Enable the Smart Export agent")
        form.addRow(self.enabled)
        self.backend = QComboBox()
        self.backend.addItems(["anthropic", "ollama"])
        form.addRow("Backend:", self.backend)
        self.model = QLineEdit()
        form.addRow("Model:", self.model)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit_Password)
        self.api_key.setPlaceholderText("Blank = use ANTHROPIC_API_KEY env var (stored in OS keychain)")
        form.addRow("API key:", self.api_key)
        self.max_iter = QSpinBox()
        self.max_iter.setRange(1, 50)
        form.addRow("Max iterations:", self.max_iter)
        self.load()

    def load(self):
        self.enabled.setChecked(prefs.get("agent_enabled", False))
        self.backend.setCurrentText(prefs.get("agent_backend", "anthropic"))
        self.model.setText(prefs.get("agent_model", "claude-sonnet-4-6"))
        self.api_key.setText(credential_store.get_secret("agent_api_key", prefs) or "")
        self.max_iter.setValue(prefs.get("agent_max_iterations", 10))

    def save(self):
        prefs["agent_enabled"] = self.enabled.isChecked()
        prefs["agent_backend"] = self.backend.currentText()
        prefs["agent_model"] = self.model.text().strip()
        credential_store.set_secret("agent_api_key", self.api_key.text().strip(), prefs)
        prefs["agent_max_iterations"] = self.max_iter.value()


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

        self.agent = _AgentPanel()
        self.tabs.addTab(self.agent, "Agent")
        self._panels.append(self.agent)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        for panel in self._panels:
            if hasattr(panel, "save"):
                panel.save()
        self.accept()
