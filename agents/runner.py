"""Ruflo agent runtime host (QThread wrapper).

Hosts the agent loop off the GUI thread. The Anthropic/Ollama API key is read
from the OS credential store (or the ANTHROPIC_API_KEY env var), never from the
plain prefs file.
"""
import pathlib

from ruflo import RufloAgent, RufloConfig
from calibre_plugins.shelf_bridge.agents import tools  # registers @ruflo_tool decorators  # noqa: F401
from calibre_plugins.shelf_bridge.auth import credential_store
from calibre_plugins.shelf_bridge.prefs import prefs

try:
    from PyQt5.Qt import QThread, pyqtSignal
except ImportError:  # pragma: no cover - PyQt6 path
    from PyQt6.QtCore import QThread, pyqtSignal

PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


def _load_prompt(name):
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


class AgentRunner(QThread):
    finished = pyqtSignal(dict)   # final result dict
    progress = pyqtSignal(str)    # step-by-step log lines

    def __init__(self, task_name, task_input, db, parent=None):
        super().__init__(parent)
        self.task_name = task_name
        self.task_input = task_input
        self.db = db

    def run(self):
        config = RufloConfig(
            backend=prefs.get("agent_backend", "anthropic"),
            model=prefs.get("agent_model", "claude-sonnet-4-6"),
            api_key=credential_store.get_secret("agent_api_key", prefs),  # blank -> env
            max_iterations=prefs.get("agent_max_iterations", 10),
            tool_context={"db": self.db},   # injected as first arg of each tool
        )

        system_prompt = _load_prompt("system")
        task_prompt = _load_prompt(self.task_name)

        agent = RufloAgent(
            config=config,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            namespace="shelf_bridge",
        )
        agent.on_step(lambda step: self.progress.emit(step.summary))

        result = agent.run(self.task_input)
        self.finished.emit(result.to_dict())
