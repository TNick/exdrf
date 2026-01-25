import logging
import uuid
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf.filter import (
    FieldFilter,
    FilterType,
    SearchType,
    compare_filters,
    create_multi_field_or_filter,
    extract_field_filters,
    validate_filter,
)
from exdrf_al.utils import DelChoice
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QTimer, pyqtSignal
from sqlalchemy import case, delete, func, select, tuple_, update
from sqlalchemy.exc import SQLAlchemyError
from unidecode import unidecode

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.models.cache import SparseList
from exdrf_qt.models.field_list import FieldsList
from exdrf_qt.models.record import QtRecord
from exdrf_qt.models.requests import RecordRequestManager
from exdrf_qt.models.selector import Selector
from exdrf_qt.worker import Work

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject  # noqa: F401
    from sqlalchemy import Select  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.models.requests import RecordRequest  # noqa: F401


DEFAULT_CHUNK_SIZE = 24
MODEL_LOG_LEVEL = 1
EDITABLE_LOG_LEVEL = MODEL_LOG_LEVEL
DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


@define(slots=True)
class ModelWork(Work):
    """Async work for QtModel.

    Attributes:
        model: The model that is performing the work.
        cancelled: If True, the work is cancelled.
    """

    model: "QtModel" = field(kw_only=True, repr=False)
    cancelled: bool = field(default=False, init=False)

    def perform(self, session: "Session") -> None:
        """Perform the work."""
        self.result = []
        if self.cancelled:
            return

        if self.use_unique:
            tmp_result = list(session.scalars(self.statement).unique().all())
        else:
            tmp_result = list(session.scalars(self.statement))

        for i, db_rec in enumerate(tmp_result):
            qt_rec = QtRecord(model=self.model)
            try:
                self.model.db_item_to_record(db_rec, qt_rec)
            except Exception as e:
                logger.error(
                    "M: %s Error converting item %d to record: %s",
                    self.model.name,
                    i,
                    e,
                    exc_info=e,
                )
                qt_rec.error = True
            self.result.append(qt_rec)

        session.expunge_all()

    def get_category(self) -> str:
        """The category for the priority queue.

        The default implementation returns the ID of the model, meaning
        that each individual model instance is a separate class.

        We want to process the newest requests first for the same model.
        """
        return str(id(self.model))

    def get_priority(self) -> int:
        """The priority for the priority queue among its peers in same class."""
        return self.req_id[1].priority


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
        _total_count: The total number of items in the database selection.
            This does not include the number of items in the top cache.
        _loaded_count: The number of items loaded from the database. This does
            not include the number of items in the top cache. Compare to
            _total_count to see if there are more items to load.
        _checked: A list of database IDs that are checked. If this list is None
            (default) the model shows no checkboxes. If the record does not
            have a database ID, the ID of the record object itself is used.
        _db_to_row: A dictionary that maps database IDs to row indices in the
            cache (does not include top_cache items).
        _wait_before_request: The number of milliseconds to wait before issuing
            a request for items.
        _soft_delete_field_name: The name of the field in the model that
            indicates if a record is normally hidden (soft delete). This only
            indicates the name of the field to be searched in the database
            model; the value here should not be taken to indicate that
            the database model actually has this field. Use the
            has_soft_delete_field property to check if the model has a soft
            delete field and get_soft_delete_field() to get the field.
            To prevent the model from applying deletion filtering you
            can set this value to None.
        _del_choice: The choice of deleted records to include in the model.
            ACTIVE means only records that are not marked as deleted will be
            included. DELETED means only records that are marked as deleted
            will be included. ALL means all records will be included. The
            default is ACTIVE. This option changes the filter applied to the
            model by the Selector but only if the get_soft_delete_field()
            returns a valid field.
        _no_dia_map: A dictionary that maps field names to fields that are
            storing the value of the field without diacritics. This only
            applies to string fields and is used whenever we need to create
            filters. If the name of a local column is found in this
            dictionary an OR filter is created with the original value and the
            value without diacritics.
        _fixed_filters: If present, will be AND-ed together with the
            filters attribute before computing the filtered selector.
            The intended use is to apply some fixed filters that are not
            user-editable.

    Signals:
        totalCountChanged: Emitted when a change in the total count is
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
    _fixed_filters: Optional[FilterType] = None
    top_cache: List["QtRecord"]
    cache: SparseList["QtRecord"]
    batch_size: int
    _total_count: int
    _loaded_count: int
    _checked: Optional[Set[RecIdType]] = None
    _db_to_row: Dict[RecIdType, int]
    _wait_before_request: int
    _soft_delete_field_name: Union[str, None]
    _del_choice: DelChoice
    _save_settings: bool
    _no_dia_map: Dict[str, str]
    allow_top_cache_edit: bool

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
        soft_delete_field_name: Union[str, None] = "deleted",
        del_choice: DelChoice = DelChoice.ACTIVE,
        load_settings: bool = True,
        save_settings: bool = True,
        no_dia_map: Optional[Dict[str, str]] = None,
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
            wait_before_request: The number of milliseconds to wait before
                issuing a request for items.
            soft_delete_field_name: The name of the field in the model that
                indicates if a record is normally hidden (soft delete).
            del_choice: The choice of deleted records to include in the model.
                ACTIVE means only records that are not marked as deleted will
                be included. DELETED means only records that are marked as
                deleted will be included. ALL means all records will be
                included. The default is ACTIVE. This option changes the
                filter applied to the model by the Selector but only if the
                get_soft_delete_field() returns a valid field.
            load_settings: If True, the settings (like what field to search when
                simple searching) are loaded from the context and applied to
                the model.
            save_settings: If True, when some of the setting (like what field
                to search when simple searching) are changed, the new settings
                are saved to the context.
            no_dia_map: A dictionary that maps field names to fields that are
                storing the value of the field without diacritics. This only
                applies to string fields.
        """
        # super().__init__(parent=parent)
        QAbstractItemModel.__init__(self, parent=parent)
        RecordRequestManager.__init__(self)
        FieldsList.__init__(self)
        QtUseContext.__init__(self)

        self.ctx = ctx
        self.top_cache = []
        self._no_dia_map = no_dia_map or {}
        self._wait_before_request = wait_before_request
        self._db_to_row = {}
        self._soft_delete_field_name = soft_delete_field_name
        self._del_choice = del_choice
        self.allow_top_cache_edit = False
        self.db_model = db_model
        self.fields = cast(Any, fields if fields is not None else [])
        self.selection = (
            selection if selection is not None else select(db_model)
        )
        self.base_selection = self.selection
        self.sort_by = []
        self.prioritized_ids = None
        self._filters = []
        self._save_settings = save_settings
        self.batch_size = batch_size
        self.cache = SparseList(lambda: QtRecord(model=self, db_id=-1))

        self._total_count = -1
        self._loaded_count = 0

        if load_settings:
            self.load_settings()

        # Compute the total count.
        self._total_count = (
            -1 if prevent_total_count else self.recalculate_total_count()
        )

    @property
    def partially_initialized(self) -> bool:
        """Return True if the model is partially initialized."""
        return self._total_count == -1

    def reset_model(self, clear_top_cache: bool = False) -> None:
        """Reset the model.

        The function clears the cache and resets the total count.

        Args:
            clear_top_cache (bool): Whether to clear the top cache.
        """
        logger.log(MODEL_LOG_LEVEL, "M: %s Resetting model...", self.name)
        self.beginResetModel()

        # Clear the top cache if requested.
        if clear_top_cache:
            self.top_cache.clear()

        # Clear any pending requests so late callbacks from previous state are
        # ignored after the cache is reset.
        for req in self.requests.values():
            req.cancelled = True
        self.requests.clear()
        # self.uniq_gen = 0

        self.cache.clear()
        self._db_to_row = {}
        self._total_count = -1
        self._loaded_count = 0
        self.recalculate_total_count()
        self.endResetModel()
        logger.log(MODEL_LOG_LEVEL, "M: %s Model reset complete.", self.name)

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
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Total count recalculated: %d",
                self.name,
                count,
            )
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
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Setting total count to %d",
                self.name,
                value,
            )
            self.ensure_stubs(value)
            self._total_count = value
            true_value = value + len(self.top_cache)
            self.totalCountChanged.emit(true_value)
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Total count set to %d (true value: %d)",
                self.name,
                value,
                true_value,
            )

    @property
    def loaded_count(self) -> int:
        """Return the number of items loaded from the database.

        This value does NOT include the number of items in the top cache.
        """
        return self._loaded_count

    @loaded_count.setter
    def loaded_count(self, value: int) -> None:
        """Set the number of items loaded from the database.

        Also emits the `loadedCountChanged` signal if the value changes.

        The argument should not include the number of items in the top cache.
        """
        if value != self._loaded_count:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Setting loaded count to %d",
                self.name,
                value,
            )
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
        logger.log(
            MODEL_LOG_LEVEL, "M: %s Setting filters to %s", self.name, value
        )
        validate_result = validate_filter(value)
        if validate_result:
            error = (
                f"Invalid filters: {validate_result[0]} "
                f"{'->'.join(validate_result[1:])}"
            )
            logger.error("M: %s %s", self.name, error)
            raise ValueError(error)
        self._filters = value
        logger.log(MODEL_LOG_LEVEL, "M: %s Filters set to %s", self.name, value)

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
                .from_qt_model(
                    self,
                    dialect=(
                        self.ctx.engine.dialect.name
                        if self.ctx.engine is not None
                        else None
                    ),
                )  # type: ignore
                .run(
                    self._filters
                    if self._fixed_filters is None
                    else [
                        (
                            self._fixed_filters
                            if isinstance(self._fixed_filters, list)
                            else [self._fixed_filters]
                        ),
                        (
                            self._filters
                            if isinstance(self._filters, list)
                            else [self._filters]
                        ),
                    ]  # type: ignore
                )
            )
        except Exception:
            logger.error(
                "M: %s Error while computing the filtered selection",
                self.name,
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
        try:
            order_by_clauses = []

            if self.prioritized_ids:
                primary_cols = self.get_primary_columns()
                if isinstance(primary_cols, (list, tuple)):
                    primary_cols = tuple_(*primary_cols)
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
                                "M: %s Sorting field %s not found",
                                self.name,
                                field_key,
                            )
                            continue
                        if not fld.sortable:
                            logger.warning(
                                "M: %s Sorting field %s not sortable",
                                self.name,
                                field_key,
                            )
                            continue
                        tmp = fld.apply_sorting(order == "asc")
                        if tmp is not None:
                            order_by_clauses.append(tmp)

                except Exception:
                    logger.error(
                        "M: %s Error applying sorting", self.name, exc_info=True
                    )
                    return self.filtered_selection

            if order_by_clauses:
                return self.filtered_selection.order_by(*order_by_clauses)
        except Exception:
            logger.error(
                "M: %s Error while computing the sorted selection",
                self.name,
                exc_info=True,
            )
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
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Setting checked ids to %s...",
            self.name,
            value,
        )
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
                self._checked = value
                reset_model = True
            elif self._checked == value:
                return
            else:
                # Changing the checked items.
                changed = self._checked.symmetric_difference(value)
                self._checked = value
                for record_id in changed:
                    row = self._db_to_row.get(record_id, None)
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

        # Respect the partially-initialized state.
        if reset_model and self._total_count != -1:
            self.clear_cached_flags()
            self.reset_model()

        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Checked items were set. Reset model: %s.",
            self.name,
            reset_model,
        )

    def get_soft_delete_field(self) -> Union[Any, None]:
        """Return the field in the model that indicates if a record is
        normally hidden (soft delete).

        The default implementation simply looks for a field named "deleted".

        Returns None if the model has no soft delete field of the model
        attribute from the database model.
        """
        assert self.db_model is not None
        if not self._soft_delete_field_name:
            return None
        return getattr(self.db_model, self._soft_delete_field_name, None)

    def change_soft_delete_value(self, db_record: DBM, value: bool) -> None:
        """Change the value of the soft delete field for the given database
        record.
        """
        if not self._soft_delete_field_name:
            raise NotImplementedError(
                f"Soft delete not available in model {self.name}."
            )
        setattr(db_record, self._soft_delete_field_name, value)

    @property
    def has_soft_delete_field(self) -> bool:
        """Return True if the model has a soft delete field."""
        return self.get_soft_delete_field() is not None

    @property
    def del_choice(self) -> DelChoice:
        """Return the choice of deleted records to include in the model."""
        return self._del_choice

    @del_choice.setter
    def del_choice(self, value: DelChoice) -> None:
        """Set the choice of deleted records to include in the model."""
        if value == self._del_choice:
            return
        self._del_choice = value

        # Respect the partially-initialized state.
        if self._total_count == -1:
            return

        self.reset_model()

    def ensure_stubs(self, new_total: int) -> None:
        """Populate the cache with stubs so that the model can be used.

        Sets the cache size to the new total count. If no items are currently
        loaded, requests an initial batch of items from the database.

        Args:
            new_total: The new total count to set for the cache size.
        """
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Ensuring stubs for %d items...",
            self.name,
            new_total,
        )
        self.cache.set_size(new_total)

        # If the cache is empty, we post a request for items.
        # Note: This is called from total_count setter BEFORE _total_count
        # is updated.
        # We temporarily set _total_count so request_items() works correctly.
        if self._loaded_count == 0 and new_total > 0:
            old_total = self._total_count
            try:
                self._total_count = new_total
                count = min(self.batch_size * 8, new_total)
                if count > 0:
                    self.request_items(0, count)
                logger.log(
                    MODEL_LOG_LEVEL,
                    "M: %s Requested %d items.",
                    self.name,
                    count,
                )
            finally:
                # Restore old value - it will be set correctly by the setter
                self._total_count = old_total

    def request_items(self, start: int, count: int) -> None:
        """Request items from the database.

        The function loads items from the database and stores them in the
        cache.

        Args:
            start: The starting index of the items to load. The index used here
                should not include the offset of the top cache (the first
                database item is at index 0 always).
            count: The number of items to load.
        """
        if start + count > self._total_count:
            count = self._total_count - start
        if count <= 0:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Requested %d items, but count is 0 or negative.",
                self.name,
                start,
                count,
            )
            return
        req = self.new_request(start, count)
        if not self.trim_request(req):
            # There are already requests in progress that overlap with this one.
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request %d-%d overlaps with existing requests.",
                self.name,
                start,
                start + count,
            )
            return

        # Save to internal list.
        self.add_request(req)

        # Allow some time to accumulate requests before executing them.
        if self._wait_before_request > 0:
            QTimer.singleShot(
                self._wait_before_request, lambda: self.execute_request(req)
            )
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Waiting %d milliseconds before executing request %s.",
                self.name,
                self._wait_before_request,
                req.uniq_id,
            )
        else:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Executing request %s immediately.",
                self.name,
                req.uniq_id,
            )
            self.execute_request(req)

    def execute_request(self, req: "RecordRequest") -> None:
        """Delayed execution of the request.

        The function is called by the QTimer after a short delay to allow
        multiple requests to be accumulated. The function pushes the
        request to the worker thread and emits the `requestIssued` signal.
        """
        if req.cancelled:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request %s was cancelled",
                self.name,
                req.uniq_id,
            )
            return
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Executing request %s.",
            self.name,
            req.uniq_id,
        )

        # Prevent merges into this request.
        req.pushed = True
        req.work = ModelWork(
            model=self,
            statement=(
                self.sorted_selection.offset(req.start).limit(req.count)
            ),
            callback=self._load_items,  # type: ignore
            req_id=(id(self), req),
        )

        self.ctx.push_work(req.work)

        # Inform interested parties that a request has been issued.
        try:
            if self._is_deleted():
                logger.log(
                    MODEL_LOG_LEVEL,
                    "M: %s Request %s ignored (model deleted).",
                    self.name,
                    req.uniq_id,
                )
                return
            self.requestIssued.emit(
                req.uniq_id, req.start, req.count, len(self.requests)
            )
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request %s issued. Start: %d, Count: %d, Requests: %d.",
                self.name,
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
            )
        except RuntimeError:
            logger.error(
                "M: %s RuntimeError in requestIssued signal",
                self.name,
                exc_info=True,
            )

    def _load_items(self, work: "ModelWork") -> None:
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Loading items for request %s.",
            self.name,
            work.req_id,
        )
        if self._is_deleted():
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Ignoring load (model deleted).",
                self.name,
            )
            return

        # Locate the request in the list of requests.
        # work.req_id is a tuple (id(self), req), so work.req_id[1] is the
        # request object
        if isinstance(work.req_id, tuple) and len(work.req_id) >= 2:
            req = self.requests.pop(work.req_id[1].uniq_id, None)
        else:
            # Fallback for different req_id formats
            req = None

        if work.cancelled:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request was %s cancelled",
                self.name,
                work.req_id,
            )
            return

        if req is None:
            logger.error(
                "M: %s Request %s not found in requests", self.name, work.req_id
            )
            return

        # If this request generated an error mark those requests as such.
        available = 0
        if work.error:
            for i in range(req.start, req.start + req.count):
                record = self.cache[i]
                record.db_id = -1
                record.error = True
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request %d generated an error: %s",
                self.name,
                work.req_id,
                work.error,
            )
            self.requestError.emit(
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
                str(work.error),
            )
        else:

            # Clamp the number of items to what we actually received to avoid
            # indexing past the result list when the backend returns fewer rows
            # than requested (e.g. concurrent resets or changes in selection).
            available = min(
                req.count,
                len(work.result),
                max(0, len(self.cache) - req.start),
            )
            if available < req.count:
                logger.log(
                    MODEL_LOG_LEVEL,
                    "M: %s Request %s returned fewer rows than requested "
                    "(asked=%d, got=%d, len(cache)=%d).",
                    self.name,
                    req.uniq_id,
                    req.count,
                    len(work.result),
                    len(self.cache),
                )

            loaded_update = 0
            for i in range(req.start, req.start + available):
                old_record = cast("QtRecord", self.cache[i])
                new_record = cast("QtRecord", work.result[i - req.start])
                if not old_record.loaded:
                    loaded_update = loaded_update + 1
                self.cache[i] = new_record
                new_record.clear_cached_flags()

                # The row is the index of the item in the cache
                # without the top cache.
                self._db_to_row[new_record.db_id] = i
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Request %s completed. "
                "Start: %d, Count: %d, Requests: %d.",
                self.name,
                req.uniq_id,
                req.start,
                req.count,
                len(self.requests),
            )
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
                req.start + available - 1, len(self.column_fields) - 1
            ),
        )

    def _is_deleted(self) -> bool:
        """Return True if the Qt object was deleted."""
        try:
            from PyQt5 import sip

            return sip.isdeleted(self)
        except Exception:
            return False

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
                    "M: %s Error converting item %d to record "
                    "using field '%s': %s",
                    self.name,
                    f_index,
                    fld.name,
                    e,
                )

                import traceback

                logger.error("M: %s %s", self.name, traceback.format_exc())

                result.values[f_index] = {
                    Qt.ItemDataRole.DisplayRole: str(e),
                    Qt.ItemDataRole.EditRole: str(e),
                }
                result.error = True

        # Deal with soft delete.
        del_field = self.get_soft_delete_field()
        if del_field is not None:
            del_value = getattr(item, del_field.name)
            result.soft_del = bool(del_value)

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
                import sqlparse

                logger.error(
                    "M: %s SqlAlchemy error '%s' getting item by ID '%s' "
                    "with statement:\n%s",
                    self.name,
                    e,
                    rec_id,
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
        logger.log(MODEL_LOG_LEVEL, "M: %s Cloning model...", self.name)
        result = self.__class__(
            ctx=self.ctx,
            db_model=self.db_model,
            selection=self.base_selection,
            prevent_total_count=True,
        )
        # Set filters and sort - this will trigger reset_model() if filters
        # change
        # But we want to avoid that, so set _filters directly and sort_by
        result._filters = self._filters
        result.sort_by = self.sort_by
        # Don't copy top_cache - cloned model should start fresh
        result.top_cache = []
        result._loaded_count = 0
        # Update the selection to match the sorted/filtered query BEFORE
        # recalculating total count, so ensure_stubs() uses the correct query
        # Note: base_selection should remain the unfiltered base, selection
        # will be the filtered/sorted version
        # Ensure base_selection is set correctly first (should already be set
        # in constructor, but be explicit)
        result.base_selection = self.base_selection
        # Compute the sorted selection - this will use the filters and sort_by
        # we just set, and will compute from base_selection
        result.selection = result.sorted_selection
        # Recalculate total count, which will trigger ensure_stubs()
        # and request initial items using the correct sorted/filtered selection
        result.recalculate_total_count()
        logger.log(MODEL_LOG_LEVEL, "M: %s Model cloned.", self.name)
        return result

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows under the given parent.

        Args:
            parent: The parent index. If invalid, returns the total count.
                Items have no children, so for valid parents returns 0.

        Returns:
            The number of rows (total count for root, 0 for items).
        """
        if not parent.isValid():
            return self.total_count

        # Items have no children.
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns under the given parent.

        Args:
            parent: The parent index (unused, items have no children).

        Returns:
            The number of columns (number of column fields).
        """
        return len(self.column_fields)

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Return whether the parent has any children.

        Args:
            parent: The parent index. If invalid, returns True (root has
                children). Items have no children, so for valid parents
                returns False.

        Returns:
            True if the parent has children, False otherwise.
        """
        if not parent.isValid():
            return True

        # Items have no children.
        return False

    def parent(self, child: QModelIndex = QModelIndex()) -> QModelIndex:
        """Return the parent of the given child.

        Args:
            child: The child index (unused, items have no parent).

        Returns:
            An invalid QModelIndex, as items have no parent.
        """
        # Items have no children.
        return QModelIndex()

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        """Return the index of the item at the given row and column.

        Args:
            row: The row number.
            column: The column number.
            parent: The parent index. Items have no parent, so valid parents
                return an invalid index.

        Returns:
            A valid QModelIndex for root items, or an invalid QModelIndex
            if the indices are out of range or parent is valid.
        """
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

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Return the data for the given index and role.

        For DisplayRole, if the item is not loaded, requests items from the
        database. For CheckStateRole, returns the checked state if the model
        is in checkable mode and the item is loaded.

        Args:
            index: The model index to get data for.
            role: The data role (DisplayRole, CheckStateRole, etc.).

        Returns:
            The data for the given index and role, or None if invalid or
            not available.
        """
        if not index.isValid():
            return None

        row = index.row()
        if row < len(self.top_cache):
            item: "QtRecord" = self.top_cache[row]
            return item.data(index.column(), cast(Qt.ItemDataRole, role))
        row = row - len(self.top_cache)

        item = self.cache[row]
        if (
            role == Qt.ItemDataRole.DisplayRole
            and not item.loaded
            and not item.error
        ):
            self.request_items(
                max(0, row - self.batch_size), self.batch_size * 2
            )

        if role == Qt.ItemDataRole.CheckStateRole:
            # Checkboxes are only shown if the model is in checkable mode
            # and if the item is loaded.
            if not item.loaded or self._checked is None:
                return None

            record_id = id(item) if item.db_id is None else item.db_id
            return (
                Qt.CheckState.Checked
                if record_id in self._checked
                else Qt.CheckState.Unchecked
            )

        return item.data(index.column(), cast(Qt.ItemDataRole, role))

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = 0
    ) -> Any:
        """Return the header data for the given section, orientation, and role.

        For horizontal headers with DisplayRole, returns the field title.
        For vertical headers with DisplayRole, returns the database ID.
        For TextAlignmentRole, returns centered alignment.

        Args:
            section: The section (column for horizontal, row for vertical).
            orientation: The header orientation (Horizontal or Vertical).
            role: The data role (DisplayRole, TextAlignmentRole, etc.).

        Returns:
            The header data for the given parameters, or None if not available.
        """
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return the item flags for the given index.

        Args:
            index: The model index to get flags for.

        Returns:
            Item flags (Enabled, Selectable, and optionally UserCheckable
            if in checkable mode). Returns NoItemFlags for invalid indices.
        """
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)

        row = index.row()
        column = index.column()
        record = self.data_record(row)

        cached = record.get_flags(column) if record is not None else None
        if cached is not None:
            return cached

        value = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._checked is not None and index.column() == 0:
            value |= Qt.ItemFlag.ItemIsUserCheckable
        if self._is_index_editable(record, row, column):
            value |= Qt.ItemFlag.ItemIsEditable

        if record is not None:
            record.set_flags(column, value)

        return cast(Qt.ItemFlags, value)

    def clear_cached_flags(self) -> None:
        """Clear the cached flags."""
        for record in self.cache:
            record.clear_cached_flags()
        for record in self.top_cache:
            record.clear_cached_flags()

    def _is_index_editable(
        self, record: Optional["QtRecord"], row: int, column: int
    ) -> bool:
        """Return True if the given index is editable.

        Args:
            index: The model index to check.

        Returns:
            True if the index is editable, False otherwise.
        """
        if record is None:
            logger.log(
                EDITABLE_LOG_LEVEL,
                "M: %s Refusing to edit item at row %d; no record",
                self.name,
                row,
            )
            return False

        # The top level items are those outside the normal flow, not managed
        # directly by the model.
        if row < len(self.top_cache):

            # The editing of top level items can be disabled for the
            # whole model.
            if not self.allow_top_cache_edit:
                return False

            # No record or not loaded and/or error while loading.
            if not record.loaded or record.error:
                logger.log(
                    EDITABLE_LOG_LEVEL,
                    "M: %s Refusing to edit item %s at row %d; "
                    "loaded: %s, error: %s",
                    self.name,
                    record.db_id,
                    row,
                    record.loaded,
                    record.error,
                )
                return False

            # The column must be within the range of the model's fields.
            if column >= len(self.column_fields):
                logger.log(
                    EDITABLE_LOG_LEVEL,
                    "M: %s Refusing to edit item %s at row %d; "
                    "column out of range: %d (max %d)",
                    self.name,
                    record.db_id,
                    row,
                    column,
                    len(self.column_fields) - 1,
                )
                return False

            # Record allows it, let the column decide.
            return self.column_fields[column].is_editable()

        # Not loaded and/or error while loading.
        if not record.loaded or record.error:
            logger.log(
                EDITABLE_LOG_LEVEL,
                "M: %s Refusing to edit item %s at row %d; "
                "loaded: %s, error: %s",
                self.name,
                record.db_id,
                row,
                record.loaded,
                record.error,
            )
            return False

        # The column must be within the range of the model's fields.
        if column >= len(self.column_fields):
            logger.log(
                EDITABLE_LOG_LEVEL,
                "M: %s Refusing to edit item %s at row %d; "
                "column out of range: %d (max %d)",
                self.name,
                record.db_id,
                row,
                column,
                len(self.column_fields) - 1,
            )
            return False

        # Record allows it, let the column decide.
        return self.column_fields[column].is_editable()

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set the data for the given index and role.

        Args:
            index: The model index to set data for.
            value: The value to set.
            role: The data role (CheckStateRole for checkboxes).

        Returns:
            True if the data was set successfully, False otherwise.
        """
        if not index.isValid():
            return False

        # Get the item. If it is not loaded, we cannot set the data.
        row = index.row()
        column = index.column()
        record = self.data_record(row)

        if not self._is_index_editable(record, row, column):
            return False

        # _is_index_editable should have already checked that the record is
        # not None, loaded, and not in error state.
        assert record is not None, "Record is None"
        assert record.loaded, "Record is not loaded"
        assert not record.error, "Record is in error state"

        column_fields = self.column_fields
        assert column < len(column_fields)

        if row < len(self.top_cache):
            assert self.allow_top_cache_edit, "Top cache editing is disabled"

        # Are we editing the check state?
        if role == Qt.ItemDataRole.CheckStateRole:
            if self._checked is not None:
                # If there is a record ID we use that, otherwise we use
                # the record object itself (which is unique).
                record_id = id(record) if record.db_id is None else record.db_id
                if value == Qt.CheckState.Checked:
                    self._checked.add(record_id)
                else:
                    self._checked.discard(record_id)
                record.clear_cached_flags()
                self.dataChanged.emit(
                    index, index, [Qt.ItemDataRole.CheckStateRole]
                )
                self.checkedChanged.emit()
                return True
            else:
                logger.log(
                    MODEL_LOG_LEVEL,
                    "M: %s Refusing to edit item %s at row %d; "
                    "no checked list",
                    self.name,
                    record.db_id,
                    row,
                )
                return False

        if role != Qt.ItemDataRole.EditRole:
            logger.log(
                MODEL_LOG_LEVEL,
                "M: %s Refusing to edit item %s at row %d; "
                "role is not EditRole: %d",
                self.name,
                record.db_id,
                row,
                role,
            )
            return False

        # Cache all display values to be able to determine f we should
        # emit a dataChanged signal.
        display_values = {
            column_fields[i]
            .name: record.values.get(i, {})
            .get(Qt.ItemDataRole.DisplayRole, None)
            for i in range(len(column_fields))
            if i != column
        }

        if row < len(self.top_cache):
            self.change_top_level_value(record, column, value)
        else:
            # Get the field that manages this record.
            field = column_fields[column]
            assert field.is_editable()

            try:
                with self.ctx.same_session(auto_commit=True) as session:
                    conditions = self.item_by_id_conditions(record.db_id)
                    db_item = session.scalar(
                        select(self.db_model).where(*conditions)
                    )
                    if db_item is None:
                        logger.error(
                            "M: %s Record %s not found for edit",
                            self.name,
                            record.db_id,
                        )
                        return False

                    field.apply_edit_value(db_item, value, session)
                    session.commit()
                    self.db_item_to_record(db_item, record)
            except Exception as e:
                logger.error(
                    "M: %s Error setting field %s for row %d (ID: %s): %s",
                    self.name,
                    field.name,
                    row - len(self.top_cache),
                    record.db_id,
                    e,
                    exc_info=True,
                )
                return False

        # Current cell is always updated.
        record.clear_cached_flags()
        self.dataChanged.emit(
            index,
            index,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.ToolTipRole,
                Qt.ItemDataRole.StatusTipRole,
            ],
        )

        # Other cells might have changed, so we need to emit a
        # dataChanged signal for them, too.
        for i in range(len(self.column_fields)):
            if i != column:
                if display_values.get(
                    self.column_fields[i].name
                ) != record.values.get(i, {}).get(
                    Qt.ItemDataRole.DisplayRole, None
                ):
                    self.dataChanged.emit(
                        self.index(row, i),
                        self.index(row, i),
                        [Qt.ItemDataRole.DisplayRole],
                    )

        logger.debug(
            "M: %s Data changed for item ID: %s at row %d, column %d",
            self.name,
            record.db_id,
            row,
            column,
        )
        return True

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """Sort the model by the given column and order.

        The function clears the cache and resets the total count.
        """
        try:

            # Respect the partially-initialized state.
            if self._total_count == -1:
                return

            field = self.column_fields[column]
            if not self.is_field_sortable(field.name):
                logger.error(
                    "M: %s Refusing to sort by column %d; "
                    "field %s is not part of the sortable set.",
                    self.name,
                    column,
                    field.name,
                )
                return

            if not field.sortable:
                logger.error(
                    "M: %s Refusing to sort by column %d; "
                    "field %s is capable of sorting.",
                    self.name,
                    column,
                    field.name,
                )
                return

            self.sort_by = [
                (
                    field.name,
                    "asc" if order == Qt.SortOrder.AscendingOrder else "desc",
                )
            ]

            self.reset_model()
        except Exception as e:
            logger.error(
                "M: %s Error sorting model: %s", self.name, e, exc_info=True
            )

    def change_filter(
        self,
        fld: str,
        op: str,
        vl: Any,
        trigger_reset: bool = True,
    ):
        """Changes a top level filter by matching the field and operation.

        If the filter does not exist in the current filter, it is added.
        If the filter exists in the current filter, it is replaced in place.

        Args:
            fld: The field to filter by.
            op: The operation to perform.
            vl: The value to compare against.
            trigger_reset: If True, the model will be reset if the model
                is fully loaded.
        """
        for filter in self._filters:
            if isinstance(filter, FieldFilter):
                if filter.fld == fld and filter.op == op:
                    filter.op = op
                    filter.vl = vl
                    if trigger_reset and self.is_fully_loaded:
                        self.reset_model()
                    return
        self._filters.append(FieldFilter(fld=fld, op=op, vl=vl))
        if trigger_reset and self.is_fully_loaded:
            self.reset_model()

    def apply_filter(self, filter: Union[FilterType, None]) -> None:
        """Apply a filter to the model.

        Sets the filter and resets the model, clearing the cache and
        recalculating the total count. If the filter is the same as the
        current filter, no action is taken.

        Args:
            filter: The filter to apply. Can be None to clear filters.

        Raises:
            ValueError: If the filter structure is invalid.
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
            logger.error(
                "M: %s Error applying filter: %s", self.name, e, exc_info=True
            )

        # Make sure that the filter is valid.
        if filter:
            validate_result = validate_filter(filter)
            if validate_result:
                raise ValueError(
                    f"Invalid filters: {validate_result[0]} "
                    f"{'->'.join(validate_result[1:])}"
                )

        self._filters = filter if filter else []
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Changing filters from %s to %s",
            self.name,
            previous,
            self._filters,
        )

        # Respect the partially-initialized state.
        if self._total_count == -1:
            return

        self.reset_model()

    def text_to_filter(
        self,
        text: str,
        search_type: Optional[SearchType] = SearchType.EXTENDED,
        limit: Optional[str] = None,
    ) -> FilterType:
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.

        Args:
            text: The text to convert to a filter.
            search_type: The type of search to perform.
            limit: If provided, the search will be limited to the given field
                name. If None, all simple_search_fields will be used.

        Returns:
            The filter.
        """
        if not text or len(text.strip()) == 0:
            return []

        # We allow for ID:NNN,NNN,NNN format to filter by primary key.
        simplified = text.upper().strip().replace(" ", "")
        if simplified.startswith("ID:"):
            if len(simplified) == 3:
                # The user just typed the marker, we wait for more characters.
                return []
            id_parts = simplified[3:].split(",")
            try:
                id_parts = [int(part) for part in id_parts]
                pk_fields = self.primary_key_fields
                if len(pk_fields) == len(id_parts):
                    filters = [
                        FieldFilter(fld=f.name, op="==", vl=id_parts[i])
                        for i, f in enumerate(pk_fields)
                    ]
                    if len(filters) > 1:
                        return ["and", filters]  # type: ignore
                    return [filters[0]] if filters else []  # type: ignore
            except ValueError:
                pass

        # Determine which fields to search
        fields_to_search = [
            f.name
            for f in self.simple_search_enabled_fields
            if limit is None or f.name == limit
        ]

        if not fields_to_search:
            return []

        # Use SearchType to prepare the input (handles EXTENDED mode
        # transformations)
        if search_type is None:
            search_type = SearchType.SIMPLE

        # Prepare the text using SearchType
        prepared_text = search_type.prepare_input(text)

        # Create filters for the original text
        filters = create_multi_field_or_filter(
            fields_to_search, prepared_text, search_type
        )

        # Handle unidecode variants for text-based searches
        ua_text = unidecode(prepared_text)
        if ua_text != prepared_text:
            # Create filters for uni-decoded text
            ua_filters = create_multi_field_or_filter(
                fields_to_search, ua_text, search_type
            )

            # Combine both sets of filters with OR
            all_field_filters = extract_field_filters(filters)
            all_field_filters.extend(extract_field_filters(ua_filters))

            if len(all_field_filters) == 0:
                return []
            elif len(all_field_filters) == 1:
                return [all_field_filters[0]]  # type: ignore
            else:
                return ["OR", all_field_filters]  # type: ignore

        return filters

    def apply_simple_search(
        self,
        text: str,
        search_type: "SearchType" = SearchType.SIMPLE,
        limit: Optional[str] = None,
    ) -> None:
        """Apply a simple search to the model.

        The search is applied to the fields in the `simple_search_fields`
        property.

        Search types:
            - EXACT: Exact search. The = operator is used, so the value must
                match exactly, including case.
            - SIMPLE: Partial search. The ilike operator is used, and the
                input is not altered in any way. The user can use the %
                wildcard to match any number of characters.
            - EXTENDED: Extended search. The input is altered in the
                following ways:
                - All spaces are replaced with %
                - All * are replaced with %
                - If the input contains no wildcards (%, *), then % is added
                to the beginning and end of the input.
            - PATTERN: Pattern search. The input is considered to be a
                regular expression pattern. It is not altered in any way.
                Will be applied using the i (case-insensitive) and m (
                multi-line, ^ and $ apply to each line) flags.

        Args:
            text: The text to search for.
            exact: If True, the search will be exact.
            limit: If present, the search will be limited to the given field.
        """
        filters = self.text_to_filter(text, search_type, limit)
        self.apply_filter(filters)  # type: ignore

    def checked_rows(self) -> Optional[List[RecIdType]]:
        """Return the list of row indices for checked items.

        Returns None if the model is not in checkable mode. The returned
        row indices include the offset from top_cache items.

        The function may update the values in the _checked attribute
        to replace the object ID with the database ID.

        Returns:
            A list of row indices for checked items, or None if not in
            checkable mode.
        """
        if self._checked is None:
            return None

        result = []

        # Index the top cache by record ID.
        top_id_cache = {id(r): i for i, r in enumerate(self.top_cache)}
        replace = []
        for record_id in self._checked:
            assert record_id is not None, "Record ID is None"

            # The usual case when the database ID was used.
            row = self._db_to_row.get(record_id, None)
            if row is not None:
                result.append(
                    row
                    + (0 if record_id in top_id_cache else len(self.top_cache))
                )
                continue

            # The record itself is used usually when we're dealing with top
            # level items.
            top_row = top_id_cache.get(record_id, None)  # type: ignore
            if top_row is not None:
                result.append(len(self.top_cache))
                continue

            # Unusual: a record that was unloaded at the time of the check.
            for r_idx, rec in self.cache.iter_existing():
                iter_rec_id = id(rec)
                if rec.db_id is not None:
                    replace.append((iter_rec_id, rec.db_id))
                if iter_rec_id == record_id:
                    result.append(r_idx)
                    break

        # If we have found some records to replace, we need to update the
        # checked list.
        for record_id, db_id in replace:
            assert (
                db_id in self._db_to_row
            ), f"Database ID {db_id} not found in _db_to_row"
            self._checked[db_id] = self._checked[record_id]  # type: ignore
            del self._checked[record_id]  # type: ignore

        return result

    def set_prioritized_ids(self, ids: Optional[List[RecIdType]]) -> None:
        """Set the prioritized IDs and reset the model.

        Prioritized IDs appear first in sorting results. If the IDs are
        the same as the current prioritized IDs, no action is taken.

        Args:
            ids: The list of IDs to prioritize, or None to clear prioritization.
        """
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Setting prioritized ids to %s...",
            self.name,
            ids,
        )
        if self.prioritized_ids == ids:
            return
        self.prioritized_ids = ids
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Prioritized ids set to %s. Resetting model.",
            self.name,
            ids,
        )

        # Respect the partially-initialized state.
        if self._total_count == -1:
            return

        self.reset_model()

    def find_qt_record_by_id(
        self, rec_id: RecIdType
    ) -> Tuple[Optional[int], Optional[QtRecord]]:
        """Find a database record by its ID.

        Args:
            id: The ID of the record to find.

        Returns:
            The record, or None if not found.
        """
        # Attempt to find the record in the regular cache.
        row = self._db_to_row.get(rec_id, None)
        if row is None:
            # See if the record is in the top cache.
            for t_row in range(len(self.top_cache)):
                if self.top_cache[t_row].db_id == rec_id:
                    return t_row, self.top_cache[t_row]
            return None, None

        # Adjust the row index to account for the top cache.
        row = row + len(self.top_cache)
        return row, self.cache[row]

    def insert_db_record(self, db_item: DBM) -> "QtRecord":
        """Insert a database record into the model.

        The record is not placed into the normal cache. It is placed into a
        special cache that always reports its items first, before other items.
        """
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Inserting record into model...",
            self.name,
        )
        parent_idx = QModelIndex()
        self.rowsAboutToBeInserted.emit(parent_idx, 0, 0)
        result = self.db_item_to_record(db_item)
        self.top_cache.insert(0, result)
        self.rowsInserted.emit(parent_idx, 0, 0)
        self.totalCountChanged.emit(self.total_count)
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Record inserted into model.",
            self.name,
        )
        return result

    def insert_new_records(
        self, new_items: Sequence[Union[Dict[str, Any], "QtRecord"]]
    ) -> List["QtRecord"]:
        """Insert a database record into the model.

        The record is not placed into the normal cache. It is placed into a
        special cache that always reports its items first, before other items.
        """
        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Inserting %d new records into model...",
            self.name,
            len(new_items),
        )

        result = []
        parent_idx = QModelIndex()
        self.rowsAboutToBeInserted.emit(parent_idx, 0, len(new_items) - 1)

        for i, item in enumerate(new_items):
            if isinstance(item, QtRecord):
                m_item = item
            else:
                m_item = self.data_to_record(item)
            if m_item is None:
                logger.error(
                    "M: %s Error converting item %d to record",
                    self.name,
                    i,
                )
                continue
            self.top_cache.insert(i, m_item)
            result.append(m_item)

        self.rowsInserted.emit(parent_idx, 0, len(new_items) - 1)
        self.totalCountChanged.emit(self.total_count)

        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s %d new records inserted into model.",
            self.name,
            len(new_items),
        )
        return result

    def set_top_records(self, records: Sequence["QtRecord"]) -> None:
        """Set the top records.

        Args:
            records: The records to set.
        """
        crt_len = len(self.top_cache)
        if crt_len:
            self.rowsAboutToBeRemoved.emit(QModelIndex(), 0, crt_len - 1)
            self.rowsRemoved.emit(QModelIndex(), 0, crt_len - 1)

        new_len = len(records)
        if new_len:
            self.rowsAboutToBeInserted.emit(QModelIndex(), 0, new_len - 1)
            self.top_cache = list(records)
            self.rowsInserted.emit(QModelIndex(), 0, new_len - 1)
        else:
            self.top_cache = []

        if new_len != crt_len:
            self.totalCountChanged.emit(self.total_count)

    def record_to_data(self, record: "QtRecord", session: "Session") -> DBM:
        """Convert a record to a database item."""
        result = self.db_model()

        for f_index, fld in enumerate(self.column_fields):
            value = record.data(f_index, Qt.ItemDataRole.EditRole)
            fld.save_value_to(result, value, session)

        return result

    def data_to_record(
        self, item: Dict[str, Any], record: Optional["QtRecord"] = None
    ) -> "QtRecord":
        """Convert data to a record.

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

        uuid_id = str(uuid.uuid4())

        if record is None:
            result = QtRecord(
                model=self,  # type: ignore
                db_id=uuid_id,  # type: ignore
            )
        else:
            result = record
            result.db_id = uuid_id  # type: ignore

        for f_index, fld in enumerate(self.column_fields):
            try:
                value = item.get(fld.name, None)
                result.values[f_index] = {
                    Qt.ItemDataRole.DisplayRole: value,
                    Qt.ItemDataRole.EditRole: value,
                }
            except Exception as e:
                logger.error(
                    "M: %s Error converting item %d to record "
                    "using field '%s': %s",
                    self.name,
                    f_index,
                    fld.name,
                    e,
                )

                import traceback

                logger.error("M: %s %s", self.name, traceback.format_exc())

                result.values[f_index] = {
                    Qt.ItemDataRole.DisplayRole: str(e),
                    Qt.ItemDataRole.EditRole: str(e),
                }
                result.error = True

        # Deal with soft delete.
        del_field = self.get_soft_delete_field()
        if del_field is not None:
            del_value = item.get(del_field.name, None)
            result.soft_del = bool(del_value)

        result.loaded = True
        return result

    @property
    def settings_key(self) -> str:
        """Return the key for the settings."""
        return f"model_{self.name}_settings"

    def load_settings(self) -> None:
        """Load the settings from the context."""

        spl_src_fields = self.simple_search_fields
        spl_src_fields_stg = self.ctx.stg.get_setting(
            f"{self.settings_key}.simple_search_fields", default=None
        )
        if spl_src_fields_stg is not None:
            if len(spl_src_fields_stg) > len(spl_src_fields):
                spl_src_fields_stg = spl_src_fields_stg[: len(spl_src_fields)]
            elif len(spl_src_fields_stg) < len(spl_src_fields):
                spl_src_fields_stg = spl_src_fields_stg + [True] * (
                    len(spl_src_fields) - len(spl_src_fields_stg)
                )
            if not all(isinstance(i, bool) for i in spl_src_fields_stg):
                spl_src_fields_stg = [True] * len(spl_src_fields)
                logger.warning(
                    "M: %s Simple search fields settings are invalid, "
                    "resetting to default.",
                    self.name,
                )
            self._s_s_enabled = spl_src_fields_stg

    def set_simple_search_field_states(self, values: List[bool]):
        """Set the state of each field for simple search.

        Args:
            values: The list of states.
        """
        if len(values) != len(self._s_s_fields):
            raise ValueError(
                "The number of states must match the number of fields."
            )
        self._s_s_enabled = values
        if self._save_settings:
            self.ctx.stg.set_setting(
                f"{self.settings_key}.simple_search_fields",
                values,
            )

    def constraints_changed(self, concept_key: str, new_value: Any) -> None:
        """React to the constraints being changed.

        The default implementation does nothing.

        Args:
            concept_key: The key of the concept that has changed.
            new_value: The new value of the concept.
        """

    def get_constraint_filter(
        self, concept_key: str, new_value: Any
    ) -> Optional[Any]:
        """Get the filter for a constraint."""
        return None

    def ensure_fully_loaded(self) -> None:
        """Ensure that the model is fully loaded."""
        if self.is_fully_loaded:
            return

        range_start = None
        existing = set(self.cache.keys())
        for i in range(self._total_count):
            if i in existing:
                m_rec = self.cache[i]
                if m_rec.loaded and not m_rec.error:
                    # If we-re accumulating indices, end that now.
                    if range_start is not None:
                        self.request_items(range_start, i - range_start)
                        range_start = None
                    continue

            # If we're not accumulating indices, start that now.
            if range_start is None:
                range_start = i

        # If we're still accumulating indices, end that now.
        if range_start is not None:
            self.request_items(range_start, self._total_count - range_start)

    def change_top_level_value(
        self, record: "QtRecord", column: int, value: Any
    ) -> None:

        # Get the field that manages this record.
        field = self.column_fields[column]
        assert field.is_editable()

        # Top level items are managed in memory only.
        # Update the in-memory record without touching the DB.
        record.values[column] = field.expand_value(value)

    def restore_records(
        self, ids: List[RecIdType], change_top: bool = False
    ) -> None:
        """Restore the records with the given IDs.

        Args:
            ids: The list of IDs of the records to restore.
            change_top: Whether to change the top cache.
        """
        if not self.has_soft_delete_field:
            raise NotImplementedError(
                f"Soft delete not available in model {self.name}."
            )
        del_field = self.get_soft_delete_field()
        if del_field is None:
            raise NotImplementedError("Soft delete field is not set.")

        changed_cache = []
        tc_size = len(self.top_cache)
        with self.ctx.same_session() as session:
            not_found = {}
            for db_rec in session.scalars(
                select(self.db_model).where(self.get_id_filter(ids))
            ):
                assert db_rec is not None
                db_id = self.get_db_item_id(db_rec)
                row = self._db_to_row.get(db_id, None)
                if row is None:
                    not_found[db_id] = db_rec
                    continue
                m_rec = self.cache[row]
                assert m_rec is not None and m_rec.db_id == db_id
                assert m_rec.loaded and not m_rec.error

                self.change_soft_delete_value(db_rec, False)
                self.cache[row].soft_del = False

                changed_cache.append(row + tc_size)

            if change_top:
                top_map = {
                    m_rec.db_id: (row, m_rec)
                    for row, m_rec in enumerate(self.top_cache)
                    if m_rec.db_id is not None
                }
                final_not_found = {}
                for db_id, db_rec in not_found.items():
                    if db_id in top_map:
                        row, m_rec = top_map[db_id]
                        m_rec.soft_del = False
                        changed_cache.append(row + tc_size)
                    else:
                        final_not_found[db_id] = db_rec
                not_found = final_not_found

            session.commit()

        for row in changed_cache:
            self.dataChanged.emit(
                self.index(row, 0), self.index(row, self.columnCount() - 1)
            )
        logger.debug(
            "M: %s Restored %d records.",
            self.name,
            len(changed_cache),
        )
        if len(not_found) > 0:
            logger.warning(
                "M: %s %d records were not found in the database and "
                "were not restored: %s.",
                self.name,
                len(not_found),
                ", ".join(str(id) for id in not_found.keys()),
            )

    def can_clone_records(self) -> bool:
        """Return True if the model can clone records.

        The default clone implementation simply copies the field values
        from the original record to the new record, except primary fields.

        This method returns True if there are any non-primary fields
        and the number of primary key fields is exactly one, assuming that,
        in this case, the database will allocate the ID for the new record.

        """
        if len(self.primary_key_fields) != 1:
            return False
        return any((not field.primary) for field in self.column_fields)

    def clone_record(self, db_id: RecIdType) -> Tuple[int, "QtRecord"]:
        """Clone the record with the given ID.

        If the database index is found among the loaded ones the new
        record will be inserted right after it, otherwise it will be inserted
        at the start of the model, after the top cache.

        Args:
            db_id: The ID of the record to clone.

        Returns:
            The index of the new record in the model and the new record.
        """
        with self.ctx.same_session() as session:
            db_rec = session.scalar(
                select(self.db_model).where(self.get_id_filter([db_id]))
            )
            if db_rec is None:
                raise ValueError(
                    self.t(
                        "cmn.record-id-not-found",
                        "Record with ID {rec_id} was not found in "
                        "the database.",
                        rec_id=db_id,
                    ),
                )

            new_rec = self.db_model()
            for fld in self.fields:
                if not fld.primary:
                    setattr(new_rec, fld.name, getattr(db_rec, fld.name))
            session.add(new_rec)
            session.commit()
            result = self.db_item_to_record(new_rec)

        # We want to place this record right next to the one that was cloned.
        insert_index = self._db_to_row.get(db_id, -1) + 1
        self.beginInsertRows(QModelIndex(), insert_index, insert_index)
        self.cache.insert_rows(insert_index, 1)
        self._db_to_row = {
            db_id_temp: row_temp + 1 if row_temp >= insert_index else row_temp
            for db_id_temp, row_temp in self._db_to_row.items()
        }
        self.cache[insert_index] = result
        self._total_count += 1
        self.endInsertRows()
        self.totalCountChanged.emit(self.total_count)
        logger.debug(
            "M: %s Record cloned into model at index %d from ID %s to ID %s.",
            self.name,
            insert_index,
            db_id,
            result.db_id,
        )
        return insert_index, result

    def remove_all_records(self) -> None:
        """Remove all records in the current selection."""

        # Resolve primary key columns for the selection subquery.
        primary_field_names = [fld.name for fld in self.fields if fld.primary]
        if not primary_field_names:
            raise ValueError("Cannot remove all records without a primary key.")

        # Build a subquery that selects the IDs in the current selection.
        selection_subquery = self.filtered_selection.subquery()
        selection_cols = [
            getattr(selection_subquery.c, name) for name in primary_field_names
        ]
        id_subquery = select(*selection_cols).select_from(selection_subquery)

        # Build the primary key expression for the target table.
        db_pk_cols = [
            getattr(self.db_model, name) for name in primary_field_names
        ]
        db_pk_expr = (
            tuple_(*db_pk_cols) if len(db_pk_cols) > 1 else db_pk_cols[0]
        )

        # Apply the bulk update or delete without loading records.
        with self.ctx.same_session() as session:
            if self.has_soft_delete_field:
                del_field = self.get_soft_delete_field()
                if del_field is None:
                    raise NotImplementedError(
                        f"Soft delete not available in model {self.name}."
                    )
                stmt = (
                    update(self.db_model)
                    .where(db_pk_expr.in_(id_subquery))
                    .values({del_field: True})
                )
            else:
                stmt = delete(self.db_model).where(db_pk_expr.in_(id_subquery))

            result = session.execute(stmt)
            session.commit()

        # Reset the model to refresh counts and cache.
        self.reset_model(clear_top_cache=True)

        logger.log(
            MODEL_LOG_LEVEL,
            "M: %s Removed all records (affected rows: %s).",
            self.name,
            result.rowcount,
        )

    def iter_records(
        self,
        include_top: bool = True,
        include_not_loaded: bool = False,
        include_error: bool = False,
        include_no_data: bool = False,
    ) -> Iterator[Tuple["QtRecord", int]]:
        if include_top:
            for row, record in enumerate(self.top_cache):
                if include_not_loaded and not record.loaded:
                    continue
                if include_error and record.error:
                    continue
                yield record, row

        offset = len(self.top_cache)

        for row in range(self._total_count):
            m_record = self.cache.get_or_create(row, create=include_no_data)
            if m_record is None:
                continue

            if include_not_loaded and not m_record.loaded:
                continue
            if include_error and m_record.error:
                continue
            yield m_record, row + offset
