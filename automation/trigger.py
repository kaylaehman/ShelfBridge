"""Automation triggers — library-change listener + scheduled QTimer.

Owns both triggers; instantiated once in ``main.genesis()`` and torn down in
``shutdown()``. It only emits ``export_requested``; the actual (threaded) export
is run by the host action so GUI work stays on the main thread.
"""
import time

try:
    from PyQt5.Qt import QTimer, QObject, pyqtSignal
except ImportError:  # pragma: no cover - PyQt6 path
    from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from calibre_plugins.shelf_bridge.prefs import prefs


class ShelfBridgeTrigger(QObject):
    export_requested = pyqtSignal(str)   # emits trigger reason string

    def __init__(self, gui, parent=None):
        super().__init__(parent)
        self.gui = gui
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_schedule_tick)
        self._last_export = 0.0
        self._connected = False
        self._legacy_connected = False   # track which attach path was used (review I2)

    # ── Library-change trigger ───────────────────────────────────────────
    def attach_library_change(self):
        if self._connected:
            return
        try:
            self.gui.current_db.new_api.library_database_instance.add_listener(
                self._on_library_change)
            self._legacy_connected = False
        except AttributeError:
            self.gui.library_changed.connect(self._on_library_change_legacy)
            self._legacy_connected = True
        self._connected = True

    def detach_library_change(self):
        if not self._connected:
            return
        try:
            if self._legacy_connected:
                self.gui.library_changed.disconnect(self._on_library_change_legacy)
            else:
                self.gui.current_db.new_api.library_database_instance.remove_listener(
                    self._on_library_change)
        except Exception:
            pass
        self._connected = False
        self._legacy_connected = False

    def _on_library_change(self, *args, **kwargs):
        if not prefs.get("auto_export_on_change", False):
            return
        debounce = prefs.get("auto_export_debounce_secs", 60)
        if time.time() - self._last_export < debounce:
            return
        self.export_requested.emit("library_change")

    def _on_library_change_legacy(self):
        self._on_library_change()

    # ── Scheduled trigger ────────────────────────────────────────────────
    def start_schedule(self):
        interval_min = prefs.get("schedule_interval_minutes", 60)
        self._timer.start(interval_min * 60 * 1000)

    def stop_schedule(self):
        self._timer.stop()

    def restart_schedule(self):
        self.stop_schedule()
        if prefs.get("schedule_enabled", False):
            self.start_schedule()

    def _on_schedule_tick(self):
        if not prefs.get("schedule_enabled", False):
            return
        self.export_requested.emit("schedule")

    # ── Teardown ─────────────────────────────────────────────────────────
    def shutdown(self):
        self.stop_schedule()
        self.detach_library_change()
