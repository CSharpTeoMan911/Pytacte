from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from firebase import firebase_database
from firebase.firebase_database import (
    FirebaseDatabase,
    ServerAvailabilityDTO,
    TranscriptionJobsDTO,
)


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
    reference.get.return_value = None
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
    first_record = {
        "server_id": "server-1",
        "server_address": "192.0.2.1",
        "load_balancer": False,
        "tls": True,
        "cpu_usage": 12.5,
        "last_heartbeat": 202611151234,
    }
    reference = MagicMock()
    reference.order_by_key.return_value.limit_to_first.return_value.get.return_value = {
        "server-1": first_record,
        "server-2": {"server_id": "server-2"},
    }
    database_reference = MagicMock(return_value=reference)
    monkeypatch.setattr(firebase_database.db, "reference", database_reference)

    result = database.get_server_availability()

    assert isinstance(result, ServerAvailabilityDTO)
    assert result.server_id == "server-1"
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

    result = database.create_transcription_job("user-123", "server-1")

    assert result[0] is True
    assert isinstance(result[1], TranscriptionJobsDTO)
    assert result[1].transcription_id == "firebase-push-id"
    database_reference.assert_called_once_with(
        "/TranscriptionJobs", app=None, url=database.database_url
    )
    job_reference.set.assert_called_once_with(
        {
            "uuid": "user-123",
            "server_id": "server-1",
            "transcription_id": "firebase-push-id",
            "last_heartbeat": int(datetime.now(UTC).strftime("%Y%m%d%H%M")),
        }
    )


def test_create_transcription_job_rejects_user_at_quota(database, monkeypatch):
    monkeypatch.setattr(
        database,
        "__count_transcription_jobs_for_user__",
        lambda user_uid: database.max_transcription_jobs_per_user,
    )

    result = database.create_transcription_job("user-123", "server-1")

    assert result[0] is False
    assert "maximum number" in result[1]


def test_create_server_availability_adds_heartbeat(database, monkeypatch):
    data = ServerAvailabilityDTO(
        server_id="server-1",
        server_address="192.0.2.1:443",
        tls=True,
        cpu_usage=12.5,
        load_balancer=False,
    )
    server_reference = MagicMock()
    server_reference.get.return_value = None
    client_reference = MagicMock()
    references = {
        ("ServerAvailability", "server-1"): server_reference,
        ("Client_Available_Pytacte_Servers", "server-1"): client_reference,
    }
    monkeypatch.setattr(
        database,
        "__reference__",
        lambda collection, record_id: references[(collection, record_id)],
    )

    result = database.create_server_availability(data)

    assert result[0] is True
    assert isinstance(result[1], ServerAvailabilityDTO)
    saved_data = server_reference.set.call_args.args[0]
    assert saved_data["last_heartbeat"] == int(
        datetime.now(UTC).strftime("%Y%m%d%H%M")
    )
    client_reference.set.assert_called_once_with(
        {
            "server_id": "server-1",
            "server_address": "192.0.2.1:443",
            "tls": True,
            "cpu_usage": 12.5,
        }
    )
    assert result[1] is data
    assert data.last_heartbeat == saved_data["last_heartbeat"]


def test_update_server_availability_syncs_existing_client_record(database, monkeypatch):
    record = ServerAvailabilityDTO(
        server_id="server-1",
        server_address="192.0.2.2:443",
        tls=True,
        cpu_usage=15.75,
        load_balancer=False,
        last_heartbeat=202611151234,
    )
    query = MagicMock()
    query.order_by_child.return_value.equal_to.return_value.get.return_value = {
        "server-1": {
            "server_id": "server-1",
            "server_address": "192.0.2.1:443",
            "tls": False,
            "cpu_usage": 12.5,
        }
    }
    monkeypatch.setattr(firebase_database.db, "reference", lambda *_args, **_kwargs: query)
    update_calls = []
    monkeypatch.setattr(
        database,
        "__update__",
        lambda collection, record_id, changes: update_calls.append(
            (collection, record_id, changes)
        ),
    )
    monkeypatch.setattr(database, "get_server_availability", lambda _server_id: record)

    result = database.update_server_availability(record)

    assert result == (True, record)
    assert [call[0] for call in update_calls] == [
        "ServerAvailability",
        "Client_Available_Pytacte_Servers",
    ]
    assert update_calls[0] == (
        "ServerAvailability",
        "server-1",
        record.to_record(),
    )
    assert update_calls[1] == (
        "Client_Available_Pytacte_Servers",
        "server-1",
        {
            "server_id": "server-1",
            "server_address": "192.0.2.2:443",
            "tls": True,
            "cpu_usage": 15.75,
        },
    )
    query.order_by_child.assert_called_once_with("server_id")
    query.order_by_child.return_value.equal_to.assert_called_once_with("server-1")


def test_update_server_availability_succeeds_without_client_record(
    database, monkeypatch
):
    record = ServerAvailabilityDTO(
        server_id="server-1",
        server_address="192.0.2.2:443",
        tls=True,
        cpu_usage=15.75,
        load_balancer=False,
    )
    query = MagicMock()
    query.order_by_child.return_value.equal_to.return_value.get.return_value = None
    monkeypatch.setattr(firebase_database.db, "reference", lambda *_args, **_kwargs: query)
    update = MagicMock()
    monkeypatch.setattr(database, "__update__", update)
    monkeypatch.setattr(database, "get_server_availability", lambda _server_id: record)

    result = database.update_server_availability(record)

    assert result == (True, record)
    update.assert_called_once_with(
        "ServerAvailability", "server-1", record.to_record()
    )


@pytest.mark.parametrize(
    ("method_name", "collection", "method_args", "expected_changes"),
    [
        (
            "update_transcription_job_heartbeat",
            "TranscriptionJobs",
            (),
            {"last_heartbeat": 202611151234},
        ),
        (
            "update_server_availability_heartbeat",
            "ServerAvailability",
            (25.5,),
            {
                "cpu_usage": 25.5,
                "last_heartbeat": 202611151234,
            },
        ),
    ],
)
def test_heartbeat_methods_write_utc_date(
    database, monkeypatch, method_name, collection, method_args, expected_changes
):
    expected_date = "202611151234"
    monkeypatch.setattr(
        database, "__current_heartbeat__", lambda: int(expected_date)
    )
    update = MagicMock()
    monkeypatch.setattr(database, "__update__", update)
    if collection == "TranscriptionJobs":
        monkeypatch.setattr(
            database,
            "get_transcription_job",
            lambda record_id: TranscriptionJobsDTO(
                "record-1", "user-1", "server-1", int(expected_date)
            ),
        )
    else:
        monkeypatch.setattr(
            database,
            "get_server_availability",
            lambda record_id: ServerAvailabilityDTO(
                "server-1",
                "192.0.2.1:443",
                False,
                True,
                method_args[0],
                int(expected_date),
            ),
        )

    result = getattr(database, method_name)("record-1", *method_args)

    assert result[0] is True
    assert result[1].last_heartbeat == int(expected_date)
    assert update.call_args.args == (
        collection,
        "record-1",
        expected_changes,
    )
    if collection == "ServerAvailability":
        assert result[1].cpu_usage == method_args[0]


def test_create_server_availability_returns_failure_for_duplicate(database, monkeypatch):
    reference = MagicMock()
    reference.get.return_value = {"server_id": "server-1"}
    monkeypatch.setattr(database, "__reference__", lambda *_: reference)
    data = ServerAvailabilityDTO(
        server_id="server-1",
        server_address="192.0.2.1:443",
        tls=True,
        cpu_usage=12.5,
        load_balancer=False,
    )

    result = database.create_server_availability(data)

    assert result == (False, "Server 'server-1' already exists")
    reference.set.assert_not_called()
