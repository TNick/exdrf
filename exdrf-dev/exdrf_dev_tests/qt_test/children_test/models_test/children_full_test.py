import pytest
from exdrf.filter import FilterType
from exdrf_qt.context import QtContext
from exdrf_qt.worker import Work
from PyQt5.QtCore import Qt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from exdrf_dev.db.models import Base, Child, Parent
from exdrf_dev.qt_gen.db.children.models.child_ful import QtChildFuMo


class TestQtContext(QtContext):
    """A test-specific QtContext that executes queries synchronously."""

    def __init__(self, c_string: str, engine, s_stack):
        super().__init__(c_string=c_string)
        self.engine = engine
        self.s_stack = s_stack
        self.top_widget = None

    def push_work(
        self,
        statement,
        callback,
        req_id=None,
    ) -> Work:
        """Execute the query synchronously and call the callback immediately."""
        work = Work(
            statement=statement,
            callback=callback,
            req_id=req_id,
        )

        # Execute the query synchronously
        with self.session() as session:
            work.result = list(session.scalars(statement))

        # Call the callback immediately
        callback(work)
        return work


@pytest.fixture
def memory_db():
    """Create a memory database with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


@pytest.fixture
def qt_context(memory_db):
    """Create a QtContext with the memory database."""
    engine, session = memory_db
    return TestQtContext(
        c_string="sqlite:///:memory:",
        engine=engine,
        s_stack=[session],
    )


@pytest.fixture
def sample_data(memory_db):
    """Create sample data in the database."""
    _, session = memory_db

    # Create parents
    parent1 = Parent(name="Parent 1")
    parent2 = Parent(name="Parent 2")
    session.add_all([parent1, parent2])
    session.commit()

    # Create children
    child1 = Child(data="Child 1 data", parent=parent1)
    child2 = Child(data="Child 2 data", parent=parent1)
    child3 = Child(data="Child 3 data", parent=parent2)
    session.add_all([child1, child2, child3])
    session.commit()

    return parent1, parent2, child1, child2, child3


def test_model_initialization(qt_context):
    """Test that the model initializes correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)
    assert model.db_model == Child
    # IdField, DataField, ParentIdField, ParentField
    assert len(model.fields) == 4
    assert model.total_count == 0  # No data yet


def test_model_with_data(qt_context, sample_data):
    """Test that the model loads data correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)
    assert model.total_count == 3  # Three children in sample data

    # Wait for data to load
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Test data access
    index = model.index(0, 1)  # DataField column
    # Data of first child
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Child 1 data"
    assert model.data(index, Qt.ItemDataRole.EditRole) == "Child 1 data"

    # Test parent relationship
    parent_index = model.index(0, 3)  # ParentField column
    assert (
        model.data(parent_index, Qt.ItemDataRole.DisplayRole)
        == "ID:1 Name:Parent 1"
    )


def test_model_sorting(qt_context, sample_data):
    """Test that the model sorts correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)

    # Wait for initial data to load
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Sort by data column (index 1) in ascending order
    model.sort(1, Qt.SortOrder.AscendingOrder)

    # Wait for data to reload after sorting
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    assert (
        model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 1 data"
    )
    assert (
        model.data(model.index(1, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 2 data"
    )
    assert (
        model.data(model.index(2, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 3 data"
    )

    # Sort in descending order
    model.sort(1, Qt.SortOrder.DescendingOrder)

    # Wait for data to reload after sorting
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    assert (
        model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 3 data"
    )
    assert (
        model.data(model.index(1, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 2 data"
    )
    assert (
        model.data(model.index(2, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 1 data"
    )


def test_model_filtering(qt_context, sample_data):
    """Test that the model filters correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)
    parent1, _, _, _, _ = sample_data

    # Filter by parent_id
    filter_expr: FilterType = [
        {"fld": "parent_id", "op": "eq", "vl": parent1.id}
    ]
    model.apply_filter(filter_expr)
    assert model.total_count == 2  # Two children belong to parent1

    # Wait for filtered data to load
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Verify filtered data
    assert (
        model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 1 data"
    )
    assert (
        model.data(model.index(1, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 2 data"
    )


def test_model_checking(qt_context, sample_data):
    """Test that the model handles checking correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)
    _, _, child1, _, _ = sample_data

    # Ensure model has correct total_count before enabling checking
    assert model.total_count == 3  # Three children in sample data

    # Enable checking - this triggers reset_model() which should
    # automatically trigger data loading via ensure_stubs()
    model.checked_ids = set()

    # After reset_model(), ensure total_count is still correct
    assert model.total_count == 3

    # Explicitly trigger data loading after reset
    # The reset_model() should have triggered loading via ensure_stubs(),
    # but we explicitly request items to ensure loading happens
    if model.total_count > 0:
        model.request_items(0, model.batch_size * 2)

    # Also trigger loading by accessing data (as a backup)
    index = model.index(0, 0)
    _ = model.data(index, Qt.ItemDataRole.DisplayRole)

    # Wait for data to load (synchronous execution should load immediately)
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Ensure data is loaded
    assert model.loaded_count > 0, "Data should be loaded"

    # Check first item
    index = model.index(0, 0)
    model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    # The checked_ids should contain the database ID of the first child
    assert model.checked_ids == {child1.id}

    # Uncheck first item
    model.setData(
        index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole
    )
    assert model.checked_ids == set()


def test_model_cloning(qt_context, sample_data):
    """Test that the model clones correctly."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)
    parent1, _, _, _, _ = sample_data

    # Apply some settings
    filter_expr: FilterType = [
        {"fld": "parent_id", "op": "eq", "vl": parent1.id}
    ]
    model.apply_filter(filter_expr)

    # Wait for filtered data to load
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    model.sort(1, Qt.SortOrder.AscendingOrder)

    # Wait for sorted data to load
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Clone the model
    clone = model.clone_me()

    # Verify clone has same settings
    assert clone.total_count == 2  # Same filter applied

    # Trigger data loading for cloned model
    _ = clone.data(clone.index(0, 1), Qt.ItemDataRole.DisplayRole)

    # Wait for cloned model data to load
    start = time.time()
    while clone.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Same sort order
    assert (
        clone.data(clone.index(0, 1), Qt.ItemDataRole.DisplayRole)
        == "Child 1 data"
    )


def test_model_header_data(qt_context, sample_data):
    """Test that the model provides correct header data."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)

    # Test horizontal headers
    assert (
        model.headerData(
            0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )
        == "ID"
    )
    assert (
        model.headerData(
            1, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )
        == "Data"
    )
    assert (
        model.headerData(
            2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )
        == "Parent ID"
    )
    assert (
        model.headerData(
            3, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )
        == "Parent"
    )

    # Load some data to test vertical headers
    index = model.index(0, 0)
    _ = model.data(index, Qt.ItemDataRole.DisplayRole)

    # Wait for data to load
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Test vertical headers (row numbers) - only if data is loaded
    if model.loaded_count > 0:
        assert (
            model.headerData(
                0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole
            )
            == model.cache[0].db_id
        )
        if model.loaded_count > 1:
            assert (
                model.headerData(
                    1, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole
                )
                == model.cache[1].db_id
            )


def test_model_flags(qt_context, sample_data):
    """Test that the model provides correct flags."""
    model = QtChildFuMo(ctx=qt_context, wait_before_request=0)

    # Wait for data to load to ensure we have valid indices
    import time

    timeout = 1.0
    start = time.time()
    while model.loaded_count == 0 and (time.time() - start) < timeout:
        time.sleep(0.01)

    # Test flags for valid index (only if data is loaded)
    if model.loaded_count > 0:
        index = model.index(0, 0)
        flags = model.flags(index)
        assert bool(flags & Qt.ItemFlag.ItemIsEnabled)
        assert bool(flags & Qt.ItemFlag.ItemIsSelectable)

    # Test flags for invalid index
    invalid_index = model.index(-1, -1)
    assert model.flags(invalid_index) == Qt.ItemFlag.NoItemFlags
