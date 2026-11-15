from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from firebase import firebase_database
from firebase.firebase_database import FirebaseDatabase


@pytest.fixture
def database_factory():
    def create_database(database_url):
        return FirebaseDatabase(database_url, max_transcription_jobs_per_user=2)

    return create_database


@pytest.fixture
def database(database_factory):
    return database_factory(
        "https://pytacte-default-rtdb.europe-west1.firebasedatabase.app/"
    )


@pytest.mark.parametrize(
    "database_url",
    [
        "https://pytacte-default-rtdb.europe-west1.firebasedatabase.app/",
        "https://project-a-default-rtdb.firebaseio.com",
        "https://project-b.europe-west1.firebasedatabase.app",
        "http://localhost:9000",
    ],
)
def test_uses_arbitrary_database_url(database_factory, database_url, monkeypatch):
    database = database_factory(database_url)
    reference = MagicMock()
    reference.get.return_value = {"server-1": {"server_id": "server-1"}}
    database_reference = MagicMock(return_value=reference)
    monkeypatch.setattr(firebase_database.db, "reference", database_reference)

    database.get_server_availability("server-1")

    database_reference.assert_called_once_with(
        "/ServerAvailability/server-1", app=None, url=database_url
    )


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "not-a-url",
        "ftp://pytacte-default-rtdb.firebaseio.com",
        "http://pytacte-default-rtdb.firebaseio.com",
        "https://example.com",
        "https://user:password@pytacte-default-rtdb.firebaseio.com",
        "https://pytacte-default-rtdb.firebaseio.com/TranscriptionJobs",
    ],
)
def test_rejects_invalid_database_url(database_url):
    with pytest.raises(ValueError):
        FirebaseDatabase(database_url, max_transcription_jobs_per_user=2)


@pytest.mark.parametrize("threshold", [-1, True, 1.5])
def test_rejects_invalid_job_threshold(threshold):
    with pytest.raises(ValueError, match="non-negative integer"):
        FirebaseDatabase(
            "https://pytacte-default-rtdb.firebaseio.com",
            max_transcription_jobs_per_user=threshold,
        )


def test_get_server_availability_returns_only_the_first_record(database, monkeypatch):
    first_record = {"server_id": "server-1", "server_address": "192.0.2.1"}
    reference = MagicMock()
    reference.order_by_key.return_value.limit_to_first.return_value.get.return_value = {
        "server-1": first_record,
        "server-2": {"server_id": "server-2"},
    }
    database_reference = MagicMock(return_value=reference)
    monkeypatch.setattr(firebase_database.db, "reference", database_reference)

    result = database.get_server_availability()

    assert result == first_record
    reference.order_by_key.assert_called_once_with()
    reference.order_by_key.return_value.limit_to_first.assert_called_once_with(1)


def test_create_transcription_job_generates_id_and_stores_record(database, monkeypatch):
    monkeypatch.setattr(
        database, "get_server_availability", lambda: {"server_id": "server-1"}
    )
    monkeypatch.setattr(
        database, "__count_transcription_jobs_for_user__", lambda user_uid: 1
    )
    collection = MagicMock()
    job_reference = MagicMock()
    job_reference.key = "firebase-push-id"
    collection.push.return_value = job_reference
    database_reference = MagicMock(return_value=collection)
    monkeypatch.setattr(firebase_database.db, "reference", database_reference)

    result = database.create_transcription_job("user-123")

    assert result == (True, "Transcription job firebase-push-id created")
    database_reference.assert_called_once_with(
        "/TranscriptionJobs", app=None, url=database.database_url
    )
    job_reference.set.assert_called_once_with(
        {
            "uuid": "user-123",
            "server_id": "server-1",
            "transcription_id": "firebase-push-id",
        }
    )


def test_create_transcription_job_rejects_user_at_quota(database, monkeypatch):
    monkeypatch.setattr(
        database, "get_server_availability", lambda: {"server_id": "server-1"}
    )
    monkeypatch.setattr(
        database,
        "__count_transcription_jobs_for_user__",
        lambda user_uid: database.max_transcription_jobs_per_user,
    )

    result = database.create_transcription_job("user-123")

    assert result[0] is False
    assert "maximum number" in result[1]


def test_create_server_availability_adds_heartbeat(database, monkeypatch):
    data = {
        "server_id": "server-1",
        "server_address": "192.0.2.1:443",
        "tls": True,
        "cpu_usage": 12.5,
        "ram_usage": 40.0,
        "load_balancer": False,
    }
    reference = MagicMock()
    reference.get.return_value = None
    database_reference = MagicMock(return_value=reference)
    monkeypatch.setattr(database, "__reference__", database_reference)

    result = database.create_server_availability("server-1", data)

    assert result == (True, "Server availability record server-1 created")
    saved_data = reference.set.call_args.args[0]
    assert saved_data["last_heartbeat"] == int(
        datetime.now(timezone.utc).strftime("%Y%m%d")
    )
    assert "last_heartbeat" not in data


@pytest.mark.parametrize(
    ("method_name", "collection"),
    [
        ("update_transcription_job_heartbeat", "TranscriptionJobs"),
        ("update_server_availability_heartbeat", "ServerAvailability"),
    ],
)
def test_heartbeat_methods_write_utc_date(
    database, monkeypatch, method_name, collection
):
    expected_date = "20261115"
    mocked_datetime = MagicMock()
    mocked_datetime.now.return_value.strftime.return_value = expected_date
    monkeypatch.setattr(firebase_database, "datetime", mocked_datetime)
    update = MagicMock()
    monkeypatch.setattr(database, "__update__", update)

    result = getattr(database, method_name)("record-1")

    assert result[0] is True
    assert update.call_args.args == (
        collection,
        "record-1",
        {"last_heartbeat": int(expected_date)},
    )


def test_create_server_availability_returns_failure_for_duplicate(database, monkeypatch):
    reference = MagicMock()
    reference.get.return_value = {"server_id": "server-1"}
    monkeypatch.setattr(database, "__reference__", lambda *_: reference)
    data = {
        "server_id": "server-1",
        "server_address": "192.0.2.1:443",
        "tls": True,
        "cpu_usage": 12.5,
        "ram_usage": 40.0,
        "load_balancer": False,
    }

    result = database.create_server_availability("server-1", data)

    assert result == (False, "Server 'server-1' already exists")
    reference.set.assert_not_called()
