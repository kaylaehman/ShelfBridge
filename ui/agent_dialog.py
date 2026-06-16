"""Smart Export (agent) dialog — minimal chat-style runner.

Lets the user type a task ("Export to Notion", "Why did OneDrive fail?") and runs
it through the Ruflo AgentRunner on a background thread, streaming progress.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QPlainTextEdit, QComboBox,
)
from calibre_plugins.shelf_bridge.prefs import prefs

# Map a friendly label to the prompt/task file name loaded by AgentRunner.
_TASKS = [("Export", "export"), ("Diagnose a failure", "diagnose"),
          ("Set up automation", "schedule")]


class AgentDialog(QDialog):
    def __init__(self, gui, parent=None):
        super().__init__(parent or gui)
        self.gui = gui
        self.setWindowTitle("ShelfBridge — Smart Export (Agent)")
        layout = QVBoxLayout(self)

        if not prefs.get("agent_enabled", False):
            layout.addWidget(QLabel(
                "The agent feature is disabled. Enable it in ShelfBridge settings "
                "(Agent tab) to use Smart Export."))

        self.task = QComboBox()
        for label, name in _TASKS:
            self.task.addItem(label, name)
        layout.addWidget(self.task)

        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        layout.addWidget(self.transcript)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Describe what you want (e.g. 'Export to Notion')")
        row.addWidget(self.input)
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run)
        row.addWidget(self.run_btn)
        layout.addLayout(row)

        self._runner = None

    def _run(self):
        if not prefs.get("agent_enabled", False):
            self.transcript.appendPlainText("Agent is disabled.")
            return
        from calibre_plugins.shelf_bridge.agents.runner import AgentRunner
        task_name = self.task.currentData()
        self.run_btn.setEnabled(False)
        self.transcript.appendPlainText(f"> {self.input.text()}")
        db = self.gui.current_db.new_api
        self._runner = AgentRunner(task_name, self.input.text(), db, self)
        self._runner.progress.connect(lambda s: self.transcript.appendPlainText(s))
        self._runner.finished.connect(self._on_finished)
        self._runner.start()

    def _on_finished(self, result):
        self.transcript.appendPlainText(f"Done: {result}")
        self.run_btn.setEnabled(True)
