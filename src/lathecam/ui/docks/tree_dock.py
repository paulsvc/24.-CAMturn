from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QColor, QBrush
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lathecam.models.project import LatheProject, OperationType
from lathecam.ui.i18n import get_language, tr
from lathecam.ui.theme import get_current_theme


class FeatureTreeDock(QDockWidget):
    """SolidWorks-style FeatureManager tree dock for Stock, CAD Faces, and Turning Operations."""

    node_selected = Signal(str, str)  # (node_kind: 'stock'|'profile'|'face'|'operation', node_id: str)
    operations_changed = Signal()
    assign_op_to_face_requested = Signal(str, object)  # (face_id, OperationType)

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
        self.tree.setColumnWidth(0, 215)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
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
        lang = get_language()

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

        # 2. CAD Machinable Faces Folder
        faces_root = QTreeWidgetItem(
            root,
            [
                tr("tree.faces_folder"),
                tr("tree.faces_count", count=len(self._project.faces)),
            ],
        )
        faces_root.setData(0, Qt.ItemDataRole.UserRole, ("faces_folder", "faces_folder"))
        faces_root.setForeground(1, QBrush(QColor("#d97706" if is_light else "#f59e0b")))
        faces_root.setExpanded(True)

        for face in self._project.faces:
            z_range_str = f"Z: {face.z_max:.1f} → {face.z_min:.1f}"
            f_item = QTreeWidgetItem(
                faces_root,
                [f"{face.icon} {face.format_label(lang)}", z_range_str],
            )
            f_item.setData(0, Qt.ItemDataRole.UserRole, ("face", face.face_id))
            f_item.setForeground(1, QBrush(QColor("#b45309" if is_light else "#fbbf24")))

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
            if op.geometry_scope == "face" and op.assigned_face_id:
                face_obj = self._project.get_face_by_id(op.assigned_face_id)
                if face_obj:
                    status_str = f"[F{face_obj.index}] {status_str}"
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
        """Programmatically selects an operation node (or clears if None)."""
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

    def select_face_by_id(self, face_id: str | None) -> None:
        """Programmatically selects a CAD Face node in the tree."""
        if not face_id:
            return
        self._updating = True
        iterator = self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive)
        for item in iterator:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, tuple) and data == ("face", face_id):
                self.tree.setCurrentItem(item)
                item.setSelected(True)
                break
        self._updating = False

    def _on_tree_context_menu(self, pos: QPoint) -> None:
        if self._project is None:
            return
        item = self.tree.itemAt(pos)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or data[0] != "face":
            return
        face = self._project.get_face_by_id(data[1])
        if face is None:
            return

        menu = QMenu(self)
        hdr = QAction(tr("face.menu_header", label=face.format_label(get_language())), self)
        hdr.setEnabled(False)
        menu.addAction(hdr)
        menu.addSeparator()

        act_rough = menu.addAction(tr("face.act_rough"))
        act_finish = menu.addAction(tr("face.act_finish"))
        act_thread = menu.addAction(tr("face.act_thread"))
        act_part = menu.addAction(tr("face.act_part"))

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen == act_rough:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.ROUGHING)
        elif chosen == act_finish:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.FINISHING)
        elif chosen == act_thread:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.THREADING)
        elif chosen == act_part:
            self.assign_op_to_face_requested.emit(face.face_id, OperationType.PARTING)

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
