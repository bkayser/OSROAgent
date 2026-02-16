"""
In-memory rate limiter for the chat endpoint. Per-IP sliding windows: 50/hour, 100/24h.

When running with multiple uvicorn workers, each process has its own _timestamps dict,
so rate limits are effectively multiplied by the number of workers. For the circuit
breaker to be effective across workers, _timestamps must eventually be replaced with
a shared store (e.g. Redis) so all workers see the same per-IP counts.
"""

import threading
import time
from collections import defaultdict
from typing import List

# Limits: 50 per rolling 1 hour, 100 per rolling 24 hours (no per-minute limit)
LIMIT_PER_HOUR = 50
LIMIT_PER_24H = 100
WINDOW_1H_SEC = 3600
WINDOW_24H_SEC = 86400

# Per-IP list of request timestamps (epoch seconds). Anonymous/missing IPs share key "".
# TODO: Replace with Redis (or similar) to share counts across workers so the circuit
# breaker is effective when using multiple uvicorn workers.
_timestamps: dict[str, List[float]] = defaultdict(list)
_lock = threading.Lock()


def _prune(ts_list: List[float], cutoff: float) -> None:
    """Remove timestamps older than cutoff (in place)."""
    while ts_list and ts_list[0] < cutoff:
        ts_list.pop(0)


def check_and_record(client_ip: str) -> bool:
    """
    Check if the client is over the rate limit. If not, record this request and return True.
    If over limit, return False without recording.

    Uses sliding windows: 50 requests per rolling 1 hour, 100 per rolling 24 hours.
    Missing/empty IP is treated as a single key so unidentified clients share one bucket.
    """
    key = (client_ip or "").strip() or ""
    now = time.time()
    cutoff_24h = now - WINDOW_24H_SEC
    cutoff_1h = now - WINDOW_1H_SEC

    with _lock:
        ts_list = _timestamps[key]
        _prune(ts_list, cutoff_24h)

        count_1h = sum(1 for t in ts_list if t >= cutoff_1h)
        count_24h = len(ts_list)

        if count_1h >= LIMIT_PER_HOUR or count_24h >= LIMIT_PER_24H:
            return False

        ts_list.append(now)
        return True
