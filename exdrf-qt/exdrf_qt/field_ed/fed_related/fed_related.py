import logging
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from exdrf.validator import ValidationResult
from PyQt5.QtCore import QItemSelection
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import false, select

from exdrf_qt.controls.base_editor import ExdrfEditorBase
from exdrf_qt.controls.table_list import TreeViewDb
from exdrf_qt.field_ed.base import DrfFieldEd
from exdrf_qt.models.model import QtModel
from exdrf_qt.models.record import QtRecord
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    pass

    from PyQt5.QtWidgets import QAction

    from exdrf_qt.context import QtContext
    from exdrf_qt.field_ed.fed_related.base_adapter import BaseAdapter

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class DrfRelatedType(Enum):
    SIMPLE = "simple"
    BRIDGE = "bridge"


class DrfRelated(QWidget, Generic[DBM], DrfFieldEd):
    # -------- QtUseContext --------
    # create_window
    # close_window
    # get_icon
    # t
    # show_error
    # get_stg
    # set_stg
    # current_db_setting_id

    # -------- Field value in DrfFieldEd --------
    # _change_field_value
    # _field_value
    # is_empty
    # change_field_value
    # field_value
    # controlChanged
    # enteredErrorState

    # -------- NULL in DrfFieldEd --------
    # _nullable
    # nullable
    # change_nullable
    # clearable
    # getClearable
    # setClearable

    # -------- Read-Only in DrfFieldEd --------
    # _read_only
    # read_only
    # change_read_only
    # modifiable
    # getModifiable
    # setModifiable

    # -------- Name in DrfFieldEd --------
    # _name
    # name
    # getName
    # setName

    # -------- Editor integration in DrfFieldEd --------
    # form
    # set_form
    # load_value_from
    # save_value_to
    # constraints_changed

    # -------- Validation in DrfFieldEd --------
    # validate_control
    # is_valid

    # -------- Other in DrfFieldEd --------
    # add_clear_to_null_action
    # apply_description
    # create_ex_field
    # description
    # null_error

    adapter: "BaseAdapter"

    lay_main: "QHBoxLayout"
    lay_btns: "QVBoxLayout"
    btn_add: "QPushButton"
    btn_remove: "QPushButton"

    src_model: "QtModel[DBM]"
    src_list: "TreeViewDb"

    dst_model: "QtModel[DBM]"
    dst_list: "TreeViewDb"

    def __init__(
        self,
        ctx: "QtContext",
        dst_model: Type[QtModel[DBM]],
        src_model: Type[QtModel[DBM]],
        dst_db_model: Type[DBM],
        src_db_model: Type[DBM],
        variant: DrfRelatedType = DrfRelatedType.SIMPLE,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        self.ctx = ctx

        # Initialize parent classes.
        QWidget.__init__(self, parent)
        DrfFieldEd.__init__(self, ctx=ctx)

        # Create the models.
        self.create_models(
            dst_model=dst_model,
            src_model=src_model,
            dst_db_model=dst_db_model,
            src_db_model=src_db_model,
        )

        # Setup the UI.
        self.setup_ui()

        # Create the adapter based on user selection.
        if variant == DrfRelatedType.SIMPLE:
            from exdrf_qt.field_ed.fed_related.simple_adapter import (
                SimpleAdapter,
            )

            self.adapter = SimpleAdapter(ctx=ctx, core=self, **kwargs)
        elif variant == DrfRelatedType.BRIDGE:
            from exdrf_qt.field_ed.fed_related.bridge_adapter import (
                BridgeAdapter,
            )

            self.adapter = BridgeAdapter(ctx=ctx, core=self, **kwargs)
        else:
            raise ValueError(f"Invalid variant: {variant}")

        # Load models into the lists.
        self.adapter.adjust_model(self.dst_model)
        self.src_list.setModel(self.src_model)
        self.dst_list.setModel(self.dst_model)

        # Prepare the lists.
        self.prepare_views()

        # Start the adapter.
        self.adapter.started()

    def setup_ui(self) -> None:
        """Setup the UI."""
        # Create the main layout.
        self.lay_main = QHBoxLayout()
        # Create the source list.
        self.src_list = TreeViewDb(parent=self, ctx=self.ctx)
        self.lay_main.addWidget(self.src_list)

        # Create the middle buttons.
        self.create_middle_buttons()

        # Create the destination list.
        self.dst_list = TreeViewDb(parent=self, ctx=self.ctx)
        self.adjust_dst_actions()
        self.lay_main.addWidget(self.dst_list)

        # Set the layout for the page.
        self.setLayout(self.lay_main)

    def adjust_dst_action(self, action: "QAction", handler: Any):
        try:
            action.triggered.disconnect()
        except Exception:
            pass
        action.triggered.connect(handler)

    def adjust_dst_actions(self):
        self.adjust_dst_action(self.dst_list.ac_rem, self.on_btn_remove_clicked)
        self.adjust_dst_action(self.dst_list.ac_rem_all, self.on_remove_all)

    def create_models(
        self,
        dst_model: Type[QtModel[DBM]],
        src_model: Type[QtModel[DBM]],
        dst_db_model: Type[DBM],
        src_db_model: Type[DBM],
    ) -> None:
        """Create the models."""

        # Source model.
        self.src_model = src_model(
            ctx=self.ctx,
            db_model=src_db_model,
            parent=self,
        )

        # Create the destination model.
        self.dst_model = dst_model(
            ctx=self.ctx,
            db_model=dst_db_model,
            parent=self,
            # We purposefully provide a selection here that returns
            # no results.
            selection=select(dst_db_model).where(false()),
        )

    def create_middle_buttons(self) -> None:
        """Create the buttons in the median strip.

        These allow the user to add and remove records from the relationship.
        """

        # The layout that hosts them.
        self.lay_btns = QVBoxLayout()

        # Add a spacer item to push the buttons from the top.
        self.lay_btns.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        self.btn_add = QPushButton(self.t("cmn.add-left", "Add 🡆"), parent=self)
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self.on_btn_add_clicked)
        self.lay_btns.addWidget(self.btn_add)

        self.btn_remove = QPushButton(
            self.t("cmn.remove-right", "🡄 Remove"), parent=self
        )
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self.on_btn_remove_clicked)
        self.lay_btns.addWidget(self.btn_remove)

        # Add a spacer item to push the buttons from the bottom.
        self.lay_btns.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Add the layout to the main layout.
        self.lay_main.addLayout(self.lay_btns)

    def prepare_views(self) -> None:
        """Setup the buttons."""
        sm_src = self.src_list.selectionModel()
        if sm_src is not None:
            sm_src.selectionChanged.connect(self.on_src_selection_changed)

        sm_dst = self.dst_list.selectionModel()
        if sm_dst is not None:
            sm_dst.selectionChanged.connect(self.on_dst_selection_changed)

        # React to change in number of items.
        self.dst_model.totalCountChanged.connect(
            self.on_dst_total_count_changed
        )
        # Remove unused actions.
        self.dst_list.ac_new.deleteLater()
        self.dst_list.ac_new = None  # type: ignore
        self.dst_list.ac_view.deleteLater()
        self.dst_list.ac_view = None  # type: ignore
        self.dst_list.ac_edit.deleteLater()
        self.dst_list.ac_edit = None  # type: ignore
        self.dst_list.ac_clone.deleteLater()
        self.dst_list.ac_clone = None  # type: ignore
        self.dst_list.ac_filter.deleteLater()
        self.dst_list.ac_filter = None  # type: ignore

    @top_level_handler
    def on_src_selection_changed(
        self, selected: "QItemSelection", deselected: "QItemSelection"
    ) -> None:
        """Handle the selection change in the source list."""
        enabled = not selected.isEmpty()
        if self.form and not self.form.is_editing:
            enabled = False

        self.btn_add.setEnabled(enabled)

    @top_level_handler
    def on_dst_selection_changed(
        self, selected: "QItemSelection", deselected: "QItemSelection"
    ) -> None:
        """Handle the selection change in the destination list."""
        enabled = not selected.isEmpty()
        if self.form and not self.form.is_editing:
            enabled = False

        self.btn_remove.setEnabled(enabled)

    @top_level_handler
    def on_btn_add_clicked(self) -> None:
        """Handle the click on the add button."""

        # Collect the selected source records.
        src_sm = self.src_list.selectionModel()
        if src_sm is None:
            return
        selected_rows = [i.row() for i in src_sm.selectedRows()]
        if not selected_rows:
            return

        # Only collect loaded records.
        selected_records = [
            self.src_model.data_record(i) for i in selected_rows
        ]
        if not selected_records:
            return
        filtered_records = [
            r
            for r in selected_records
            if r and r.loaded and not r.error and r.db_id is not None
        ]
        self.adapter.add_records(filtered_records)

        # Clear the selection in the source list.
        src_sm.clearSelection()

    @top_level_handler
    def on_btn_remove_clicked(self) -> None:
        """Handle the click on the remove button."""
        # Collect the selected destination records.
        dst_sm = self.dst_list.selectionModel()
        if dst_sm is None:
            return
        selected_rows = [i.row() for i in dst_sm.selectedRows()]
        if not selected_rows:
            return

        # Collect all records.
        selected_records = [
            (self.dst_model.data_record(i), i) for i in selected_rows
        ]
        if not selected_records:
            return
        filtered_records = cast(
            "List[Tuple[QtRecord, int]]",
            [r for r in selected_records if r[0] is not None],
        )
        self.adapter.remove_records(filtered_records)

        # Clear the selection in the destination list.
        dst_sm.clearSelection()

    def change_field_value(self, new_value: Any) -> None:
        raise NotImplementedError(
            "This method is not implemented. "
            "The control only works under an editor for now."
        )

    def validate_control(self) -> "ValidationResult":
        return self.adapter.validate_control()

    def load_value_from(self, record: DBM):
        self.adapter.load_value_from(record)

    def save_value_to(self, record: DBM):
        self.adapter.save_value_to(record)

    def set_form(self, form: "ExdrfEditorBase"):
        form.recordSaved.connect(self.on_record_saved)
        return super().set_form(form)

    @top_level_handler
    def on_record_saved(self, record: DBM):
        """Handle the record saved signal."""
        self.adapter.load_value_from(record)

    @top_level_handler
    def on_remove_all(self) -> None:
        """Handle the remove all button click."""
        # Collect the selected destination records.
        dst_sm = self.dst_list.selectionModel()
        if dst_sm is None:
            return

        # Collect all records.
        selected_records = dst_sm.iter_records(
            include_top=True,
        )
        if not selected_records:
            return
        filtered_records = cast(
            "List[Tuple[QtRecord, int]]",
            [r for r in selected_records if r[0] is not None],
        )
        self.adapter.remove_records(filtered_records)

        # Clear the selection in the destination list.
        dst_sm.clearSelection()

    @top_level_handler
    def on_dst_total_count_changed(self, count: int) -> None:
        """Handle the change in the total number of items in the destination
        list.

        Args:
            count: The new total number of items.
        """
        enabled = count > 0
        if self.form and not self.form.is_editing:
            enabled = False
        self.dst_list.ac_rem_all.setEnabled(enabled)

    def change_edit_mode(self, in_editing: bool) -> None:
        """Change the edit mode of the related editor.

        Args:
            is_editing: True if the editor is in editing mode, False otherwise.
        """
        # Source selection.
        src_sm = self.src_list.selectionModel()
        src_enabled = in_editing
        if in_editing and src_sm is not None:
            src_enabled = not src_sm.selectedRows().isEmpty()

        # Destination selection.
        dst_sm = self.dst_list.selectionModel()
        dst_enabled = in_editing
        if in_editing and dst_sm is not None:
            dst_enabled = not dst_sm.selectedRows().isEmpty()

        # Change the buttons.
        self.btn_add.setEnabled(src_enabled)
        self.btn_remove.setEnabled(dst_enabled)
        self.dst_list.ac_rem.setEnabled(dst_enabled)

        self.dst_list.ac_rem_all.setEnabled(
            in_editing and self.dst_model.total_count > 0
        )
