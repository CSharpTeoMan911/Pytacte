"""Firebase Realtime Database access for server-owned records."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from firebase_admin import App, db
from firebase_admin.exceptions import FirebaseError


@dataclass
class TranscriptionJobsDTO:
    """DTO for one record in the ``TranscriptionJobs`` table."""

    transcription_id: str
    uuid: str
    server_id: str
    last_heartbeat: int | None = None

    def __post_init__(self) -> None:
        if not self.transcription_id:
            raise ValueError("transcription_id must not be empty")
        if not self.uuid:
            raise ValueError("uuid must not be empty")
        if not self.server_id:
            raise ValueError("server_id must not be empty")
        if self.last_heartbeat is not None and (
            isinstance(self.last_heartbeat, bool)
            or not isinstance(self.last_heartbeat, int)
        ):
            raise ValueError("last_heartbeat must be an integer timestamp")

    def to_record(self) -> dict[str, str | int]:
        record: dict[str, str | int] = {
            "transcription_id": self.transcription_id,
            "uuid": self.uuid,
            "server_id": self.server_id,
        }
        if self.last_heartbeat is not None:
            record["last_heartbeat"] = self.last_heartbeat
        return record


@dataclass
class ServerAvailabilityDTO:
    """DTO for one record in the ``ServerAvailability`` table."""

    server_id: str
    server_address: str
    load_balancer: bool
    tls: bool
    cpu_usage: float
    ram_usage: float
    last_heartbeat: int | None = None

    def __post_init__(self) -> None:
        if not self.server_id:
            raise ValueError("server_id must not be empty")
        if not self.server_address:
            raise ValueError("server_address must not be empty")
        if not isinstance(self.load_balancer, bool):
            raise TypeError("load_balancer must be a boolean")
        if not isinstance(self.tls, bool):
            raise TypeError("tls must be a boolean")
        if isinstance(self.cpu_usage, bool) or not isinstance(
            self.cpu_usage, (int, float)
        ):
            raise TypeError("cpu_usage must be a number")
        if isinstance(self.ram_usage, bool) or not isinstance(
            self.ram_usage, (int, float)
        ):
            raise TypeError("ram_usage must be a number")
        self.cpu_usage = float(self.cpu_usage)
        self.ram_usage = float(self.ram_usage)
        if self.last_heartbeat is not None and (
            isinstance(self.last_heartbeat, bool)
            or not isinstance(self.last_heartbeat, int)
        ):
            raise ValueError("last_heartbeat must be an integer timestamp")

    def to_record(self) -> dict[str, str | int | float | bool]:
        record: dict[str, str | int | float | bool] = {
            "server_id": self.server_id,
            "server_address": self.server_address,
            "load_balancer": self.load_balancer,
            "tls": self.tls,
            "cpu_usage": self.cpu_usage,
            "ram_usage": self.ram_usage,
        }
        if self.last_heartbeat is not None:
            record["last_heartbeat"] = self.last_heartbeat
        return record


class FirebaseDatabase:
    """Encapsulate CRUD operations for load-balancer database records."""

    def __init__(
        self,
        database_url: str,
        max_transcription_jobs_per_user: int,
        firebase_app: App | None = None,
    ):
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
    # TranscriptionJobs table
    # -------------------------------

    def create_transcription_job(
        self, user_uid: str, server_id: str
    ) -> tuple[bool, TranscriptionJobsDTO | str]:
        """Create a job with a Firebase-generated ID, if its user is under quota."""
        try:
            if not isinstance(user_uid, str) or not user_uid:
                raise ValueError("user_uid must be a non-empty string")
            self.__validate_record_id__(server_id)
            job_count = self.__count_transcription_jobs_for_user__(user_uid)
            if job_count >= self.max_transcription_jobs_per_user:
                return (
                    False,
                    (
                        "User has reached the maximum number of transcription jobs "
                        f"({self.max_transcription_jobs_per_user})"
                    ),
                )

            collection = db.reference(
                "/TranscriptionJobs", app=self.firebase_app, url=self.database_url
            )
            reference = collection.push()
            transcription_id = reference.key
            if transcription_id is None:
                return False, "Firebase did not generate a transcription ID"

            record = TranscriptionJobsDTO(
                transcription_id=transcription_id,
                uuid=user_uid,
                server_id=server_id,
                last_heartbeat=self.__current_heartbeat__(),
            )
            reference.set(record.to_record())
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to create transcription job: {error}"

    def get_transcription_job(
        self, transcription_id: str
    ) -> TranscriptionJobsDTO | None:
        """Return a transcription job DTO, or ``None`` if it does not exist."""
        self.__validate_record_id__(transcription_id)
        record = self.__reference__("TranscriptionJobs", transcription_id).get()
        return self.__record_to_transcription_jobs_dto__(record)

    def update_transcription_job_heartbeat(
        self, transcription_id: str
    ) -> tuple[bool, TranscriptionJobsDTO | str]:
        """Update the heartbeat and return the updated transcription DTO."""
        try:
            self.__validate_record_id__(transcription_id)
            self.__update__(
                "TranscriptionJobs",
                transcription_id,
                {"last_heartbeat": self.__current_heartbeat__()},
            )
            record = self.get_transcription_job(transcription_id)
            if record is None:
                return False, f"Transcription job {transcription_id} was not found"
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to update transcription job heartbeat: {error}"

    def delete_transcription_job(
        self, transcription_id: str
    ) -> tuple[bool, TranscriptionJobsDTO | str]:
        """Delete a transcription job and return the deleted DTO."""
        try:
            self.__validate_record_id__(transcription_id)
            record = self.get_transcription_job(transcription_id)
            if record is None:
                return False, f"Transcription job {transcription_id} was not found"
            self.__reference__("TranscriptionJobs", transcription_id).delete()
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to delete transcription job: {error}"

    # -------------------------------
    # ServerAvailability table
    # -------------------------------

    def create_server_availability(
        self, record: ServerAvailabilityDTO
    ) -> tuple[bool, ServerAvailabilityDTO | str]:
        """Create a server availability record and return its stored DTO."""
        try:
            if not isinstance(record, ServerAvailabilityDTO):
                raise TypeError("record must be a ServerAvailabilityDTO")
            self.__validate_record_id__(record.server_id)
            record.last_heartbeat = self.__current_heartbeat__()
            reference = self.__reference__("ServerAvailability", record.server_id)
            if reference.get() is not None:
                return False, f"Server {record.server_id!r} already exists"
            reference.set(record.to_record())
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to create server availability record: {error}"

    def get_server_availability(
        self, server_id: str | None = None
    ) -> ServerAvailabilityDTO | None:
        """Return one server DTO, or the first record when no ID is supplied."""
        if server_id is not None:
            self.__validate_record_id__(server_id)
            record = self.__reference__("ServerAvailability", server_id).get()
            return self.__record_to_server_availability_dto__(record)

        records = (
            db.reference(
                "/ServerAvailability", app=self.firebase_app, url=self.database_url
            )
            .order_by_key()
            .limit_to_first(1)
            .get()
        )
        if not isinstance(records, Mapping) or not records:
            return None
        return self.__record_to_server_availability_dto__(next(iter(records.values())))

    def update_server_availability_heartbeat(
        self, server_id: str, cpu_usage: float, ram_usage: float
    ) -> tuple[bool, ServerAvailabilityDTO | str]:
        """Update server resource usage and heartbeat, returning its DTO."""
        try:
            self.__validate_record_id__(server_id)
            if isinstance(cpu_usage, bool) or not isinstance(cpu_usage, (int, float)):
                raise TypeError("cpu_usage must be a number")
            if isinstance(ram_usage, bool) or not isinstance(ram_usage, (int, float)):
                raise TypeError("ram_usage must be a number")
            self.__update__(
                "ServerAvailability",
                server_id,
                {
                    "cpu_usage": float(cpu_usage),
                    "ram_usage": float(ram_usage),
                    "last_heartbeat": self.__current_heartbeat__(),
                },
            )
            record = self.get_server_availability(server_id)
            if record is None:
                return False, f"Server {server_id!r} was not found"
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to update server availability heartbeat: {error}"

    def delete_server_availability(
        self, server_id: str
    ) -> tuple[bool, ServerAvailabilityDTO | str]:
        """Delete a server availability record and return the deleted DTO."""
        try:
            self.__validate_record_id__(server_id)
            record = self.get_server_availability(server_id)
            if record is None:
                return False, f"Server {server_id!r} was not found"
            self.__reference__("ServerAvailability", server_id).delete()
            return True, record
        except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
            return False, f"Failed to delete server availability record: {error}"

    def delete_expired_servers(self) -> tuple[bool, str]:
        """Delete server records whose UTC heartbeat is more than five minutes old."""

        expired_before = datetime.now(UTC) - timedelta(minutes=5)
        cutoff = int(expired_before.strftime("%Y%m%d%H%M"))
        deleted_count = 0

        while True:
            try:
                expired_items = (
                    db.reference(
                        "/ServerAvailability",
                        app=self.firebase_app,
                        url=self.database_url,
                    )
                    .order_by_child("last_heartbeat")
                    .end_at(cutoff)
                    .limit_to_first(20)
                    .get()
                )

                if not isinstance(expired_items, Mapping) or not expired_items:
                   break
               
                expired_items_colection = iter(expired_items.items())
                
                try:
                    while True:
                        server_id, record = next(expired_items_colection)
                        self.__reference__("ServerAvailability", server_id).delete()
                        deleted_count += 1    
                except StopIteration:
                    pass
                    
            except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError):
                pass
            
        return True, f"Deleted {deleted_count} expired server record(s)"

    def delete_expired_transcription_jobs(self) -> tuple[bool, str]:
        """Delete transcription jobs whose UTC heartbeat is over five minutes old."""

        expired_before = datetime.now(UTC) - timedelta(minutes=5)
        cutoff = int(expired_before.strftime("%Y%m%d%H%M"))
        deleted_count = 0

        while True:
            try:
                expired_items = (
                    db.reference(
                        "/TranscriptionJobs",
                        app=self.firebase_app,
                        url=self.database_url,
                    )
                    .order_by_child("last_heartbeat")
                    .end_at(cutoff)
                    .limit_to_first(20)
                    .get()
                )

                if not isinstance(expired_items, Mapping) or not expired_items:
                    break

                for transcription_id in expired_items:
                    self.__reference__(
                        "TranscriptionJobs", transcription_id
                    ).delete()
                    deleted_count += 1
            except (ValueError, TypeError, KeyError, RuntimeError, FirebaseError) as error:
                return (
                    False,
                    (f"Failed to delete expired transcription jobs after deleting "
                    f"{deleted_count}: {error}"),
                )

        return True, f"Deleted {deleted_count} expired transcription job(s)"

    # -------------------------------
    # Private producer methods
    # -------------------------------

    def __reference__(self, collection: str, record_id: str):
        return db.reference(
            f"/{collection}/{record_id}",
            app=self.firebase_app,
            url=self.database_url,
        )

    def __update__(
        self,
        collection: str,
        record_id: str,
        changes: Mapping[str, str | int | float | bool],
    ) -> object:
        if not changes:
            raise ValueError("At least one field must be provided for an update")
        reference = self.__reference__(collection, record_id)
        if reference.get() is None:
            raise KeyError(f"{collection} record {record_id!r} does not exist")
        reference.update(dict(changes))
        return reference.get()

    def __count_transcription_jobs_for_user__(self, user_uid: str) -> int:
        jobs = db.reference(
            "/TranscriptionJobs", app=self.firebase_app, url=self.database_url
        ).get()
        if not isinstance(jobs, Mapping):
            return 0
        return sum(
            1
            for job in jobs.values()
            if isinstance(job, Mapping) and job.get("uuid") == user_uid
        )

    def __current_heartbeat__(self) -> int:
        return int(datetime.now(UTC).strftime("%Y%m%d%H%M"))

    def __record_to_transcription_jobs_dto__(
        self, record: object
    ) -> TranscriptionJobsDTO | None:
        if not isinstance(record, Mapping):
            return None
        transcription_id = record.get("transcription_id")
        user_uid = record.get("uuid")
        server_id = record.get("server_id")
        heartbeat = record.get("last_heartbeat")
        if not all(
            isinstance(value, str) for value in (transcription_id, user_uid, server_id)
        ):
            return None
        if heartbeat is not None and (
            isinstance(heartbeat, bool) or not isinstance(heartbeat, int)
        ):
            return None
        return TranscriptionJobsDTO(
            transcription_id=transcription_id,
            uuid=user_uid,
            server_id=server_id,
            last_heartbeat=heartbeat,
        )

    def __record_to_server_availability_dto__(
        self, record: object
    ) -> ServerAvailabilityDTO | None:
        if not isinstance(record, Mapping):
            return None
        server_id = record.get("server_id")
        server_address = record.get("server_address")
        load_balancer = record.get("load_balancer")
        tls = record.get("tls")
        cpu_usage = record.get("cpu_usage")
        ram_usage = record.get("ram_usage")
        heartbeat = record.get("last_heartbeat")
        if not isinstance(server_id, str) or not isinstance(server_address, str):
            return None
        if not isinstance(load_balancer, bool) or not isinstance(tls, bool):
            return None
        if isinstance(cpu_usage, bool) or not isinstance(cpu_usage, (int, float)):
            return None
        if isinstance(ram_usage, bool) or not isinstance(ram_usage, (int, float)):
            return None
        if heartbeat is not None and (
            isinstance(heartbeat, bool) or not isinstance(heartbeat, int)
        ):
            return None
        return ServerAvailabilityDTO(
            server_id=server_id,
            server_address=server_address,
            load_balancer=load_balancer,
            tls=tls,
            cpu_usage=float(cpu_usage),
            ram_usage=float(ram_usage),
            last_heartbeat=heartbeat,
        )

    def __validate_record_id__(self, record_id: str) -> None:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Record ID must be a non-empty string")
        if any(character in record_id for character in ".#$[]/"):
            raise ValueError(
                "Record ID contains a character forbidden in Firebase keys"
            )
