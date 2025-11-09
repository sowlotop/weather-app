from collections import deque
from time import time
from typing import Deque, Dict

class RateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self.store: Dict[str, Deque[float]] = {}

    def hit(self, key: str) -> bool:
        now = time()
        window_start = now - 60
        dq = self.store.setdefault(key, deque())
        while dq and dq[0] < window_start:
            dq.popleft()
        if len(dq) >= self.limit:
            return False
        dq.append(now)
        return True
