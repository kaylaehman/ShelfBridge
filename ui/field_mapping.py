"""Field-mapping tab (minimal stub).

Lets the user define per-service ``{source_key: target_key}`` overrides stored in
``prefs["field_maps"]``. The pipeline applies these via ``field_mapping.apply_field_map``.
Kept intentionally small (design decision C) — the full v0.4.0 mapping UX is out
of scope for this build.
"""
from calibre_plugins.shelf_bridge.ui.qt import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QComboBox,
    QPushButton, QHBoxLayout,
)
from calibre_plugins.shelf_bridge.prefs import prefs
from calibre_plugins.shelf_bridge.adapters import list_adapters

_BOOK_FIELDS = [
    "title", "authors", "isbn", "isbn13", "publisher", "pub_date", "tags",
    "series", "series_index", "rating", "read_dates", "languages", "comments",
]


class FieldMappingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Optional: rename book fields before export, per service.\n"
            "Leave empty to use the default mapping."))

        self.service = QComboBox()
        for cls in list_adapters():
            self.service.addItem(cls.display_name, cls.service_id)
        self.service.currentIndexChanged.connect(self._load_service)
        layout.addWidget(self.service)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Book field", "Target column"])
        layout.addWidget(self.table)

        row = QHBoxLayout()
        add = QPushButton("Add row")
        add.clicked.connect(lambda: self._add_row("", ""))
        remove = QPushButton("Remove selected")
        remove.clicked.connect(self._remove_selected)
        row.addWidget(add)
        row.addWidget(remove)
        layout.addLayout(row)

        self._load_service()

    def _current_service(self):
        return self.service.currentData()

    def _add_row(self, src, tgt):
        r = self.table.rowCount()
        self.table.insertRow(r)
        combo = QComboBox()
        combo.addItems(_BOOK_FIELDS)
        if src in _BOOK_FIELDS:
            combo.setCurrentIndex(_BOOK_FIELDS.index(src))
        self.table.setCellWidget(r, 0, combo)
        self.table.setItem(r, 1, QTableWidgetItem(tgt))

    def _remove_selected(self):
        for idx in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(idx)

    def _load_service(self):
        self.table.setRowCount(0)
        mapping = prefs.get("field_maps", {}).get(self._current_service(), {})
        for src, tgt in mapping.items():
            self._add_row(src, tgt)

    def save(self):
        all_maps = dict(prefs.get("field_maps", {}))
        mapping = {}
        for r in range(self.table.rowCount()):
            combo = self.table.cellWidget(r, 0)
            tgt_item = self.table.item(r, 1)
            src = combo.currentText() if combo else ""
            tgt = tgt_item.text().strip() if tgt_item else ""
            if src and tgt:
                mapping[src] = tgt
        all_maps[self._current_service()] = mapping
        prefs["field_maps"] = all_maps
