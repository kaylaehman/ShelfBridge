"""ShelfBridge InterfaceAction — toolbar button, menus, automation wiring.

Auto-export is offloaded to a worker QThread so trigger-driven network/file I/O
never runs on the Calibre GUI thread (review arch C2).
"""
import time

from calibre.gui2.actions import InterfaceAction

from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge.automation.trigger import ShelfBridgeTrigger
from calibre_plugins.shelf_bridge.automation.export_runner import run_export_headless
from calibre_plugins.shelf_bridge.ui.qt import QMenu, QThread, pyqtSignal


class _AutoExportThread(QThread):
    done = pyqtSignal(dict)

    def __init__(self, gui, reason, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.reason = reason

    def run(self):
        try:
            db = self.gui.current_db.new_api
            summary = run_export_headless(db, reason=self.reason)
            self.done.emit(summary)
        except Exception:  # pragma: no cover
            self.done.emit({"results": {}, "trigger": self.reason})


class ShelfBridgeAction(InterfaceAction):
    name = 'ShelfBridge'
    action_spec = ('Export Catalog', None,
                   'Export library to a reading service', 'Ctrl+Shift+E')

    def genesis(self):
        icon = get_icons('images/icon.png')  # noqa: F821 (Calibre injects get_icons)
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.show_export_dialog)

        # A fresh InterfaceAction qaction has no menu; create one so the toolbar
        # button's dropdown exposes Export + Configure. (Without this,
        # qaction.menu() is None and create_menu_action would fail.)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.create_menu_action(self.menu, 'shelf_bridge_export', 'Export Catalog…',
                                triggered=self.show_export_dialog)
        self.create_menu_action(self.menu, 'shelf_bridge_config', 'Configure Services…',
                                triggered=self.show_config)

        self._auto_thread = None
        self._trigger = ShelfBridgeTrigger(self.gui, parent=self.gui)
        self._trigger.export_requested.connect(self._on_auto_export)
        if prefs.get("auto_export_on_change", False):
            self._trigger.attach_library_change()
        if prefs.get("schedule_enabled", False):
            self._trigger.start_schedule()

    # ── Manual actions ───────────────────────────────────────────────────
    def show_export_dialog(self):
        from calibre_plugins.shelf_bridge.ui.dialogs import ExportDialog
        d = ExportDialog(self.gui)
        d.exec_() if hasattr(d, "exec_") else d.exec()

    def show_config(self):
        from calibre_plugins.shelf_bridge.config import ConfigDialog
        d = ConfigDialog(self.gui, self.qaction)
        result = d.exec_() if hasattr(d, "exec_") else d.exec()
        if result:
            self.apply_settings()

    # ── Preferences → Plugins → Customize plugin ─────────────────────────
    # InterfaceActionBase delegates these to the InterfaceAction, so defining
    # them here makes the "Customize plugin" button open ShelfBridge's settings.
    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.shelf_bridge.config import ConfigWidget
        return ConfigWidget(self.gui)

    def save_settings(self, config_widget):
        config_widget.save_settings()
        self.apply_settings()

    # ── Automation ───────────────────────────────────────────────────────
    def _on_auto_export(self, reason):
        if self._auto_thread is not None and self._auto_thread.isRunning():
            return  # an export is already in flight
        self._auto_thread = _AutoExportThread(self.gui, reason, parent=self.gui)
        self._auto_thread.done.connect(self._on_auto_done)
        self._auto_thread.start()

    def _on_auto_done(self, summary):
        self._trigger._last_export = time.time()
        if not prefs.get("notify_on_auto_export", True):
            return
        total = sum(r.get("records_exported", 0)
                    for r in summary.get("results", {}).values()
                    if isinstance(r, dict) and r.get("success"))
        trigger = summary.get("trigger", "auto")
        try:
            self.gui.status_bar.showMessage(
                f"[ShelfBridge] Auto-export ({trigger}): {total} books synced.", 5000)
        except Exception:
            pass

    def apply_settings(self):
        if prefs.get("auto_export_on_change", False):
            self._trigger.attach_library_change()
        else:
            self._trigger.detach_library_change()
        self._trigger.restart_schedule()

    def shutdown(self):
        try:
            self._trigger.shutdown()
        finally:
            super().shutdown()
