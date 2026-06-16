"""OneDrive device-code authorization dialog.

Runs ``poll_for_token`` on a background QThread (never the GUI thread) with a
cooperative stop event so closing the dialog cancels cleanly. On success the
token is persisted to the OS credential store.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    Qt, QDialog, QVBoxLayout, QLabel, QPushButton, QThread, pyqtSignal,
)
from calibre_plugins.shelf_bridge.auth import graph_token
from calibre_plugins.shelf_bridge.auth.graph_token import AuthExpiredError
from calibre_plugins.shelf_bridge.prefs import prefs

import threading


class _PollThread(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, client_id, device_code, interval, stop_event, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.device_code = device_code
        self.interval = interval
        self.stop_event = stop_event

    def run(self):
        try:
            token = graph_token.poll_for_token(
                self.client_id, self.device_code,
                interval=self.interval, stop_event=self.stop_event,
            )
            graph_token.save_token(token, prefs)
            self.done.emit(True, "OneDrive authorized successfully.")
        except AuthExpiredError as e:
            self.done.emit(False, str(e))
        except Exception as e:  # pragma: no cover
            self.done.emit(False, f"Authorization error: {e}")


class DeviceAuthDialog(QDialog):
    def __init__(self, parent, client_id):
        super().__init__(parent)
        self.setWindowTitle("Authorize OneDrive")
        self.client_id = client_id
        self.result_ok = False
        self.result_msg = "Authorization cancelled."
        self.stop_event = threading.Event()
        self._thread = None

        layout = QVBoxLayout(self)
        self.info = QLabel("Requesting device code…")
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

        self._start()

    def _start(self):
        try:
            flow = graph_token.start_device_flow(self.client_id)
        except Exception as e:
            self.info.setText(f"Could not start device flow: {e}")
            return
        self.info.setText(
            f"1. Go to: {flow.get('verification_uri', 'https://microsoft.com/devicelogin')}\n"
            f"2. Enter code: {flow.get('user_code', '?')}\n\n"
            "Waiting for you to complete sign-in…"
        )
        self._thread = _PollThread(
            self.client_id, flow["device_code"], flow.get("interval", 5), self.stop_event, self)
        self._thread.done.connect(self._on_done)
        self._thread.start()

    def _on_done(self, ok, msg):
        self.result_ok = ok
        self.result_msg = msg
        self.accept() if ok else self.reject()

    def reject(self):
        self.stop_event.set()
        if self._thread is not None:
            self._thread.wait(2000)
        super().reject()


def run_device_auth(parent, client_id):
    """Show the dialog; return (ok, message)."""
    if not client_id:
        return False, "Enter a Client ID first."
    dlg = DeviceAuthDialog(parent, client_id)
    dlg.exec_() if hasattr(dlg, "exec_") else dlg.exec()
    return dlg.result_ok, dlg.result_msg
