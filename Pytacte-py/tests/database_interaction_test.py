"""Live Firebase Realtime Database CRUD integration test.

Run with:
    pytest tests/database_interaction_test.py \
        --database-url=https://your-project-default-rtdb.europe-west1.firebasedatabase.app/

Firebase Admin credentials must also be available through Application Default
Credentials (for example, GOOGLE_APPLICATION_CREDENTIALS).
"""

from datetime import datetime, timezone
from uuid import uuid4

import firebase_admin
import pytest
from firebase_admin import credentials, db as firebase_db

from firebase.firebase_database import FirebaseDatabase


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
    server_data = {
        "server_id": server_id,
        "server_address": "127.0.0.1:1",
        "tls": False,
        "cpu_usage": 0.0,
        "ram_usage": 0.0,
        "load_balancer": False,
    }

    try:
        created_server = database.create_server_availability(server_id, server_data)
        assert created_server[0], created_server[1]
        server_created = True

        stored_server = database.get_server_availability(server_id)
        assert stored_server is not None
        assert stored_server["server_id"] == server_id
        assert isinstance(stored_server["last_heartbeat"], int)

        # Set an older value first so the heartbeat API visibly changes the record.
        firebase_db.reference(
            f"/ServerAvailability/{server_id}",
            app=database.firebase_app,
            url=database.database_url,
        ).update({"last_heartbeat": 20000101})

        updated_server = database.update_server_availability_heartbeat(server_id)
        assert updated_server[0], updated_server[1]
        stored_server = database.get_server_availability(server_id)
        expected_heartbeat = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
        assert stored_server["last_heartbeat"] == expected_heartbeat
        assert stored_server["last_heartbeat"] != 20000101

        created_job = database.create_transcription_job(user_uid)
        assert created_job[0], created_job[1]
        transcription_id = created_job[1].rsplit(" ", 2)[1]

        stored_job = database.get_transcription_job(transcription_id)
        assert stored_job is not None
        assert stored_job["transcription_id"] == transcription_id
        assert stored_job["uuid"] == user_uid

        updated_job = database.update_transcription_job_heartbeat(transcription_id)
        assert updated_job[0], updated_job[1]
        stored_job = database.get_transcription_job(transcription_id)
        assert stored_job["last_heartbeat"] == expected_heartbeat

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
