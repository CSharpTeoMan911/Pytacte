"""Live Firebase Realtime Database CRUD integration test.

Run with:
    pytest tests/database_interaction_test.py \
        --database-url=https://your-project-default-rtdb.europe-west1.firebasedatabase.app/

Firebase Admin credentials must also be available through Application Default
Credentials (for example, GOOGLE_APPLICATION_CREDENTIALS).
"""

from datetime import UTC, datetime, timedelta
from multiprocessing import get_context
from random import Random
from unittest.mock import Mock
from uuid import uuid4

import firebase_admin
import pytest
from firebase_admin import credentials
from firebase_admin import db as firebase_db

from firebase.firebase_database import FirebaseDatabase, ServerAvailabilityDTO
from server.load_balancer import LoadBalancer


def test_delete_expired_items_includes_orphan_transcription_jobs():
    database = Mock()
    database.delete_expired_transcription_jobs.return_value = (True, "expired jobs")
    database.delete_expired_servers.return_value = (True, "expired servers")
    database.delete_orphan_client_servers.return_value = (
        True,
        "orphan client servers",
    )
    database.delete_orphan_transcription_jobs.return_value = (True, "orphan jobs")
    load_balancer = LoadBalancer.__new__(LoadBalancer)
    load_balancer.database_connection = database

    result = load_balancer.delete_expired_items()

    assert result == (
        [True, True, True, True],
        [
            "expired jobs",
            "expired servers",
            "orphan client servers",
            "orphan jobs",
        ],
    )
    database.delete_orphan_transcription_jobs.assert_called_once_with()


def _run_server_sort_in_process(database_url):
    app = firebase_admin.initialize_app(
        credentials.ApplicationDefault(),
        options={"databaseURL": database_url},
        name=f"server-sort-test-{uuid4().hex}",
    )
    try:
        database = FirebaseDatabase(
            database_url,
            max_transcription_jobs_per_user=2,
            firebase_app=app,
        )
        database.sort_severs_by_least_cpu_usage()
    finally:
        firebase_admin.delete_app(app)


@pytest.fixture
def database(request):
    database_url = request.config.getoption("--database-url")
    if not database_url:
        pytest.skip("Pass --database-url or set FIREBASE_DATABASE_URL")

    app = firebase_admin.initialize_app(
        credentials.ApplicationDefault(),
        options={"databaseURL": database_url},
        name=f"database-interaction-test-{uuid4().hex}",
    )
    try:
        yield FirebaseDatabase(
            database_url,
            max_transcription_jobs_per_user=2,
            firebase_app=app,
        )
    finally:
        firebase_admin.delete_app(app)


def test_server_and_transcription_job_crud_round_trip(database):
    suffix = uuid4().hex
    server_id = f"integration-test-{suffix}"
    user_uid = f"integration-test-user-{suffix}"
    transcription_id = None
    server_created = False
    cleanup_results = []
    client_server_reference = firebase_db.reference(
        f"/Client_Available_Pytacte_Servers/{server_id}",
        app=database.firebase_app,
        url=database.database_url,
    )
    server_data = ServerAvailabilityDTO(
        server_id=server_id,
        server_address="127.0.0.1:1",
        tls=False,
        cpu_usage=0.0,
        load_balancer=False,
    )

    try:
        created_server = database.create_server_availability(server_data)
        assert created_server[0], created_server[1]
        server_created = True

        stored_server = database.get_server_availability(server_id)
        assert stored_server is not None
        assert stored_server.server_id == server_id
        assert isinstance(stored_server.last_heartbeat, int)

        stored_client_server = client_server_reference.get()
        assert stored_client_server is not None
        assert stored_client_server["server_id"] == server_id
        assert stored_client_server["server_address"] == server_data.server_address
        assert stored_client_server["tls"] is server_data.tls
        assert stored_client_server["cpu_usage"] == server_data.cpu_usage

        # Set an older value first so the heartbeat API visibly changes the record.
        firebase_db.reference(
            f"/ServerAvailability/{server_id}",
            app=database.firebase_app,
            url=database.database_url,
        ).update({"last_heartbeat": 20000101})

        heartbeat_data = ServerAvailabilityDTO(
            server_id=server_id,
            server_address=server_data.server_address,
            tls=server_data.tls,
            cpu_usage=31.5,
            load_balancer=server_data.load_balancer,
        )
        updated_server = database.update_server_availability_heartbeat(
            heartbeat_data
        )
        assert updated_server[0], updated_server[1]
        stored_server = database.get_server_availability(server_id)
        stored_client_server = client_server_reference.get()
        expected_heartbeat = int(datetime.now(UTC).strftime("%Y%m%d%H%M"))
        assert stored_server.last_heartbeat == expected_heartbeat
        assert stored_server.last_heartbeat != 20000101
        assert stored_server.cpu_usage == 31.5
        assert stored_client_server["cpu_usage"] == 31.5

        updated_server_data = ServerAvailabilityDTO(
            server_id=server_id,
            server_address="127.0.0.1:2",
            tls=True,
            cpu_usage=18.75,
            load_balancer=False,
            last_heartbeat=stored_server.last_heartbeat,
        )
        updated_server_result = database.update_server_availability(
            updated_server_data
        )
        assert updated_server_result[0], updated_server_result[1]

        stored_server = database.get_server_availability(server_id)
        stored_client_server = client_server_reference.get()
        assert stored_server is not None
        assert stored_server.server_address == "127.0.0.1:2"
        assert stored_server.tls is True
        assert stored_server.cpu_usage == 18.75
        assert stored_client_server["server_id"] == server_id
        assert stored_client_server["server_address"] == "127.0.0.1:2"
        assert stored_client_server["tls"] is True
        assert stored_client_server["cpu_usage"] == 18.75

        created_job = database.create_transcription_job(user_uid, server_id)
        assert created_job[0], created_job[1]
        transcription_id = created_job[1].transcription_id

        stored_job = database.get_transcription_job(transcription_id)
        assert stored_job is not None
        assert stored_job.transcription_id == transcription_id
        assert stored_job.uuid == user_uid

        updated_job = database.update_transcription_job_heartbeat(transcription_id)
        assert updated_job[0], updated_job[1]
        stored_job = database.get_transcription_job(transcription_id)
        assert stored_job.last_heartbeat == expected_heartbeat

        print(f"Created and updated server record: /ServerAvailability/{server_id}")
        print(f"Created and updated transcription record: /TranscriptionJobs/{transcription_id}")
        print(f"Updated heartbeat value: {expected_heartbeat}")
    finally:
        if transcription_id is not None:
            cleanup_results.append(
                database.delete_transcription_job(transcription_id)
            )
        client_server_reference.delete()
        if server_created:
            cleanup_results.append(database.delete_server_availability(server_id))

    for successful, message in cleanup_results:
        assert successful, message
    if transcription_id is not None:
        assert database.get_transcription_job(transcription_id) is None
    if server_created:
        assert database.get_server_availability(server_id) is None
    assert client_server_reference.get() is None


def test_sort_servers_by_least_cpu_usage_keeps_lowest_50(database):
    random = Random(20261116)
    distinct_cpu_values = [
        value / 10000
        for value in random.sample(range(1, 1_000_001), 90)
    ]
    cpu_values = distinct_cpu_values + distinct_cpu_values[:10]
    random.shuffle(cpu_values)
    expected_cpu_values = sorted(cpu_values)[:50]

    suffix = uuid4().hex
    server_ids = [f"sort-test-{suffix}-{index:03d}" for index in range(100)]
    server_collection = firebase_db.reference(
        "/ServerAvailability",
        app=database.firebase_app,
        url=database.database_url,
    )
    client_collection = firebase_db.reference(
        "/Client_Available_Pytacte_Servers",
        app=database.firebase_app,
        url=database.database_url,
    )

    existing_servers = server_collection.order_by_key().limit_to_first(1).get()
    existing_clients = client_collection.order_by_key().limit_to_first(1).get()
    if existing_servers or existing_clients:
        pytest.skip(
            "Run against an empty ServerAvailability and "
            "Client_Available_Pytacte_Servers database; sorting prunes the client table"
        )

    test_records = {
        server_id: {
            "server_id": server_id,
            "server_address": f"127.0.0.1:{20000 + index}",
            "load_balancer": False,
            "tls": False,
            "cpu_usage": cpu_values[index],
            "last_heartbeat": int(datetime.now(UTC).strftime("%Y%m%d%H%M")),
        }
        for index, server_id in enumerate(server_ids)
    }

    try:
        server_collection.update(test_records)

        seeded_ids = [
            server_id
            for server_id in server_ids
            if server_collection.child(server_id).get() is not None
        ]
        assert len(seeded_ids) == 100, (
            f"Expected to insert 100 test servers, found {len(seeded_ids)}"
        )

        process = get_context("spawn").Process(
            target=_run_server_sort_in_process,
            args=(database.database_url,),
        )
        process.start()
        process.join(timeout=60)
        if process.is_alive():
            process.terminate()
            process.join()
            pytest.fail(
                "sort_severs_by_least_cpu_usage did not finish within 60 seconds"
            )
        assert process.exitcode == 0, (
            "sort_severs_by_least_cpu_usage subprocess exited with "
            f"status {process.exitcode}"
        )

        actual_client_records = [
            client_collection.child(server_id).get()
            for server_id in server_ids
        ]
        actual_cpu_values = sorted(
            record["cpu_usage"]
            for record in actual_client_records
            if record is not None
        )
        assert len(actual_cpu_values) == 50, (
            f"Expected 50 test servers in Client_Available_Pytacte_Servers, "
            f"found {len(actual_cpu_values)}"
        )
        assert actual_cpu_values == expected_cpu_values
    finally:
        server_collection.update({server_id: None for server_id in server_ids})
        client_collection.update({server_id: None for server_id in server_ids})


def test_load_balancer_rebalances_after_server_load_increases(database):
    suffix = uuid4().hex
    initial_server_id = f"load-balance-test-{suffix}-initial"
    added_server_ids = [
        f"load-balance-test-{suffix}-added-{index}" for index in range(3)
    ]
    server_ids = [initial_server_id, *added_server_ids]
    server_collection = firebase_db.reference(
        "/ServerAvailability",
        app=database.firebase_app,
        url=database.database_url,
    )
    client_collection = firebase_db.reference(
        "/Client_Available_Pytacte_Servers",
        app=database.firebase_app,
        url=database.database_url,
    )

    if (
        server_collection.order_by_key().limit_to_first(1).get()
        or client_collection.order_by_key().limit_to_first(1).get()
    ):
        pytest.skip(
            "Run against empty server collections; sorting prunes the entire "
            "client-available collection"
        )

    heartbeat = int(datetime.now(UTC).strftime("%Y%m%d%H%M"))
    initial_record = {
        "server_id": initial_server_id,
        "server_address": "127.0.0.1:21000",
        "load_balancer": False,
        "tls": False,
        "cpu_usage": 1.0,
        "last_heartbeat": heartbeat,
    }
    added_cpu_values = [10.0, 20.0, 30.0]
    added_records = {
        server_id: {
            "server_id": server_id,
            "server_address": f"127.0.0.1:{21001 + index}",
            "load_balancer": False,
            "tls": False,
            "cpu_usage": cpu_usage,
            "last_heartbeat": heartbeat,
        }
        for index, (server_id, cpu_usage) in enumerate(
            zip(added_server_ids, added_cpu_values, strict=True)
        )
    }

    try:
        server_collection.child(initial_server_id).set(initial_record)
        assert server_collection.child(initial_server_id).get()["cpu_usage"] == 1.0

        server_collection.child(initial_server_id).update({"cpu_usage": 95.0})
        assert server_collection.child(initial_server_id).get()["cpu_usage"] == 95.0

        server_collection.update(added_records)
        assert all(server_collection.child(server_id).get() for server_id in added_server_ids)

        load_balancer = LoadBalancer.__new__(LoadBalancer)
        load_balancer.database_connection = database
        load_balancer.sort_servers_by_cpu()

        client_records = {
            server_id: client_collection.child(server_id).get()
            for server_id in server_ids
        }
        available_ids = {
            server_id for server_id, record in client_records.items() if record is not None
        }
        expected_available_ids = set(added_server_ids[:2])

        assert available_ids == expected_available_ids
        assert sorted(
            client_records[server_id]["cpu_usage"] for server_id in available_ids
        ) == [10.0, 20.0]
    finally:
        server_collection.update({server_id: None for server_id in server_ids})
        client_collection.update({server_id: None for server_id in server_ids})


def test_delete_expired_servers_removes_expired_and_preserves_fresh(database):
    suffix = uuid4().hex
    server_ids = [f"expired-test-{suffix}-{index:03d}" for index in range(100)]
    fresh_server_ids = [f"fresh-test-{suffix}-{index:03d}" for index in range(10)]
    now = datetime.now(UTC)
    server_records = {
        server_id: {
            "server_id": server_id,
            "server_address": f"127.0.0.1:{10000 + index}",
            "load_balancer": False,
            "tls": False,
            "cpu_usage": 0.0,
            # Reuse timestamps so duplicate heartbeat values are covered.
            "last_heartbeat": int(
                (now - timedelta(minutes=6 + index // 4)).strftime(
                    "%Y%m%d%H%M"
                )
            ),
        }
        for index, server_id in enumerate(server_ids)
    }
    fresh_server_records = {
        server_id: {
            "server_id": server_id,
            "server_address": f"127.0.0.1:{11000 + index}",
            "load_balancer": False,
            "tls": False,
            "cpu_usage": 0.0,
            "last_heartbeat": int(now.strftime("%Y%m%d%H%M")),
        }
        for index, server_id in enumerate(fresh_server_ids)
    }
    test_records = {**server_records, **fresh_server_records}
    collection = firebase_db.reference(
        "/ServerAvailability",
        app=database.firebase_app,
        url=database.database_url,
    )

    try:
        collection.update(test_records)

        seeded_server_ids = [
            server_id
            for server_id in test_records
            if collection.child(server_id).get() is not None
        ]
        assert len(seeded_server_ids) == len(test_records), (
            f"Expected to seed 100 expired and 10 fresh test servers, but only "
            f"{len(seeded_server_ids)} of {len(test_records)} were present"
        )
        print("Verified 100 expired and 10 fresh test servers before cleanup")

        exact_timestamp_match = (
            collection.order_by_child("last_heartbeat")
            .start_at(server_records[server_ids[0]]["last_heartbeat"])
            .limit_to_first(1)
            .end_at(server_records[server_ids[0]]["last_heartbeat"])
            .get()
        )
        print(
            "Exact heartbeat query returned: "
            f"{list(exact_timestamp_match) if exact_timestamp_match else []}"
        )

        result = database.delete_expired_servers()
        print(f"delete_expired_servers() returned: {result}")
        assert result[0], result[1]

        remaining_expired_server_ids = [
            server_id
            for server_id in server_ids
            if collection.child(server_id).get() is not None
        ]
        remaining_fresh_server_ids = [
            server_id
            for server_id in fresh_server_ids
            if collection.child(server_id).get() is not None
        ]
        print(
            "After one delete_expired_servers() call: "
            f"{len(server_ids) - len(remaining_expired_server_ids)} expired test "
            f"servers deleted, {len(remaining_expired_server_ids)} remain, "
            f"{len(remaining_fresh_server_ids)} of 10 fresh test servers remain"
        )
        assert not remaining_expired_server_ids, (
            f"One cleanup call left {len(remaining_expired_server_ids)} of the "
            f"100 expired test servers: {remaining_expired_server_ids[:10]}"
        )
        assert set(remaining_fresh_server_ids) == set(fresh_server_ids), (
            "Cleanup removed or changed fresh test servers: "
            f"{set(fresh_server_ids) - set(remaining_fresh_server_ids)}"
        )
    finally:
        # Clean up test records left behind by the method or a failed assertion.
        collection.update({server_id: None for server_id in test_records})


def test_delete_expired_items_removes_server_from_client_collection(database):
    suffix = uuid4().hex
    server_id = f"expired-client-server-test-{suffix}"
    cutoff = int(
        (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y%m%d%H%M")
    )

    # delete_expired_items() sweeps all expired jobs and servers, so don't run
    # this live test if unrelated stale records already exist in the database.
    for collection_name in ("ServerAvailability", "TranscriptionJobs"):
        expired_items = (
            firebase_db.reference(
                f"/{collection_name}",
                app=database.firebase_app,
                url=database.database_url,
            )
            .order_by_child("last_heartbeat")
            .end_at(cutoff)
            .limit_to_first(1)
            .get()
        )
        if expired_items:
            pytest.skip(
                f"Refusing global cleanup: expired records already exist in "
                f"{collection_name}"
            )

    job_collection = firebase_db.reference(
        "/TranscriptionJobs",
        app=database.firebase_app,
        url=database.database_url,
    )
    client_collection = firebase_db.reference(
        "/Client_Available_Pytacte_Servers",
        app=database.firebase_app,
        url=database.database_url,
    )
    last_id = None
    while True:
        jobs = (
            job_collection.order_by_key().limit_to_first(20).get()
            if last_id is None
            else job_collection.order_by_key().start_at(last_id).limit_to_first(20).get()
        )
        if not isinstance(jobs, dict) or not jobs:
            break

        page_last_id = None
        for transcription_id, record in jobs.items():
            page_last_id = transcription_id
            if transcription_id == last_id:
                continue
            job_server_id = record.get("server_id") if isinstance(record, dict) else None
            if (
                not isinstance(job_server_id, str)
                or not job_server_id
                or client_collection.child(job_server_id).get() is None
            ):
                pytest.skip(
                    "Refusing global cleanup: orphan transcription jobs already "
                    f"exist (for example {transcription_id})"
                )

        if page_last_id == last_id:
            break
        last_id = page_last_id

    server_collection = firebase_db.reference(
        "/ServerAvailability",
        app=database.firebase_app,
        url=database.database_url,
    )
    client_collection = firebase_db.reference(
        "/Client_Available_Pytacte_Servers",
        app=database.firebase_app,
        url=database.database_url,
    )
    server_record = {
        "server_id": server_id,
        "server_address": "127.0.0.1:1",
        "load_balancer": False,
        "tls": False,
        "cpu_usage": 0.0,
        "last_heartbeat": int(
            (datetime.now(UTC) - timedelta(minutes=10)).strftime("%Y%m%d%H%M")
        ),
    }
    client_record = {
        "server_id": server_id,
        "server_address": server_record["server_address"],
        "tls": server_record["tls"],
        "cpu_usage": server_record["cpu_usage"],
    }

    try:
        server_collection.child(server_id).set(server_record)
        client_collection.child(server_id).set(client_record)
        assert server_collection.child(server_id).get() == server_record
        assert client_collection.child(server_id).get() == client_record

        load_balancer = LoadBalancer.__new__(LoadBalancer)
        load_balancer.database_connection = database
        result = load_balancer.delete_expired_items()

        assert result[0] == [True, True, True, True], result
        assert server_collection.child(server_id).get() is None
        assert client_collection.child(server_id).get() is None
    finally:
        server_collection.child(server_id).delete()
        client_collection.child(server_id).delete()


def test_delete_expired_server_with_only_last_heartbeat(database):
    server_id = f"expired-single-field-test-{uuid4().hex}"
    collection = firebase_db.reference(
        "/ServerAvailability",
        app=database.firebase_app,
        url=database.database_url,
    )
    expired_record = {
        "last_heartbeat": int(
            (datetime.now(UTC) - timedelta(minutes=10)).strftime("%Y%m%d%H%M")
        )
    }

    try:
        collection.child(server_id).set(expired_record)
        assert collection.child(server_id).get() == expired_record

        result = database.delete_expired_servers()

        assert result[0], result[1]
        assert collection.child(server_id).get() is None
    finally:
        collection.child(server_id).delete()


def test_delete_expired_transcription_jobs_preserves_fresh_jobs(database):
    suffix = uuid4().hex
    expired_ids = [f"expired-job-test-{suffix}-{index:03d}" for index in range(100)]
    fresh_ids = [f"fresh-job-test-{suffix}-{index:03d}" for index in range(10)]
    now = datetime.now(UTC)
    expired_records = {
        transcription_id: {
            "transcription_id": transcription_id,
            "uuid": f"test-user-{suffix}",
            "server_id": f"test-server-{suffix}",
            "last_heartbeat": int(
                (now - timedelta(minutes=6 + index // 4)).strftime("%Y%m%d%H%M")
            ),
        }
        for index, transcription_id in enumerate(expired_ids)
    }
    fresh_records = {
        transcription_id: {
            "transcription_id": transcription_id,
            "uuid": f"test-user-{suffix}",
            "server_id": f"test-server-{suffix}",
            "last_heartbeat": int(now.strftime("%Y%m%d%H%M")),
        }
        for transcription_id in fresh_ids
    }
    test_records = {**expired_records, **fresh_records}
    collection = firebase_db.reference(
        "/TranscriptionJobs",
        app=database.firebase_app,
        url=database.database_url,
    )

    try:
        collection.update(test_records)

        seeded_ids = [
            transcription_id
            for transcription_id in test_records
            if collection.child(transcription_id).get() is not None
        ]
        assert len(seeded_ids) == len(test_records), (
            f"Expected to seed 100 expired and 10 fresh jobs, but only "
            f"{len(seeded_ids)} of {len(test_records)} were present"
        )
        print("Verified 100 expired and 10 fresh test jobs before cleanup")

        result = database.delete_expired_transcription_jobs()
        print(f"delete_expired_transcription_jobs() returned: {result}")
        assert result[0], result[1]

        remaining_expired_ids = [
            transcription_id
            for transcription_id in expired_ids
            if collection.child(transcription_id).get() is not None
        ]
        remaining_fresh_ids = [
            transcription_id
            for transcription_id in fresh_ids
            if collection.child(transcription_id).get() is not None
        ]
        print(
            "After one delete_expired_transcription_jobs() call: "
            f"{len(expired_ids) - len(remaining_expired_ids)} expired test jobs "
            f"deleted, {len(remaining_expired_ids)} remain, "
            f"{len(remaining_fresh_ids)} of 10 fresh test jobs remain"
        )
        assert not remaining_expired_ids, (
            f"Cleanup left {len(remaining_expired_ids)} of the 100 expired test "
            f"jobs: {remaining_expired_ids[:10]}"
        )
        assert set(remaining_fresh_ids) == set(fresh_ids), (
            f"Cleanup removed or changed fresh test jobs: "
            f"{set(fresh_ids) - set(remaining_fresh_ids)}"
        )
    finally:
        collection.update({transcription_id: None for transcription_id in test_records})


def test_delete_orphan_transcription_jobs_removes_only_jobs_with_unavailable_servers(
    database,
):
    suffix = uuid4().hex
    job_ids = [f"orphan-job-test-{suffix}-{index:03d}" for index in range(25)]
    server_ids = [f"orphan-job-server-test-{suffix}-{index:03d}" for index in range(25)]
    job_collection = firebase_db.reference(
        "/TranscriptionJobs",
        app=database.firebase_app,
        url=database.database_url,
    )
    client_server_collection = firebase_db.reference(
        "/Client_Available_Pytacte_Servers",
        app=database.firebase_app,
        url=database.database_url,
    )

    # The cleanup scans the whole live table, so don't let the test remove
    # unrelated orphan jobs that were already present before it started.
    existing_orphans = []
    last_id = None
    while True:
        existing_jobs = (
            job_collection.order_by_key().limit_to_first(20).get()
            if last_id is None
            else job_collection.order_by_key().start_at(last_id).limit_to_first(20).get()
        )
        if not isinstance(existing_jobs, dict) or not existing_jobs:
            break

        page_last_id = None
        for transcription_id, record in existing_jobs.items():
            page_last_id = transcription_id
            if transcription_id == last_id:
                continue
            server_id = record.get("server_id") if isinstance(record, dict) else None
            if (
                not isinstance(server_id, str)
                or not server_id
                or client_server_collection.child(server_id).get() is None
            ):
                existing_orphans.append(transcription_id)

        if page_last_id == last_id:
            break
        last_id = page_last_id

    if existing_orphans:
        pytest.skip(
            "Refusing global orphan cleanup because unrelated orphan jobs already "
            f"exist: {existing_orphans[:5]}"
        )

    retained_ids = set(job_ids[1::2])
    test_jobs = {
        job_id: {
            "transcription_id": job_id,
            "uuid": f"orphan-job-user-{suffix}",
            "server_id": server_ids[index],
        }
        for index, job_id in enumerate(job_ids)
    }
    available_server_records = {
        server_ids[index]: {
            "server_id": server_ids[index],
            "server_address": f"127.0.0.1:{22000 + index}",
            "tls": False,
            "cpu_usage": 0.0,
        }
        for index in range(1, len(server_ids), 2)
    }

    try:
        client_server_collection.update(available_server_records)
        job_collection.update(test_jobs)

        seeded_ids = [
            job_id for job_id in job_ids if job_collection.child(job_id).get() is not None
        ]
        assert set(seeded_ids) == set(job_ids)

        result = database.delete_orphan_transcription_jobs()
        assert result[0], result[1]

        remaining_ids = {
            job_id for job_id in job_ids if job_collection.child(job_id).get() is not None
        }
        assert remaining_ids == retained_ids
        assert all(
            client_server_collection.child(server_ids[index]).get() is not None
            for index in range(1, len(server_ids), 2)
        )
    finally:
        job_collection.update({job_id: None for job_id in job_ids})
        client_server_collection.update(
            {server_id: None for server_id in available_server_records}
        )
