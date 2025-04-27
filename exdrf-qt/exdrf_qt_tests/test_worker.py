from queue import Queue
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from exdrf_qt.worker import Relay, Work, Worker


@pytest.fixture
def mock_db_conn():
    """Fixture to mock the database connection."""
    mock_conn = MagicMock()
    mock_conn.session.return_value.__enter__.return_value.scalars.return_value = [
        1,
        2,
        3,
    ]
    return mock_conn


@pytest.fixture
def relay(mock_db_conn):
    """Fixture to create a Relay instance."""
    return Relay(cn=mock_db_conn)


def test_relay_push_work_starts_worker(relay):
    """Test that pushing work starts the worker thread."""
    mock_statement = MagicMock(spec=select)
    mock_callback = MagicMock()

    work = relay.push_work(statement=mock_statement, callback=mock_callback)

    assert work in relay.data.values()
    assert relay.worker.isRunning()


def test_relay_handle_result_success(relay):
    """Test that handle_result calls the callback on success."""
    mock_work = MagicMock(spec=Work)
    mock_work.req_id = 1
    mock_work.callback = MagicMock()
    relay.data[mock_work.req_id] = mock_work

    relay.handle_result(mock_work.req_id)

    mock_work.callback.assert_called_once_with(mock_work)


def test_relay_handle_result_missing_work(relay, caplog):
    """Test that handle_result logs a message if work is missing."""
    relay.handle_result(999)

    assert "Work with ID 999 not found in data" in caplog.text


def test_worker_run_processes_work(mock_db_conn):
    """Test that the worker processes work from the queue."""
    queue = Queue()
    worker = Worker(queue=queue, cn=mock_db_conn)
    mock_statement = MagicMock(spec=select)
    mock_work = Work(statement=mock_statement, callback=MagicMock(), req_id=1)
    queue.put(mock_work)

    with patch.object(worker, "haveResult") as mock_signal:
        worker.run()

    assert mock_work.result == [1, 2, 3]
    mock_signal.emit.assert_called_once_with(mock_work.req_id)


def test_worker_run_handles_exception(mock_db_conn, caplog):
    """Test that the worker handles exceptions during work processing."""
    queue = Queue()
    worker = Worker(queue=queue, cn=mock_db_conn)
    mock_statement = MagicMock(spec=select)
    mock_db_conn.session.return_value.__enter__.side_effect = Exception(
        "DB error"
    )
    mock_work = Work(statement=mock_statement, callback=MagicMock(), req_id=1)
    queue.put(mock_work)

    with patch.object(worker, "haveResult") as mock_signal:
        worker.run()

    assert mock_work.error is not None
    assert "Error while executing work" in caplog.text
    mock_signal.emit.assert_called_once_with(mock_work.req_id)


def test_relay_stop_stops_worker(relay):
    """Test that stopping the relay stops the worker thread."""
    relay.worker.start()
    assert relay.worker.isRunning()

    relay.stop()
    assert not relay.worker.isRunning()
