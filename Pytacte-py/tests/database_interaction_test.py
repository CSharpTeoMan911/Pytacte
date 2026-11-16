"""Live Firebase Realtime Database CRUD integration test.

Run with:
    pytest tests/database_interaction_test.py \
        --database-url=https://your-project-default-rtdb.europe-west1.firebasedatabase.app/

Firebase Admin credentials must also be available through Application Default
Credentials (for example, GOOGLE_APPLICATION_CREDENTIALS).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import firebase_admin
import pytest
from firebase_admin import credentials
from firebase_admin import db as firebase_db

from firebase.firebase_database import FirebaseDatabase, ServerAvailabilityDTO


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
    server_data = ServerAvailabilityDTO(
        server_id=server_id,
        server_address="127.0.0.1:1",
        tls=False,
        cpu_usage=0.0,
        ram_usage=0.0,
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

        # Set an older value first so the heartbeat API visibly changes the record.
        firebase_db.reference(
            f"/ServerAvailability/{server_id}",
            app=database.firebase_app,
            url=database.database_url,
        ).update({"last_heartbeat": 20000101})

        updated_server = database.update_server_availability_heartbeat(
            server_id, cpu_usage=31.5, ram_usage=47.25
        )
        assert updated_server[0], updated_server[1]
        stored_server = database.get_server_availability(server_id)
        expected_heartbeat = int(datetime.now(UTC).strftime("%Y%m%d%H%M"))
        assert stored_server.last_heartbeat == expected_heartbeat
        assert stored_server.last_heartbeat != 20000101
        assert stored_server.cpu_usage == 31.5
        assert stored_server.ram_usage == 47.25

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
        if server_created:
            cleanup_results.append(database.delete_server_availability(server_id))

    for successful, message in cleanup_results:
        assert successful, message
    if transcription_id is not None:
        assert database.get_transcription_job(transcription_id) is None
    if server_created:
        assert database.get_server_availability(server_id) is None


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
            "ram_usage": 0.0,
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
            "ram_usage": 0.0,
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
