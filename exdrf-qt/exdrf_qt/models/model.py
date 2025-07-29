import logging
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import sqlparse
from exdrf.constants import RecIdType
from exdrf.filter import FieldFilter, FilterType, validate_filter
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QTimer, pyqtSignal
from sqlalchemy import case, func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from unidecode import unidecode

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.models.cache import SparseList
from exdrf_qt.models.field_list import FieldsList
from exdrf_qt.models.record import QtRecord
from exdrf_qt.models.requests import RecordRequestManager
from exdrf_qt.models.selector import Selector

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.models.requests import RecordRequest  # noqa: F401
    from exdrf_qt.worker import Work  # noqa: F401


DEFAULT_CHUNK_SIZE = 8
DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


def compare_filters(f1, f2):
    if isinstance(f1, (list, tuple)) and isinstance(f2, (list, tuple)):
        if len(f1) != len(f2):
            return False
        return all(compare_filters(i1, i2) for i1, i2 in zip(f1, f2))
    else:
        if isinstance(f1, dict):
            f1 = FieldFilter(**f1)
        if isinstance(f2, dict):
            f2 = FieldFilter(**f2)
        return f1 == f2


class QtModel(
    QtUseContext,
    RecordRequestManager,
    FieldsList,
    Generic[DBM],
    QAbstractItemModel,
):
    """A base class for models with database backend.

    To change filtering or sorting change the `filters` and `sort_by`
    parameters then call the `reset_model` method. The cache will be cleared
    and the total count will be recomputed. You can also use apply_filter()
    and apply_simple_search() methods to change the filters.

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
        prioritized_ids: A list of IDs to prioritize in sorting.
        filters: The filters to apply.
        top_cache: A list of items that are independently managed from the
            bulk of the cache. These are not subject to normal insertion and
            deletion.
        cache: the list of items that have been loaded from the database. The
            items are indexed by their 0-based position in the result of the
            selection (so ignoring top_cache items).
        batch_size: The number of items to load at once. The model issues
            requests for items from the database when the total count is
            computed (if the cache is empty) and each time a request
            is made for an item that is not in the cache. Instead of loading
            one item at a time, the model loads a batch of items. The batch size
            is the number of items to load at once.
        _total_count: The total number of items in the selection.
        _loaded_count: The number of items loaded from the database.
        _checked: A list of database IDs that are checked. If this list is None
            (default) the model shows no checkboxes.
        _db_to_row: A dictionary that maps database IDs to row indices in the
            cache (does not include top_cache items).
        _wait_before_request: The number of milliseconds to wait before issuing
            a request for items.

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
            loaded, the number of requests in progress excluding this one,
            and the error message.
    """

    db_model: Type[DBM]
    selection: "Select"
    base_selection: "Select"
    sort_by: List[Tuple[str, Literal["asc", "desc"]]]
    prioritized_ids: Optional[List[RecIdType]]
    _filters: FilterType
    top_cache: List["QtRecord"]
    cache: SparseList["QtRecord"]
    batch_size: int
    _total_count: int
    _loaded_count: int
    _checked: Optional[Set[RecIdType]] = None
    _db_to_row: Dict[RecIdType, int]
    _wait_before_request: int

    totalCountChanged = pyqtSignal(int)
    checkedChanged = pyqtSignal()
    loadedCountChanged = pyqtSignal(int)
    requestIssued = pyqtSignal(int, int, int, int)
    requestCompleted = pyqtSignal(int, int, int, int)
    requestError = pyqtSignal(int, int, int, int, str)

    def __init__(
        self,
        ctx: "QtContext",
        db_model: Type[DBM],
        fields: Optional[List[Union["QtField", Type["QtField"]]]] = None,
        parent: Optional["QObject"] = None,
        selection: Optional["Select"] = None,
        prevent_total_count: Optional[bool] = False,
        batch_size: int = DEFAULT_CHUNK_SIZE,
        wait_before_request: int = 100,
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
        self.top_cache = []
        self._wait_before_request = wait_before_request
        self._db_to_row = {}
        self.db_model = db_model
        self.fields = cast(Any, fields if fields is not None else [])
        self.selection = (
            selection if selection is not None else select(db_model)
        )
        self.base_selection = self.selection
        self.sort_by = []
        self.prioritized_ids = None
        self._filters = []
        self.batch_size = batch_size
        self.cache = SparseList(lambda: QtRecord(model=self, db_id=-1))

        self._total_count = -1
        self._loaded_count = 0

        # Compute the total count.
        self._total_count = (
            -1 if prevent_total_count else self.recalculate_total_count()
        )

    def reset_model(self) -> None:
        """Reset the model.

        The function clears the cache and resets the total count.
        """
        self.beginResetModel()
        self.cache.clear()
        self._db_to_row = {}
        self._total_count = -1
        self._loaded_count = 0
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
        """Return the total number of items in the model.

        This value includes the number of items computed from the database table
        and the number of items in the top cache.
        """
        return self._total_count + len(self.top_cache)

    @total_count.setter
    def total_count(self, value: int) -> None:
        """Set the total count of items in the selection.

        The argument should not include the number of items in the top cache.
        """
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
    def filters(self) -> FilterType:
        """Return the filters."""
        return self._filters

    @filters.setter
    def filters(self, value: FilterType) -> None:
        """Set the filters."""
        validate_result = validate_filter(value)
        if validate_result:
            error = (
                f"Invalid filters: {validate_result[0]} "
                f"{'->'.join(validate_result[1:])}"
            )
            logger.error(error)
            raise ValueError(error)
        self._filters = value

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
                .run(self._filters)
            )
        except Exception:
            logger.error(
                "Error while computing the filtered selection",
                exc_info=True,
            )
            return self.selection

    @property
    def sorted_selection(self):
        """Return the selection with sorting applied.

        The function starts with `filtered_selection` and asks the field
        to apply sorting. If no sorting is applied, the function returns
        the `filtered_selection` as is.

        The function does not change the internal `selection` attribute.
        """
        order_by_clauses = []

        if self.prioritized_ids:
            primary_cols = self.get_primary_columns()
            order_by_expression = case(
                (primary_cols.in_(self.prioritized_ids), 0), else_=1
            )
            order_by_clauses.append(order_by_expression)

        if not self.sort_by:
            if not order_by_clauses:
                return self.filtered_selection
        else:
            try:
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
                        order_by_clauses.append(tmp)

            except Exception:
                logger.error("Error applying sorting", exc_info=True)
                return self.filtered_selection

        if order_by_clauses:
            return self.filtered_selection.order_by(*order_by_clauses)
        return self.filtered_selection

    @property
    def is_fully_loaded(self) -> bool:
        """Return True if all items are loaded."""
        return self._loaded_count == self._total_count

    @property
    def checked_ids(self) -> Optional[Set[RecIdType]]:
        """Return the list of checked items."""
        return self._checked

    @checked_ids.setter
    def checked_ids(self, value: Optional[Set[RecIdType]]) -> None:
        """Set the list of checked items."""
        reset_model = False
        if value is None:
            if self._checked is None:
                # No change (None to None)
                return

            # Changing from checked mode to non-checked mode.
            self._checked = None
            reset_model = True
        else:
            value = set(value)
            if self._checked is None:
                # Changing from non-checked mode to checked mode.
                self._checked = set()
                reset_model = True
            elif self._checked == value:
                return
            else:
                # Changing the checked items.
                changed = self._checked.symmetric_difference(value)
                self._checked = value
                for db_id in changed:
                    row = self._db_to_row.get(db_id, None)
                    if row is None:
                        reset_model = True
                    else:
                        # The row is the index of the item in the cache
                        # without the top cache.
                        row = row + len(self.top_cache)
                        self.dataChanged.emit(
                            self.createIndex(row, 0),
                            self.createIndex(row, len(self.column_fields) - 1),
                        )

        if reset_model:
            self.reset_model()

    def ensure_stubs(self, new_total: int) -> None:
        """We populate the cache with stubs so that the model can be used."""
        self.cache.set_size(new_total)

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
        if start + count > self._total_count:
            count = self._total_count - start
        if count <= 0:
            return
        req = self.new_request(start, count)
        if not self.trim_request(req):
            # There are already requests in progress that overlap with this one.
            return

        # Save to internal list.
        self.add_request(req)

        # Allow some time to accumulate requests before executing them.
        if self._wait_before_request > 0:
            QTimer.singleShot(
                self._wait_before_request, lambda: self.execute_request(req)
            )
        else:
            self.execute_request(req)

    def execute_request(self, req: "RecordRequest") -> None:
        """Delayed execution of the request.

        The function is called by the QTimer after a short delay to allow
        multiple requests to be accumulated. The function pushes the
        request to the worker thread and emits the `requestIssued` signal.
        """
        # Prevent merges into this request.
        req.pushed = True

        self.ctx.push_work(
            statement=self.sorted_selection.offset(req.start).limit(req.count),
            callback=self._load_items,
            req_id=(id(self), req),
        )

        # Inform interested parties that a request has been issued.
        try:
            self.requestIssued.emit(
                req.uniq_id, req.start, req.count, len(self.requests)
            )
        except RuntimeError:
            logger.error("RuntimeError in requestIssued signal", exc_info=True)

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
                record = self.cache[i]
                record.db_id = -1
                record.error = True
            logger.debug(
                "Request %d generated an error: %s", work.req_id, work.error
            )
            self.requestError.emit(
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
                str(work.error),
            )
        else:
            loaded_update = 0
            for i in range(req.start, req.start + req.count):
                record = self.cache[i]
                if not record.loaded:
                    loaded_update = loaded_update + 1
                try:
                    self.db_item_to_record(work.result[i - req.start], record)
                except Exception as e:
                    logger.error(
                        "Error converting item %d to record: %s",
                        i - req.start,
                        e,
                        exc_info=e,
                    )
                    record.error = True

                # The row is the index of the item in the cache
                # without the top cache.
                self._db_to_row[record.db_id] = i
            self.requestCompleted.emit(
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
            )
            self.loaded_count = self._loaded_count + loaded_update
        self.dataChanged.emit(
            self.createIndex(req.start, 0),
            self.createIndex(
                req.start + req.count - 1, len(self.column_fields) - 1
            ),
        )

    def db_item_to_record(
        self, item: DBM, record: Optional["QtRecord"] = None
    ) -> "QtRecord":
        """Convert a database item to a record.

        The function asks the fields to compute the values for each role of the
        corresponding column.

        NOTE: As this method is also used from outside the model it is important
        for it to remain pure. It should not change the state of the model or
        the record.

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
            try:
                result.values[f_index] = fld.values(item)
            except Exception as e:
                logger.error(
                    "Error converting item %d to record using field '%s': %s",
                    f_index,
                    fld.name,
                    e,
                )

                import traceback

                logger.error(traceback.format_exc())

                result.values[f_index] = {
                    Qt.ItemDataRole.DisplayRole: str(e),
                    Qt.ItemDataRole.EditRole: str(e),
                }
                result.error = True
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
        pks = self.get_primary_columns()
        if isinstance(pks, (list, tuple)):
            pks = tuple_(*pks)
        return pks.in_(id_list)

    def item_by_id_conditions(self, rec_id: RecIdType) -> List[Any]:
        """Return the conditions that filter by ID.

        Args:
            rec_id: The ID of the item to filter by.
        """
        primary_cols = []
        for f in self.fields:
            if f.primary:
                primary_cols.append(getattr(self.db_model, f.name))
        assert len(primary_cols) > 0, "No primary columns found"

        conditions = []
        if len(primary_cols) == 1:
            assert isinstance(rec_id, int), (
                "ID is not an int for a single primary key model. "
                f"Model: {self.db_model.__name__} "
                f"ID: {rec_id}/{rec_id.__class__.__name__}"
            )
            conditions.append(primary_cols[0] == rec_id)
        else:
            assert isinstance(rec_id, (list, tuple)), (
                "ID is not a tuple for a composite primary key model. "
                f"Model: {self.db_model.__name__} "
                f"ID: {rec_id}/{rec_id.__class__.__name__}"
            )

            assert len(primary_cols) == len(rec_id), (
                "ID tuple does not match the number of primary keys. "
                f"Model: {self.db_model.__name__} "
                f"ID: {rec_id}/{rec_id.__class__.__name__}"
            )

            for col, value in zip(primary_cols, rec_id):
                conditions.append(col == value)

        return conditions

    @contextmanager
    def get_one_db_item_by_id(
        self, rec_id: RecIdType
    ) -> Generator[Optional[DBM], None, None]:
        """Return the database item with the given ID.

        This is a convenience function that uses the primary key columns to
        load the item from the database. The model does not use this directly.

        Args:
            rec_id: The ID of the item to return.

        Returns:
            The database item with the given ID or None if not found.
        """
        if hasattr(rec_id.__class__, "metadata"):
            rec_id = cast(RecIdType, self.get_db_item_id(cast(Any, rec_id)))
        conditions = self.item_by_id_conditions(rec_id)
        with self.ctx.same_session() as session:
            selector = select(self.db_model).where(*conditions)
            try:
                yield session.scalar(selector)
            except SQLAlchemyError as e:
                logger.error(
                    "SqlAlchemy error '%s' getting item by ID '%s' in QtModel "
                    "'%s' with statement:\n%s",
                    e,
                    rec_id,
                    self.name,
                    sqlparse.format(
                        str(selector), reindent=True, keyword_case="upper"
                    ),
                )
                raise e

    def get_db_items_by_id(
        self, id_list: List[RecIdType]
    ) -> List[Union[None, DBM]]:
        """Return the database items with the given IDs.

        This is a convenience function that uses the primary key columns to
        load the item from the database. The model does not use this directly.

        Args:
            id_list: The list of IDs to retrieve. If the model has a single
                primary key, the list should consist of single values. If the
                model has a composite primary key, the list should consist
                of tuples of values (the order of the items in the tuple
                should be the same as the order of the primary columns in
                the `self.fields` array).

        Returns:
            The database items with the given ID or None if not found. The
            order of the items is the same as the order of the IDs in the
            `id_list` list. None is returned for IDs that are not found.
        """
        with self.ctx.same_session() as session:
            results = session.scalars(
                self.selection.where(self.get_id_filter(id_list))
            )
            r_map = {self.get_db_item_id(a): a for a in results}
            return [r_map.get(cast(Any, i)) for i in id_list]

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
        result.filters = self._filters
        result.sort_by = self.sort_by
        result.top_cache = self.top_cache
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

    def data_record(self, row: int) -> Optional["QtRecord"]:
        """Get the data for a particular row.

        Args:
            row: The row to get the data for. If the index is outside the
                valid interval, the function returns None.

        Returns:
            The data for the row.
        """
        if row < 0:
            return None
        if row < len(self.top_cache):
            return self.top_cache[row]
        row = row - len(self.top_cache)
        if row < len(self.cache):
            return self.cache[row]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        if row < len(self.top_cache):
            item: "QtRecord" = self.top_cache[row]
            return item.data(index.column(), cast(Qt.ItemDataRole, role))
        row = row - len(self.top_cache)

        item = self.cache[row]
        if role == Qt.ItemDataRole.DisplayRole and not item.loaded:
            self.request_items(row, self.batch_size)

        if role == Qt.ItemDataRole.CheckStateRole:
            # Checkboxes are only shown if the model is in checkable mode
            # and if the item is loaded.
            if not item.loaded or self._checked is None:
                return None

            return (
                Qt.CheckState.Checked
                if item.db_id in self._checked
                else Qt.CheckState.Unchecked
            )

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

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._checked is not None:
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return cast(Qt.ItemFlags, base)

    def setData(
        self, index: QModelIndex, value: Any, role=Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid():
            return False

        # Get the item. If it is not loaded, we cannot set the data.
        row = index.row()
        if row < len(self.top_cache):
            # We do not allow editing of top cache items.
            return False

        row = row - len(self.top_cache)
        record: "QtRecord" = self.cache[row]
        if not record.loaded:
            return False

        # Are we in checkable mode?
        if self._checked is not None:
            if role == Qt.ItemDataRole.CheckStateRole:
                if value == Qt.CheckState.Checked:
                    self._checked.add(record.db_id)
                else:
                    self._checked.discard(record.db_id)
                self.dataChanged.emit(
                    index, index, [Qt.ItemDataRole.CheckStateRole]
                )
                self.checkedChanged.emit()
                return True

        # TODO
        return False

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """Sort the model by the given column and order.

        The function clears the cache and resets the total count.
        """
        try:
            self.sort_by = [
                (
                    self.column_fields[column].name,
                    "asc" if order == Qt.SortOrder.AscendingOrder else "desc",
                )
            ]
            self.reset_model()
        except Exception as e:
            logger.error("Error sorting model: %s", e, exc_info=True)

    def apply_filter(self, filter: Union[FilterType, None]) -> None:
        """Sort the model by the given column and order.

        The function clears the cache and resets the total count.
        """
        previous = self._filters
        try:
            # Handle None cases
            if filter is None and previous is None:
                return
            if filter is None or previous is None:
                # Continue to reset model
                pass
            else:
                # Deep compare the filter structures
                if compare_filters(filter, previous):
                    return
        except Exception as e:
            logger.error("Error applying filter: %s", e, exc_info=True)

        # Make sure that the filter is valid.
        if filter:
            validate_result = validate_filter(filter)
            if validate_result:
                raise ValueError(
                    f"Invalid filters: {validate_result[0]} "
                    f"{'->'.join(validate_result[1:])}"
                )

        self._filters = filter if filter else []
        logger.debug("Changing filters from %s to %s", previous, self._filters)
        self.reset_model()

    def text_to_filter(
        self,
        text: str,
        exact: Optional[bool] = False,
        limit: Optional[str] = None,
    ) -> FilterType:
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.

        Args:
            text: The text to convert to a filter.
            exact: If True, the text will not be modified. If false,
                if the text includes at least a '*', all occurrences of '*'
                will be replaced by '%'. If the text includes no '%'
                then the text is surrounded by '%' characters. Spaces are
                always replaced by '%' characters if exact is False.
            limit: If False the computed filter is applied to all searchable
                fields. If True the computed filter is applied to the given
                field.

        Returns:
            The filter.
        """
        if len(text) == 0:
            return []

        if not exact:
            text = text.replace(" ", "%")
            if "*" not in text:
                if "%" not in text:
                    text = f"%{text}%"
            else:
                text = text.replace("*", "%")

        ua_text = unidecode(text)

        filters = [  # type: ignore
            {  # type: ignore
                "fld": f.name,  # type: ignore
                "op": "ilike",  # type: ignore
                "vl": text,  # type: ignore
            }  # type: ignore
            for f in self.simple_search_fields  # type: ignore
            if limit is None or f.name == limit
        ]  # type: ignore
        if ua_text != text:
            filters = filters + [
                {  # type: ignore
                    "fld": f.name,  # type: ignore
                    "op": "ilike",  # type: ignore
                    "vl": ua_text,  # type: ignore
                }  # type: ignore
                for f in self.simple_search_fields  # type: ignore
                if limit is None or f.name == limit
            ]
        return [  # type: ignore
            "OR",  # type: ignore
            filters,  # type: ignore
        ]  # type: ignore

    def apply_simple_search(
        self,
        text: str,
        exact: Optional[bool] = False,
        limit: Optional[str] = None,
    ) -> None:
        """Apply a simple search to the model.

        The search is applied to the fields in the `simple_search_fields`
        property.

        If exact is false you can use the `*` or `%` character to match any
        number of characters. If neither is present, the text will be
        surrounded by `%` characters. Spaces are always replaced by `%`
        characters.

        If exact is true, the text is searched for as is, without any
        changes. In this case only `%` is allowed.

        Args:
            text: The text to search for.
            exact: If True, the search will be exact.
            limit: If present, the search will be limited to the given field.
        """
        filters = self.text_to_filter(text, exact, limit)
        self.apply_filter(filters)  # type: ignore

    def checked_rows(self) -> Optional[List[RecIdType]]:
        """Return the list of checked items."""
        if self._checked is None:
            return None
        return [
            self._db_to_row[db_id] + len(self.top_cache)
            for db_id in self._checked
        ]

    def set_prioritized_ids(self, ids: Optional[List[RecIdType]]) -> None:
        """Set the prioritized IDs and reset the model."""
        if self.prioritized_ids == ids:
            return
        self.prioritized_ids = ids
        self.reset_model()
