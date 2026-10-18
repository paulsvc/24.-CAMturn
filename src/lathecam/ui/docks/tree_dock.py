from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lathecam.models.project import LatheProject
from lathecam.ui.i18n import tr
from lathecam.ui.theme import get_current_theme


class FeatureTreeDock(QDockWidget):
    """SolidWorks-style FeatureManager tree dock for Stock, Part Profile, and Turning Operations."""

    node_selected = Signal(str, str)  # (node_kind: 'stock'|'profile'|'operation', node_id: str)
    operations_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("tree.dock_title"), parent)
        self.setObjectName("FeatureTreeDock")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._project: LatheProject | None = None
        self._updating = False

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("tree.col_feature"), tr("tree.col_status")])
        self.tree.setColumnWidth(0, 210)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

        btn_row = QHBoxLayout()
        self.btn_up = QPushButton(tr("tree.btn_up"))
        self.btn_up.setObjectName("secondaryBtn")
        self.btn_up.clicked.connect(self._move_op_up)

        self.btn_down = QPushButton(tr("tree.btn_down"))
        self.btn_down.setObjectName("secondaryBtn")
        self.btn_down.clicked.connect(self._move_op_down)

        self.btn_delete = QPushButton(tr("tree.btn_remove"))
        self.btn_delete.setObjectName("secondaryBtn")
        self.btn_delete.clicked.connect(self._delete_selected_op)

        btn_row.addWidget(self.btn_up)
        btn_row.addWidget(self.btn_down)
        btn_row.addWidget(self.btn_delete)
        layout.addLayout(btn_row)

        self.setWidget(container)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("tree.dock_title"))
        self.tree.setHeaderLabels([tr("tree.col_feature"), tr("tree.col_status")])
        self.btn_up.setText(tr("tree.btn_up"))
        self.btn_down.setText(tr("tree.btn_down"))
        self.btn_delete.setText(tr("tree.btn_remove"))
        self.refresh()

    def set_project(self, project: LatheProject) -> None:
        self._project = project
        self.refresh()

    def refresh(self) -> None:
        if self._project is None:
            return

        selected_id = self.current_selected_op_id()
        is_light = get_current_theme() == "light"

        self._updating = True
        self.tree.clear()

        root = QTreeWidgetItem(self.tree, [f"⚙ {self._project.name}", "G18 / G7"])
        root.setData(0, Qt.ItemDataRole.UserRole, ("root", "root"))
        root.setExpanded(True)

        # 1. Stock Node
        st = self._project.stock
        stock_item = QTreeWidgetItem(
            root,
            [tr("tree.stock_node"), f"Ø{st.od_mm:.1f} × {st.length:.1f}mm"],
        )
        stock_item.setData(0, Qt.ItemDataRole.UserRole, ("stock", "stock"))
        stock_item.setForeground(1, QBrush(QColor("#0284c7" if is_light else "#38bdf8")))

        # 2. CAD Profile Node
        c = self._project.contour
        prof_item = QTreeWidgetItem(
            root,
            [tr("tree.profile_node"), f"{len(c.points)} pts (Ø{c.x_max*2:.1f}mm)"],
        )
        prof_item.setData(0, Qt.ItemDataRole.UserRole, ("profile", "profile"))
        prof_item.setForeground(1, QBrush(QColor("#7c3aed" if is_light else "#a78bfa")))

        # 3. Operations Folder
        dialect_label = "Fanuc 0i-TF" if self._project.post_dialect == "fanuc" else "LinuxCNC"
        ops_root = QTreeWidgetItem(
            root,
            [
                tr("tree.ops_folder", dialect=dialect_label),
                tr("tree.ops_count", count=len(self._project.operations)),
            ],
        )
        ops_root.setData(0, Qt.ItemDataRole.UserRole, ("ops_folder", "ops_folder"))
        ops_root.setExpanded(True)

        for op in self._project.operations:
            status_str = tr("tree.cmds_count", tool_id=op.tool_id, count=len(op.commands))
            if op.warning_message:
                status_str = f"⚠ {op.warning_message[:22]}"

            op_item = QTreeWidgetItem(ops_root, [op.name, status_str])
            op_item.setFlags(op_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            op_item.setCheckState(
                0,
                Qt.CheckState.Checked if op.enabled else Qt.CheckState.Unchecked,
            )
            op_item.setData(0, Qt.ItemDataRole.UserRole, ("operation", op.op_id))

            if op.warning_message:
                op_item.setForeground(1, QBrush(QColor("#dc2626" if is_light else "#ef4444")))
                op_item.setToolTip(1, op.warning_message)
            elif not op.enabled:
                op_item.setForeground(0, QBrush(QColor("#94a3b8" if is_light else "#64748b")))
                op_item.setForeground(1, QBrush(QColor("#94a3b8" if is_light else "#64748b")))
            else:
                op_item.setForeground(1, QBrush(QColor("#15803d" if is_light else "#22c55e")))

            if selected_id and op.op_id == selected_id:
                op_item.setSelected(True)
                self.tree.setCurrentItem(op_item)

        self.tree.expandAll()
        self._updating = False

    def current_selected_op_id(self) -> str | None:
        items = self.tree.selectedItems()
        if not items:
            return None
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and len(data) == 2 and data[0] == "operation":
            return data[1]
        return None

    def select_operation_by_id(self, op_id: str | None) -> None:
        """Programmatically selects an operation node (or 'all' if None)."""
        if op_id is None:
            self.tree.clearSelection()
            return
        iterator = self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive)
        for item in iterator:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, tuple) and data == ("operation", op_id):
                self.tree.setCurrentItem(item)
                item.setSelected(True)
                break

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self.tree.selectedItems()
        if not items:
            self.node_selected.emit("root", "root")
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and len(data) == 2:
            self.node_selected.emit(data[0], data[1])

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating or self._project is None or column != 0:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and data[0] == "operation":
            op_id = data[1]
            for op in self._project.operations:
                if op.op_id == op_id:
                    op.enabled = item.checkState(0) == Qt.CheckState.Checked
                    break
            self.operations_changed.emit()

    def _move_op_up(self) -> None:
        if self._project is None:
            return
        op_id = self.current_selected_op_id()
        if not op_id:
            return
        ops = self._project.operations
        idx = next((i for i, o in enumerate(ops) if o.op_id == op_id), -1)
        if idx > 0:
            ops[idx - 1], ops[idx] = ops[idx], ops[idx - 1]
            self.operations_changed.emit()

    def _move_op_down(self) -> None:
        if self._project is None:
            return
        op_id = self.current_selected_op_id()
        if not op_id:
            return
        ops = self._project.operations
        idx = next((i for i, o in enumerate(ops) if o.op_id == op_id), -1)
        if 0 <= idx < len(ops) - 1:
            ops[idx + 1], ops[idx] = ops[idx], ops[idx + 1]
            self.operations_changed.emit()

    def _delete_selected_op(self) -> None:
        if self._project is None:
            return
        op_id = self.current_selected_op_id()
        if not op_id:
            return
        self._project.operations = [o for o in self._project.operations if o.op_id != op_id]
        self.operations_changed.emit()
