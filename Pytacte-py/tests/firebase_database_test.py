from datetime import UTC, datetime, timedelta
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
        "ram_usage": 40.0,
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


def test_delete_expired_servers_reads_and_deletes_one_record_at_a_time(
    database, monkeypatch
):
    now = datetime.now(UTC)
    expired_heartbeat = int(
        (now - timedelta(minutes=10)).strftime("%Y%m%d%H%M")
    )
    expired_records = {
        f"expired-{index:03d}": {"last_heartbeat": expired_heartbeat}
        for index in range(100)
    }
    fresh_record = {
        "last_heartbeat": int(now.strftime("%Y%m%d%H%M"))
    }
    records = {**expired_records, "fresh-server": fresh_record}
    query_count = 0
    deleted_server_ids = []

    class FakeReference:
        def __init__(self, path):
            self.path = path
            self.start_value = None
            self.end_value = None
            self.equal_value = None
            self.result_limit = None

        def order_by_child(self, child_name):
            assert child_name == "last_heartbeat"
            return self

        def start_at(self, value):
            self.start_value = value
            return self

        def end_at(self, value):
            self.end_value = value
            return self

        def equal_to(self, value):
            self.equal_value = value
            return self

        def limit_to_first(self, count):
            self.result_limit = count
            return self

        def get(self):
            nonlocal query_count
            query_count += 1
            matches = sorted(
                (
                    (server_id, record)
                    for server_id, record in records.items()
                    if self.equal_value is not None
                    and record["last_heartbeat"] == self.equal_value
                    or self.equal_value is None
                    and (
                        self.start_value is None
                        or record["last_heartbeat"] >= self.start_value
                    )
                    and (
                        self.end_value is None
                        or record["last_heartbeat"] <= self.end_value
                    )
                ),
                key=lambda item: item[1]["last_heartbeat"],
            )
            return dict(matches[: self.result_limit])

        def delete(self):
            server_id = self.path.rsplit("/", maxsplit=1)[-1]
            deleted_server_ids.append(server_id)
            records.pop(server_id)

    monkeypatch.setattr(
        firebase_database.db,
        "reference",
        lambda path, **_kwargs: FakeReference(path),
    )

    result = database.delete_expired_servers()

    assert result == (True, "Deleted 100 expired server record(s)")
    assert len(deleted_server_ids) == 100
    assert set(deleted_server_ids) == set(expired_records)
    assert records == {"fresh-server": fresh_record}
    assert query_count == 101


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
        ram_usage=40.0,
        load_balancer=False,
    )
    reference = MagicMock()
    reference.get.return_value = None
    database_reference = MagicMock(return_value=reference)
    monkeypatch.setattr(database, "__reference__", database_reference)

    result = database.create_server_availability(data)

    assert result[0] is True
    assert isinstance(result[1], ServerAvailabilityDTO)
    saved_data = reference.set.call_args.args[0]
    assert saved_data["last_heartbeat"] == int(
        datetime.now(UTC).strftime("%Y%m%d%H%M")
    )
    assert result[1] is data
    assert data.last_heartbeat == saved_data["last_heartbeat"]


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
            (25.5, 64.0),
            {
                "cpu_usage": 25.5,
                "ram_usage": 64.0,
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
                method_args[1],
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
        assert result[1].ram_usage == method_args[1]


def test_create_server_availability_returns_failure_for_duplicate(database, monkeypatch):
    reference = MagicMock()
    reference.get.return_value = {"server_id": "server-1"}
    monkeypatch.setattr(database, "__reference__", lambda *_: reference)
    data = ServerAvailabilityDTO(
        server_id="server-1",
        server_address="192.0.2.1:443",
        tls=True,
        cpu_usage=12.5,
        ram_usage=40.0,
        load_balancer=False,
    )

    result = database.create_server_availability(data)

    assert result == (False, "Server 'server-1' already exists")
    reference.set.assert_not_called()
