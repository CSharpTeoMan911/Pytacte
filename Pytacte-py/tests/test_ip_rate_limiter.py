import pytest

from utils import IpRateLimiter


def set_clock(monkeypatch, initial_time=0.0):
    current_time = [initial_time]
    monkeypatch.setattr(IpRateLimiter, "monotonic", lambda: current_time[0])
    return current_time


def test_allows_requests_up_to_limit_then_rejects(monkeypatch):
    set_clock(monkeypatch)
    limiter = IpRateLimiter.RateLimiter(requests_per_minute=2)

    assert limiter.is_allowed("192.0.2.1") is True
    assert limiter.is_allowed("192.0.2.1") is True
    assert limiter.is_allowed("192.0.2.1") is False


def test_limits_each_ip_independently(monkeypatch):
    set_clock(monkeypatch)
    limiter = IpRateLimiter.RateLimiter(requests_per_minute=1)

    assert limiter.is_allowed("192.0.2.1") is True
    assert limiter.is_allowed("192.0.2.1") is False
    assert limiter.is_allowed("192.0.2.2") is True


def test_allows_request_after_previous_request_leaves_60_second_window(monkeypatch):
    current_time = set_clock(monkeypatch)
    limiter = IpRateLimiter.RateLimiter(requests_per_minute=1)

    assert limiter.is_allowed("192.0.2.1") is True
    current_time[0] = 60.1

    assert limiter.is_allowed("192.0.2.1") is True


@pytest.mark.parametrize("ip", ["", None])
def test_rejects_missing_ip(ip, monkeypatch):
    set_clock(monkeypatch)
    limiter = IpRateLimiter.RateLimiter()

    with pytest.raises(ValueError, match="ip"):
        limiter.is_allowed(ip)
