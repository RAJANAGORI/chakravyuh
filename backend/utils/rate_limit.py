import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, Dict

from fastapi import HTTPException, status


@dataclass
class _Bucket:
    entries: Deque[float]
    lock: Lock


_BUCKETS: Dict[str, _Bucket] = {}
_ROOT_LOCK = Lock()


def _get_bucket(key: str) -> _Bucket:
    with _ROOT_LOCK:
        bucket = _BUCKETS.get(key)
        if bucket is None:
            bucket = _Bucket(entries=deque(), lock=Lock())
            _BUCKETS[key] = bucket
        return bucket


def enforce_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    now = time.time()
    start = now - window_seconds
    bucket = _get_bucket(key)
    with bucket.lock:
        while bucket.entries and bucket.entries[0] < start:
            bucket.entries.popleft()
        if len(bucket.entries) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({max_requests}/{window_seconds}s).",
            )
        bucket.entries.append(now)
