"""Cross-platform system metrics used by the load balancer."""

import psutil
from firebase_admin import App

from firebase.firebase_database import FirebaseDatabase, ServerAvailabilityDTO


class LoadBalancer:
    def __init__(
        self, database_url: str, max_transcription_jobs_per_user: int, firebase_app: App
    ):
        # Prime psutil's non-blocking CPU sampler. Its first reading is otherwise
        # always 0 because it has no previous sample to compare against.
        self.database_connection = FirebaseDatabase(
            database_url=database_url,
            max_transcription_jobs_per_user=max_transcription_jobs_per_user,
            firebase_app=firebase_app,
        )
        psutil.cpu_percent(interval=None)

    def get_cpu_metrics(self) -> float:
        """Return current system-wide CPU and virtual memory usage.

        CPU and RAM percentages are in the range 0-100. RAM byte counts use
        the operating system's available system memory information.
        """
        return psutil.cpu_percent(interval=1)

    def update_cpu_and_ram_metrics(
        self, server_id: str, data: ServerAvailabilityDTO
    ) -> tuple[bool, str]:
        """Refresh the cached metrics and return the resulting snapshot."""
        if not isinstance(server_id, str):
            raise TypeError("server_id must be a string")
        if not server_id:
            raise ValueError("server_id must not be empty")
        if not isinstance(data, ServerAvailabilityDTO):
            raise TypeError("data must be a ServerAvailabilityDTO")
        if data.server_id != server_id:
            raise ValueError("data.server_id must match server_id")

        cpu_usage = self.get_cpu_metrics()
       
        data.cpu_usage = cpu_usage
        
        server_availability: ServerAvailabilityDTO | None = (
            self.database_connection.get_server_availability(server_id=server_id)
        )
        
        if server_availability is not None:
            is_successful, payload = self.database_connection.update_server_availability_heartbeat(data=data)

            if not is_successful:
                return [is_successful, payload]
        else:
            is_successful, payload = self.database_connection.create_server_availability(record=data)
            
            if not is_successful:
                return [is_successful, payload]
        
        return [True, 'Metrics updated successfully']
    
    
    def delete_expired_items(self) -> tuple[tuple[bool, bool, bool], tuple[str, str, str]]:
        is_sucessful, message = self.database_connection.delete_expired_transcription_jobs()
        _is_sucessful, _message = self.database_connection.delete_expired_servers()
        __is_sucessful, __message = self.database_connection.delete_orphan_client_servers()
            
        return [[is_sucessful, _is_sucessful, __is_sucessful], [message, _message, __message]]
    
    def sort_servers_by_cpu(self):
        self.database_connection.sort_severs_by_least_cpu_usage()
