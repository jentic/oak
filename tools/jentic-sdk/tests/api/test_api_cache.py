import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from jentic.api.api_cache import CACHE_TTL_SECONDS, APICache


@pytest.mark.asyncio
async def test_cache_returns_value():
    cache = APICache(ttl_seconds=10)
    called = 0

    async def fetcher():
        nonlocal called
        called += 1
        return ({"foo": 1}, {"bar": {"baz": 2}})

    # First call: fetcher runs
    result1 = await cache.get_or_set("id1", fetcher)
    # Second call: should hit cache
    result2 = await cache.get_or_set("id1", fetcher)
    assert result1 == result2
    assert called == 1


@pytest.mark.asyncio
async def test_cache_expires(monkeypatch):
    cache = APICache(ttl_seconds=1)
    called = 0

    async def fetcher():
        nonlocal called
        called += 1
        return ({"foo": 2}, {"bar": {"baz": 3}})

    # First call: fetcher runs
    fixed_now = datetime.now(timezone.utc)
    monkeypatch.setattr(cache, "_now", lambda: fixed_now)
    result1 = await cache.get_or_set("id2", fetcher)
    # Simulate time passing by advancing fixed_now
    later = fixed_now + timedelta(seconds=2)
    monkeypatch.setattr(cache, "_now", lambda: later)
    # Second call: should refetch due to TTL expiry
    result2 = await cache.get_or_set("id2", fetcher)
    assert result1 == result2
    assert called == 2


@pytest.mark.asyncio
async def test_cache_none_not_cached():
    cache = APICache(ttl_seconds=10)
    called = 0

    async def fetcher():
        nonlocal called
        called += 1
        return None

    # None result should not be cached
    result1 = await cache.get_or_set("id3", fetcher)
    result2 = await cache.get_or_set("id3", fetcher)
    assert result1 is None and result2 is None
    assert called == 2
