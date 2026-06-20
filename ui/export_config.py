"""Export configuration tab: scope (full library / virtual library) and the
column set for Google Sheets + OneDrive (include/exclude, reorder, rename)."""
from calibre_plugins.shelf_bridge.ui.qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QRadioButton,
    QComboBox, QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    Qt_Checked, Qt_Unchecked, Qt_ItemIsUserCheckable,
)
from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge import columns as C


class ExportPanel(QWidget):
    title = "Export"

    def __init__(self, gui=None, parent=None):
        super().__init__(parent)
        self.gui = gui
        layout = QVBoxLayout(self)

        # ── Scope ─────────────────────────────────────────────────────────
        scope = QGroupBox("Books to export")
        sform = QFormLayout(scope)
        self.rb_all = QRadioButton("Entire library")
        self.rb_vl = QRadioButton("Virtual library:")
        self.vl_combo = QComboBox()
        self.vl_combo.addItems(self._virtual_library_names())
        sform.addRow(self.rb_all)
        row = QHBoxLayout()
        row.addWidget(self.rb_vl)
        row.addWidget(self.vl_combo)
        holder = QWidget(); holder.setLayout(row)
        sform.addRow(holder)
        layout.addWidget(scope)

        # ── Columns ───────────────────────────────────────────────────────
        colbox = QGroupBox("Columns (Google Sheets & OneDrive)")
        cl = QVBoxLayout(colbox)
        cl.addWidget(QLabel("Check to include; edit Header to rename; reorder with the buttons."))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Field", "Header"])
        cl.addWidget(self.table)
        btns = QHBoxLayout()
        up = QPushButton("Move Up"); up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Move Down"); down.clicked.connect(lambda: self._move(1))
        btns.addWidget(up); btns.addWidget(down); btns.addStretch(1)
        cl.addLayout(btns)
        layout.addWidget(colbox)

        self._load()

    # scope helpers ---------------------------------------------------------
    def _virtual_library_names(self):
        try:
            return list(self.gui.current_db.new_api.pref("virtual_libraries", {}) or {})
        except Exception:
            return []

    def _custom_columns(self):
        try:
            md = self.gui.current_db.new_api.field_metadata.custom_field_metadata()
            return {k: None for k in md}
        except Exception:
            return {}

    # columns table ---------------------------------------------------------
    def _row(self, field, header, enabled):
        r = self.table.rowCount()
        self.table.insertRow(r)
        fitem = QTableWidgetItem(field)
        fitem.setFlags(fitem.flags() | Qt_ItemIsUserCheckable)
        fitem.setCheckState(Qt_Checked if enabled else Qt_Unchecked)
        self.table.setItem(r, 0, fitem)
        self.table.setItem(r, 1, QTableWidgetItem(header))

    def _move(self, delta):
        r = self.table.currentRow()
        if r < 0:
            return
        nr = r + delta
        if not (0 <= nr < self.table.rowCount()):
            return
        # swap by re-reading both rows
        a = (self.table.item(r, 0), self.table.item(r, 1))
        rows = [self._read_row(i) for i in range(self.table.rowCount())]
        rows[r], rows[nr] = rows[nr], rows[r]
        self.table.setRowCount(0)
        for field, header, enabled in rows:
            self._row(field, header, enabled)
        self.table.setCurrentCell(nr, 0)

    def _read_row(self, r):
        fitem = self.table.item(r, 0)
        hitem = self.table.item(r, 1)
        return (fitem.text(), hitem.text() if hitem else fitem.text(),
                fitem.checkState() == Qt_Checked)

    def _load(self):
        # scope
        mode = prefs.get("export_mode", "all")
        self.rb_vl.setChecked(mode == "virtual_library")
        self.rb_all.setChecked(mode != "virtual_library")
        name = prefs.get("export_virtual_library", "")
        idx = self.vl_combo.findText(name)
        if idx >= 0:
            self.vl_combo.setCurrentIndex(idx)
        # columns: saved order, then append any unseen available fields (disabled)
        custom = self._custom_columns()
        saved = C.resolve_columns(prefs, custom) or C.default_columns()
        seen = {c["field"] for c in saved}
        avail = dict(C.available_fields(custom))
        for c in saved:
            self._row(c["field"], c["header"], c["enabled"])
        for field, header in C.available_fields(custom):
            if field not in seen:
                self._row(field, header, False)

    def save(self):
        prefs["export_mode"] = "virtual_library" if self.rb_vl.isChecked() else "all"
        prefs["export_virtual_library"] = self.vl_combo.currentText() if self.rb_vl.isChecked() else ""
        cols = []
        for r in range(self.table.rowCount()):
            field, header, enabled = self._read_row(r)
            cols.append({"field": field, "header": header or field, "enabled": enabled})
        prefs["export_columns"] = cols
