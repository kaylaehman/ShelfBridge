"""Device-code authorization dialog (provider-agnostic).

Runs the provider's ``poll`` on a background QThread (never the GUI thread) with
a cooperative stop event so closing the dialog cancels cleanly. On success the
token is persisted to the OS credential store. Used by both OneDrive (Microsoft)
and Google Sheets (Google), which differ only in endpoints and whether a client
secret is needed.
"""
import threading

from calibre_plugins.shelf_bridge.ui.qt import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QThread, pyqtSignal,
    Qt_TextSelectableByMouse,
)
from calibre_plugins.shelf_bridge.prefs import prefs


class _Provider:
    """Bundles the per-service flow callables for the dialog."""
    def __init__(self, name, start, poll, save, verify_key, verify_default):
        self.name = name
        self.start = start                # () -> flow dict
        self.poll = poll                  # (device_code, interval, stop_event) -> token
        self.save = save                  # (token, prefs) -> None
        self.verify_key = verify_key      # flow key holding the verification URL
        self.verify_default = verify_default


class _PollThread(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, provider, device_code, interval, stop_event, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.device_code = device_code
        self.interval = interval
        self.stop_event = stop_event

    def run(self):
        from calibre_plugins.shelf_bridge.auth.graph_token import AuthExpiredError as MSExpired
        from calibre_plugins.shelf_bridge.auth.google_token import AuthExpiredError as GExpired
        try:
            token = self.provider.poll(self.device_code, self.interval, self.stop_event)
            self.provider.save(token, prefs)
            self.done.emit(True, f"{self.provider.name} authorized successfully.")
        except (MSExpired, GExpired) as e:
            self.done.emit(False, str(e))
        except Exception as e:  # pragma: no cover
            self.done.emit(False, f"Authorization error: {e}")


class DeviceAuthDialog(QDialog):
    def __init__(self, parent, provider):
        super().__init__(parent)
        self.provider = provider
        self.setWindowTitle(f"Authorize {provider.name}")
        self.result_ok = False
        self.result_msg = "Authorization cancelled."
        self.stop_event = threading.Event()
        self._thread = None

        layout = QVBoxLayout(self)
        self.info = QLabel("Requesting device code…")
        self.info.setTextInteractionFlags(Qt_TextSelectableByMouse)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

        self._start()

    def _start(self):
        try:
            flow = self.provider.start()
        except Exception as e:
            self.info.setText(f"Could not start device flow: {e}")
            return
        self.info.setText(
            f"1. Go to: {flow.get(self.provider.verify_key, self.provider.verify_default)}\n"
            f"2. Enter code: {flow.get('user_code', '?')}\n\n"
            "Waiting for you to complete sign-in…"
        )
        self._thread = _PollThread(
            self.provider, flow["device_code"], flow.get("interval", 5), self.stop_event, self)
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


def _run(parent, provider):
    dlg = DeviceAuthDialog(parent, provider)
    dlg.exec_() if hasattr(dlg, "exec_") else dlg.exec()
    return dlg.result_ok, dlg.result_msg


def run_device_auth(parent, client_id):
    """OneDrive (Microsoft) device-code authorization."""
    if not client_id:
        return False, "Enter a Client ID first."
    from calibre_plugins.shelf_bridge.auth import graph_token
    provider = _Provider(
        name="OneDrive",
        start=lambda: graph_token.start_device_flow(client_id),
        poll=lambda dc, interval, stop: graph_token.poll_for_token(
            client_id, dc, interval=interval, stop_event=stop),
        save=graph_token.save_token,
        verify_key="verification_uri",
        verify_default="https://microsoft.com/devicelogin",
    )
    return _run(parent, provider)


def run_google_device_auth(parent, client_id, client_secret):
    """Google Sheets device-code authorization."""
    if not client_id or not client_secret:
        return False, "Enter a Client ID and Client Secret first."
    from calibre_plugins.shelf_bridge.auth import google_token
    provider = _Provider(
        name="Google Sheets",
        start=lambda: google_token.start_device_flow(client_id),
        poll=lambda dc, interval, stop: google_token.poll_for_token(
            client_id, client_secret, dc, interval=interval, stop_event=stop),
        save=google_token.save_token,
        verify_key="verification_url",
        verify_default="https://www.google.com/device",
    )
    return _run(parent, provider)
