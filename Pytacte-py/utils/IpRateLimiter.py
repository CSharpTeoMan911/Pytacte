from time import monotonic


class RateLimiter:
    """In-memory rate limiter, tracked independently for each IP."""
    
    
    def __init__(self, requests_per_minute:int=10):
        self.requests_per_minute = requests_per_minute
        self.client_rates: dict[str, list[float]] = {}

    def is_allowed(self, ip: str) -> bool:
        """Record a request for ``ip`` and return whether it is under the rate limit"""
        if not ip:
            raise ValueError('ip must be a non-empty string')
    
        # Get current monotonic time
        now = monotonic()
            
        # Get the times for all the requests made for the current client ip
        _client_rates:list[float] | None = self.client_rates.get(ip)
        
        # If client requests are found 
        if _client_rates != None:
            
            # Extract only the requests made in the last 60 seconds (1 minute)
            relevant_rates = [time for time in _client_rates if now - time <= 60]
            
            # If the number of requests made in the last minute for 
            # the current IP exceeds the limit, return 'False'
            if len(relevant_rates) >= self.requests_per_minute:
                return False
            else:
                # If the number of requests is under, append the current monotonic value to the list
                relevant_rates.append(now)
                self.client_rates[ip] = relevant_rates
                return True
        else:
            self.client_rates[ip] = [now]
            return True
    
