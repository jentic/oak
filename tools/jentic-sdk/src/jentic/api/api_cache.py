import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

CACHE_TTL_SECONDS = 86400  # 24 Hours


# Simple in-memory async cache for successful results, with TTL
class APICache:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: Dict[
            str, Tuple[Tuple[dict[str, Any], dict[str, dict[str, Any]]], datetime]
        ] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._logger = logging.getLogger(__name__)

    def _key(self, workflow_id: str) -> str:
        return workflow_id

    def _now(self) -> datetime:
        # Use UTC for consistency
        return datetime.now(timezone.utc)

    async def get_or_set(
        self,
        workflow_id: str,
        fetcher: Callable[
            [], Awaitable[Optional[Tuple[dict[str, Any], dict[str, dict[str, Any]]]]]
        ],
    ) -> Optional[Tuple[dict[str, Any], dict[str, dict[str, Any]]]]:
        key = self._key(workflow_id)
        now = self._now()
        if key in self._cache:
            value, ts = self._cache[key]
            if now - ts < self._ttl:
                self._logger.debug(f"Cache hit for key={key} (age={(now - ts).total_seconds()}s)")
                return value
            else:
                self._logger.debug(
                    f"Cache expired for key={key} (age={(now - ts).total_seconds()}s), evicting entry"
                )
                del self._cache[key]
        else:
            self._logger.debug(f"Cache miss for key={key}")
        # Prevent race conditions for the same key
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key in self._cache:
                value, ts = self._cache[key]
                if now - ts < self._ttl:
                    self._logger.debug(
                        f"Cache hit for key={key} (age={(now - ts).total_seconds()}s) [post-lock]"
                    )
                    return value
                else:
                    self._logger.debug(
                        f"Cache expired for key={key} (age={(now - ts).total_seconds()}s) [post-lock], evicting entry"
                    )
                    del self._cache[key]
            self._logger.debug(f"Fetching value for key={key}")
            result = await fetcher()
            if result is not None:
                self._logger.debug(f"Caching value for key={key}")
                self._cache[key] = (result, now)
            else:
                self._logger.debug(f"Fetcher returned None for key={key}, not caching")
            return result


api_cache = APICache()
