"""Cross-platform system metrics used by the load balancer."""

import psutil


class LoadBalancer:
    def __init__(self, database_url):
        # Prime psutil's non-blocking CPU sampler. Its first reading is otherwise
        # always 0 because it has no previous sample to compare against.
        self.database_connection = database_url
        psutil.cpu_percent(interval=None)
    
    def get_cpu_and_ram_metrics(self):
        """Return current system-wide CPU and virtual memory usage.

        CPU and RAM percentages are in the range 0-100. RAM byte counts use
        the operating system's available system memory information.
        """
        memory = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": memory.percent,
            "ram_used_bytes": memory.used,
            "ram_total_bytes": memory.total,
        }
    
    def update_cpu_and_ram_metrics(self):
        """Refresh the cached metrics and return the resulting snapshot."""
        metrics = self.get_cpu_and_ram_metrics()
        
        return metrics
