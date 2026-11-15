"""Firebase Realtime Database access for server-owned records."""

from datetime import datetime, timezone
from typing import Any, ClassVar
from urllib.parse import urlsplit

from firebase_admin import App, db
from firebase_admin.exceptions import FirebaseError


class FirebaseDatabase:
    """Encapsulate CRUD operations for load-balancer database records.

    The Admin SDK is used so server writes can update fields that client
    security rules mark as read-only. ``database_url`` must be the Realtime
    Database instance URL for the Firebase project.
    """

    TRANSCRIPTION_JOB_FIELDS: ClassVar = {
        "transcription_id": str,
        "uuid": str,
        "server_id": str,
        "last_heartbeat": int,
    }
    SERVER_AVAILABILITY_FIELDS: ClassVar = {
        "server_id": str,
        "server_address": str,
        "tls": bool,
        "cpu_usage": (int, float),
        "ram_usage": (int, float),
        "load_balancer": bool,
        "last_heartbeat": int,
    }

    def __init__(
        self,
        database_url: str,
        max_transcription_jobs_per_user: int,
        firebase_app: App | None = None,
    ):
        self.__validate_database_url__(database_url)
        if (
            isinstance(max_transcription_jobs_per_user, bool)
            or not isinstance(max_transcription_jobs_per_user, int)
            or max_transcription_jobs_per_user < 0
        ):
            raise ValueError(
                "max_transcription_jobs_per_user must be a non-negative integer"
            )
        self.database_url = database_url
        self.max_transcription_jobs_per_user = max_transcription_jobs_per_user
        self.firebase_app = firebase_app

    def __validate_database_url__(self, database_url: str) -> None:
        if not isinstance(database_url, str) or not database_url:
            raise ValueError("database_url must be a non-empty URL string")
        if database_url != database_url.strip():
            raise ValueError("database_url must not contain surrounding whitespace")

        try:
            parsed_url = urlsplit(database_url)
            hostname = parsed_url.hostname
            _ = parsed_url.port
        except ValueError as error:
            raise ValueError("database_url is malformed") from error

        if (
            parsed_url.scheme not in {"https", "http"}
            or hostname is None
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.path not in {"", "/"}
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("database_url must be an absolute Realtime Database URL")

        is_firebase_host = hostname.endswith(
            (".firebaseio.com", ".firebasedatabase.app")
        )
        is_local_emulator = hostname in {"localhost", "127.0.0.1", "::1"}
        if not is_firebase_host and not is_local_emulator:
            raise ValueError("database_url must point to a Firebase Realtime Database")
        if parsed_url.scheme == "http" and not is_local_emulator:
            raise ValueError(
                "HTTP is only allowed for a local Realtime Database emulator"
            )
        
        



    # -------------------------------
    #   TranscriptionJobs (table)
    # -------------------------------

    def create_transcription_job(self, user_uid: str) -> tuple[bool, str]:
        """Create a job with a Firebase-generated ID, if the user is under quota."""
        try:
            server_availability = self.get_server_availability()
            if not isinstance(server_availability, dict):
                return False, "No server availability records are available"
            server_id = server_availability.get("server_id")
            if not isinstance(server_id, str) or not server_id:
                return False, "The first server availability record has no valid server_id"

            data = {"uuid": user_uid, "server_id": server_id}
            self.__validate_data__(data, self.TRANSCRIPTION_JOB_FIELDS)
            job_count = self.__count_transcription_jobs_for_user__(user_uid)
            if job_count >= self.max_transcription_jobs_per_user:
                return (
                    False,
                    ("User has reached the maximum number of transcription jobs "
                    f"({self.max_transcription_jobs_per_user})"),
                )

            collection = db.reference(
                "/TranscriptionJobs", app=self.firebase_app, url=self.database_url
            )
            reference = collection.push()
            transcription_id = reference.key
            if transcription_id is None:
                return False, "Firebase did not generate a transcription ID"

            record = {**data, "transcription_id": transcription_id}
            reference.set(record)
            return True, f"Transcription job {transcription_id} created"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to create transcription job: {error}"

    def get_transcription_job(self, transcription_id: str) -> dict[str, Any] | None:
        """Return a transcription job or ``None`` when it does not exist."""
        self.__validate_record_id__(transcription_id)
        return self.__reference__("TranscriptionJobs", transcription_id).get()

    def update_transcription_job_heartbeat(
        self, transcription_id: str
    ) -> tuple[bool, str]:
        """Update a job's heartbeat to today's UTC date in YYYYMMdd form."""
        try:
            self.__validate_record_id__(transcription_id)
            heartbeat_date = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
            self.__update__(
                "TranscriptionJobs",
                transcription_id,
                {"last_heartbeat": heartbeat_date},
            )
            return True, f"Heartbeat updated for transcription job {transcription_id}"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to update transcription job heartbeat: {error}"

    def delete_transcription_job(self, transcription_id: str) -> tuple[bool, str]:
        """Delete a transcription job."""
        try:
            self.__validate_record_id__(transcription_id)
            self.__reference__("TranscriptionJobs", transcription_id).delete()
            return True, f"Transcription job {transcription_id} deleted"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to delete transcription job: {error}"

    # --------------------------------------------------------
    
    
    
    
    # -------------------------------
    #   ServerAvailability (table)
    # -------------------------------

    def create_server_availability(
        self, server_id: str, data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Create a server availability record, rejecting an existing ID."""
        try:
            
            self.__validate_record_id__(server_id)
            data = {
                **data,
                "last_heartbeat": int(datetime.now(timezone.utc).strftime("%Y%m%d")),
            }
            self.__validate_data__(data, self.SERVER_AVAILABILITY_FIELDS, complete=True)
            if data["server_id"] != server_id:
                return False, "server_id must match the record ID"

            reference = self.__reference__("ServerAvailability", server_id)
            if reference.get() is not None:
                return False, f"Server {server_id!r} already exists"
            reference.set(data)
            return True, f"Server availability record {server_id} created"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to create server availability record: {error}"

    def get_server_availability(
        self, server_id: str
    ) -> dict[str, Any] | None:
        """Return one server record, or the first record when no ID is given."""
        if server_id is not None:
            self.__validate_record_id__(server_id)
            return self.__reference__("ServerAvailability", server_id).get()

        records = db.reference(
            "/ServerAvailability", app=self.firebase_app, url=self.database_url
        ).order_by_key().limit_to_first(1).get()
        if not isinstance(records, dict) or not records:
            return None
        return next(iter(records.values()))

    def update_server_availability_heartbeat(
        self, server_id: str
    ) -> tuple[bool, str]:
        """Update a server's heartbeat to today's UTC date in YYYYMMdd form."""
        try:
            self.__validate_record_id__(server_id)
            heartbeat_date = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
            self.__update__(
                "ServerAvailability",
                server_id,
                {"last_heartbeat": heartbeat_date},
            )
            return True, f"Heartbeat updated for server {server_id}"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to update server availability heartbeat: {error}"

    def delete_server_availability(self, server_id: str) -> tuple[bool, str]:
        """Delete a server availability record."""
        try:
            self.__validate_record_id__(server_id)
            self.__reference__("ServerAvailability", server_id).delete()
            return True, f"Server availability record {server_id} deleted"
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to delete server availability record: {error}"
        
        
    #-------------------------------------------------------------------
    
    
    
    
    
    
    
    
    
    #-------------------------------
    #   Producer Methods
    #-------------------------------

    def __reference__(self, collection: str, record_id: str):
        return db.reference(
            f"/{collection}/{record_id}",
            app=self.firebase_app,
            url=self.database_url,
        )

    def __update__(
        self, collection: str, record_id: str, changes: dict[str, Any]
    ) -> dict[str, Any]:
        if not changes:
            raise ValueError("At least one field must be provided for an update")
        reference = self.__reference__(collection, record_id)
        if reference.get() is None:
            raise KeyError(f"{collection} record {record_id!r} does not exist")
        reference.update(changes)
        return reference.get()

    def __count_transcription_jobs_for_user__(self, user_uuid: str) -> int:
        jobs = db.reference(
            "/TranscriptionJobs", app=self.firebase_app, url=self.database_url
        ).get()
        if not isinstance(jobs, dict):
            return 0
        return sum(
            1
            for job in jobs.values()
            if isinstance(job, dict) and job.get("uuid") == user_uuid
        )

    def __validate_record_id__(self, record_id: str) -> None:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Record ID must be a non-empty string")
        if any(character in record_id for character in ".#$[]/"):
            raise ValueError(
                "Record ID contains a character forbidden in Firebase keys"
            )

    def __validate_data__(
        self, data: dict[str, Any], fields: dict[str, Any], complete: bool = False
    ) -> None:
        if not isinstance(data, dict):
            raise TypeError("Record data must be a dictionary")
        if complete and fields.keys() - data.keys():
            missing = ", ".join(sorted(fields.keys() - data.keys()))
            raise ValueError(f"Missing required fields: {missing}")
        unknown = data.keys() - fields.keys()
        if unknown:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}")
        for name, value in data.items():
            expected_type = fields[name]
            if isinstance(value, bool) and expected_type in (
                (int, float),
                (float, int),
            ):
                raise TypeError(f"{name} must be a number, not a boolean")
            if not isinstance(value, expected_type):
                raise TypeError(f"{name} has an invalid value type")
            
            
    #--------------------------------------------------------
