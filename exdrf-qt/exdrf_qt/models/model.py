import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from exdrf.constants import RecIdType
from exdrf.filter import FilterType
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QTimer, pyqtSignal
from sqlalchemy import func, select, tuple_

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.models.field_list import FieldsList
from exdrf_qt.models.record import QtRecord
from exdrf_qt.models.requests import RecordRequestManager
from exdrf_qt.models.selector import Selector

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.worker import Work  # noqa: F401


DEFAULT_CHUNK_SIZE = 50
DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class QtModel(
    QtUseContext,
    RecordRequestManager,
    FieldsList,
    Generic[DBM],
    QAbstractItemModel,
):
    """A base class for models with database backend.

    Filtering consists of two parts: applying logic operators and filtering by
    the individual fields. The logic operators are by the code in this class
    inside the `filtered_selection` property. The filtering by the individual
    fields is done by the `Field` class.

    Attributes:
        ctx: The top level context.
        db_model: The database model class.
        fields: The fields of the model.
        selection: The SQLAlchemy select statement for the model that is
            active right now, computed from the base selection and filters,
            and ordered by the sort_by attribute.
        base_selection: The base SQLAlchemy select statement for the model.
            Filters and sorting are applied to this selection to create the
            selection attribute.
        sort_by: A list of tuples with the field name and order (asc or desc).
        filters: The filters to apply.
        cache: the list of items that have been loaded from the database.
        batch_size: The number of items to load at once. The model issues
            requests for items from the database when the total count is
            computed (if the cache is empty) and each time a request
            is made for an item that is not in the cache. Instead of loading
            one item at a time, the model loads a batch of items. The batch size
            is the number of items to load at once.

    Signals:
        totalCountChanged: Emitted when a change iin the total count is
            detected by the recalculate_total_count method.
        loadedCountChanged: Emitted when the number of items loaded from the
            database changes.
        requestIssued: Emitted when a request for items is issued. It receives
            the request ID, the starting index, the number of items to load,
            and the number of requests in progress, including this one.
        requestCompleted: Emitted when a request for items is completed. It
            receives the request ID, the starting index, the number of items
            loaded, and the number of requests in progress, excluding this one.
        requestError: Emitted when a request for items generates an error. It
            receives the request ID, the starting index, the number of items
            loaded, the number of requests in progress, and the error message.
    """

    db_model: Type[DBM]
    selection: "Select"
    base_selection: "Select"
    sort_by: List[Tuple[str, Literal["asc", "desc"]]]
    filters: FilterType
    cache: List["QtRecord"]
    batch_size: int
    _total_count: int
    _loaded_count: int

    totalCountChanged = pyqtSignal(int)
    loadedCountChanged = pyqtSignal(int)
    requestIssued = pyqtSignal(int, int, int, int)
    requestCompleted = pyqtSignal(int, int, int, int)
    requestError = pyqtSignal(int, int, int, int, str)

    def __init__(
        self,
        ctx: "QtContext",
        db_model: Type[DBM],
        fields: Optional[List["QtField"]] = None,
        parent: Optional["QObject"] = None,
        selection: Optional["Select"] = None,
        prevent_total_count: Optional[bool] = False,
        batch_size: int = DEFAULT_CHUNK_SIZE,
    ):
        """Initialize the model.

        Args:
            ctx: The top level context.
            db_model: The database model class.
            fields: The fields of the model.
            parent: The parent object.
            selection: The SQLAlchemy select statement for the model.
            prevent_total_count: If True, the total count is not computed
                in the constructor.
            batch_size: The number of items to load at once.
        """
        # super().__init__(parent=parent)
        QAbstractItemModel.__init__(self, parent=parent)
        RecordRequestManager.__init__(self)
        FieldsList.__init__(self)
        QtUseContext.__init__(self)

        self.ctx = ctx
        self.db_model = db_model
        self.fields = fields or []
        self.selection = (
            selection if selection is not None else select(db_model)
        )
        self.base_selection = self.selection
        self.sort_by = []
        self.filters = []
        self.batch_size = batch_size
        self.cache = []

        self._total_count = -1
        self._loaded_count = -1

        # Compute the total count.
        self._total_count = (
            -1 if prevent_total_count else self.recalculate_total_count()
        )

    def reset_model(self) -> None:
        """Reset the model.

        The function clears the cache and resets the total count.
        """
        self.beginResetModel()
        self.cache = []
        self.total_count = -1
        self.loaded_count = -1
        self.recalculate_total_count()
        self.endResetModel()

    def recalculate_total_count(self) -> int:
        """Recalculate the total number of items in the selection.

        Note that this function does *NOT` use the `self.selection` attribute.
        Instead, it counts the items in the query resulted from applying
        filters to the `root_selection`.

        Returns:
            The total number of items in the selection.
        """
        with self.ctx.same_session() as session:
            count_query = select(func.count()).select_from(
                self.filtered_selection.subquery()
            )
            count = cast(int, session.scalar(count_query))
            self.total_count = count
            return count

    @property
    def total_count(self) -> int:
        """Return the total number of items in the selection."""
        return self._total_count

    @total_count.setter
    def total_count(self, value: int) -> None:
        """Set the total count of items in the selection."""
        if value != self._total_count:
            self.ensure_stubs(value)
            self._total_count = value
            self.totalCountChanged.emit(value)

    @property
    def loaded_count(self) -> int:
        """Return the number of items loaded from the database."""
        return self._loaded_count

    @loaded_count.setter
    def loaded_count(self, value: int) -> None:
        """Set the number of items loaded from the database.

        Also emits the `loadedCountChanged` signal if the value changes.
        """
        if value != self._loaded_count:
            self._loaded_count = value
            self.loadedCountChanged.emit(value)

    @property
    def name(self) -> str:
        """Return the name of the model."""
        return self.db_model.__name__

    @property
    def filtered_selection(self) -> "Select":
        """Return the selection with filtering applied.

        The function starts from the `root_selection` and asks all filters
        to apply themselves but it does not change the internal `selection`
        attribute.

        If an exception occurs, the function logs the error and returns the
        `selection` attribute.
        """
        try:
            return (
                Selector[DBM]
                .from_qt_model(self)  # type: ignore
                .run(self.filters)
            )
        except Exception:
            logger.error("Error applying filters", exc_info=True)
            return self.selection

    @property
    def sorted_selection(self):
        """Return the selection with sorting applied.

        The function starts with `filtered_selection` and asks the field
        to apply sorting. If no sorting is applied, the function returns
        the `filtered_selection` as is.

        The function does not change the internal `selection` attribute.
        """
        if not self.sort_by:
            return self.filtered_selection

        try:
            result = []
            for field_key, order in self.sort_by:
                fld = self.get_field(field_key)
                if fld is None:
                    logger.warning(
                        "Sorting field %s not found in model %s",
                        field_key,
                        self.name,
                    )
                    continue
                if not fld.sortable:
                    logger.warning(
                        "Sorting field %s not sortable in model %s",
                        field_key,
                        self.name,
                    )
                    continue
                tmp = fld.apply_sorting(order == "asc")
                if tmp is not None:
                    result.append(tmp)

            return self.filtered_selection.order_by(*result)
        except Exception:
            logger.error("Error applying sorting", exc_info=True)
            return self.filtered_selection

    @property
    def is_fully_loaded(self) -> bool:
        """Return True if all items are loaded."""
        return self._loaded_count == self._total_count

    def ensure_stubs(self, new_total: int) -> None:
        """We populate the cache with stubs so that the model can be used."""
        crt_total = 0 if self._total_count <= 0 else self._total_count
        if crt_total >= new_total:
            self.cache = self.cache[:new_total]
            return
        if crt_total == new_total:
            return

        # We need to add stubs to the cache.
        for i in range(crt_total, new_total):
            self.cache.append(QtRecord(model=self, db_id=-1))  # type: ignore

        # If the cache is empty, we post a request for items.
        if self._loaded_count == 0:
            self.request_items(0, self.batch_size * 2)

    def request_items(self, start: int, count: int) -> None:
        """Request items from the database.

        The function loads items from the database and stores them in the
        cache.

        Args:
            start: The starting index of the items to load.
            count: The number of items to load.
        """
        if start + count > self.total_count:
            count = self.total_count - start
        if count <= 0:
            return
        req = self.new_request(start, count)
        if not self.trim_request(req):
            # There are already requests in progress that overlap with this one.
            return

        # Save to internal list.
        self.add_request(req)

        # Allow some time to accumulate requests before executing them.
        QTimer.singleShot(100, lambda: self.execute_request(req.uniq_id))

    def execute_request(self, req_id: int) -> None:
        """Delayed execution of the request.

        The function is called by the QTimer after a short delay to allow
        multiple requests to be accumulated. The function pushes the
        request to the worker thread and emits the `requestIssued` signal.
        """
        req = self.requests[req_id]

        # Prevent merges into this request.
        req.pushed = True

        self.ctx.push_work(
            statement=self.sorted_selection.offset(req.start).limit(req.count),
            callback=self._load_items,
            req_id=(id(self), req),
        )

        # Inform interested parties that a request has been issued.
        self.requestIssued.emit(
            req.uniq_id, req.start, req.count, len(self.requests)
        )

    def _load_items(self, work: "Work") -> None:
        """We are informed that a batch of items has been loaded."""
        # Locate the request in the list of requests.
        req = self.requests.pop(work.req_id[1].uniq_id, None)
        if req is None:
            logger.debug("Request %d not found in requests", work.req_id)
            return

        # If this request generated an error mark those requests as such.
        if work.error:
            for i in range(req.start, req.start + req.count):
                self.cache[i].db_id = -1
                self.cache[i].error = True
            logger.debug(
                "Request %d generated an error: %s", work.req_id, work.error
            )
            self.requestError.emit(
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
                work.error,
            )
        else:
            for i in range(req.start, req.start + req.count):
                self.db_item_to_record(
                    work.result[i - req.start], self.cache[i]
                )
            self.requestCompleted.emit(
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
            )
            self.loaded_count = self._loaded_count + req.count
        self.dataChanged.emit(
            self.createIndex(req.start, 0),
            self.createIndex(
                req.start + req.count - 1, len(self.column_fields) - 1
            ),
        )

    def db_item_to_record(
        self, item: DBM, record: Optional["QtRecord"]
    ) -> "QtRecord":
        """Convert a database item to a record.

        The function asks the fields to compute the values for each role of the
        corresponding column.

        Args:
            item: The database item.

        Returns:
            The newly created record.
        """
        from exdrf_qt.models.record import QtRecord

        if record is None:
            result = QtRecord(
                model=self,  # type: ignore
                db_id=cast(Any, self.get_db_item_id(item)),
            )
        else:
            result = record
            result.db_id = cast(Any, self.get_db_item_id(item))

        for f_index, fld in enumerate(self.column_fields):
            result.values[f_index] = fld.values(item)
        result.loaded = True
        return result

    def get_db_item_id(self, item: DBM) -> Union[int, Tuple[int, ...]]:
        """Return the ID of the database item.

        In common cases this is the `id` attribute of the database item.
        When the model has a composite primary key, the function returns a tuple
        of IDs. If the model has no primary key, the function raises an error.

        Args:
            item: The database item.

        Throws:
            ValueError: If the model has no primary key.
        """
        result = []
        for f in self.fields:
            if f.primary:
                result.append(getattr(item, f.name))
        if len(result) > 1:
            return tuple(result)
        if len(result) == 1:
            return result[0]
        raise ValueError(
            f"Item {item} does not have a primary key. "
            "Cannot convert to record."
        )

    def get_primary_columns(self) -> Any:
        """The result of this function can be used with the `.in_` attribute.

        If the model has a single primary key the result is the sqlalchemy
        column. If the model has a composite primary key, the result is a tuple
        of columns. If the model has no primary key, the function raises an
        error.

        Throws:
            ValueError: If the model has no primary key.
        """
        result = []
        for f in self.fields:
            if f.primary:
                result.append(getattr(self.db_model, f.name))
        assert len(result) > 0, "No primary columns found"
        if len(result) == 1:
            return result[0]
        return tuple_(*result)

    def get_id_filter(self, id_list: List[RecIdType]) -> Any:
        """Compute the select statement that filters by ID.

        Args:
            id_list: The list of IDs to filter by. If the model has a single
                primary key, the list should consist of single values. If the
                model has a composite primary key, the list should consist
                of tuples of values (the order of the items in the tuple
                should be the same as the order of the primary columns in
                the `self.fields` array).
        """
        return self.get_primary_columns().in_(id_list)

    def clone_me(self):
        """Clone the model.

        The function copies most of the attributes of the model. The cache
        starts up empty and the total count is recalculated.
        """
        result = self.__class__(
            ctx=self.ctx,
            db_model=self.db_model,
            selection=self.base_selection,
            prevent_total_count=True,
        )
        result.filters = self.filters
        result.sort_by = self.sort_by
        result.cache = []
        result.total_count = self.recalculate_total_count()
        result.loaded_count = -1
        return result

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            return self.total_count

        # Items have no children.
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()):
        return len(self.column_fields)

    def hasChildren(self, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            return True

        # Items have no children.
        return False

    def parent(self, child: QModelIndex = QModelIndex()):
        # Items have no children.
        return QModelIndex()

    def index(self, row: int, column: int, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            return QModelIndex()

        return self.createIndex(row, column)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        item: "QtRecord" = self.cache[row]
        if role == Qt.ItemDataRole.DisplayRole and not item.loaded:
            self.request_items(row, self.batch_size)

        return item.data(index.column(), cast(Qt.ItemDataRole, role))

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = 0
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            fld: "QtField" = self.column_fields[section]
            return fld.title or fld.title
        if (
            orientation == Qt.Orientation.Vertical
            and role == Qt.ItemDataRole.DisplayRole
        ):
            assert (
                0 <= section < len(self.cache)
            ), f"Bad section index: {section} not in [0, {len(self.cache)})"
            return self.cache[section].db_id
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        return None
