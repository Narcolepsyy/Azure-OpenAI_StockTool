import asyncio

import pytest

from app.services.perplexity_web_search import (
    PerplexityWebSearchService,
    SearchResult,
    _build_search_cache_key,
    _deserialize_search_results,
    _serialize_search_results,
    _content_cache,
    _search_cache,
)


def test_search_cache_serialization_roundtrip():
    """Search result cache serialization should round-trip cleanly."""
    _search_cache.clear()
    original_results = [
        SearchResult(
            title="Result One",
            url="https://example.com/one",
            snippet="Snippet one",
            relevance_score=0.8,
            timestamp="2025-09-25T12:00:00",
            source="brave_search",
            citation_id=1,
        ),
        SearchResult(
            title="Result Two",
            url="https://example.com/two",
            snippet="Snippet two",
            relevance_score=0.6,
            timestamp="2025-09-25T12:01:00",
            source="ddgs_search",
            citation_id=2,
        ),
    ]

    cache_key = _build_search_cache_key("sample query", 2, True, None)
    serialized = _serialize_search_results(original_results)
    _search_cache.put(cache_key, serialized)

    cached_payload = _search_cache.get(cache_key)
    restored_results = _deserialize_search_results(cached_payload)

    assert len(restored_results) == len(original_results)
    assert restored_results[0].title == original_results[0].title
    assert restored_results[1].url == original_results[1].url
    assert restored_results[0] is not original_results[0]


@pytest.mark.asyncio
async def test_content_cache_short_circuits_enhancement():
    """Content cache should prevent redundant network fetches."""
    _content_cache.clear()
    service = PerplexityWebSearchService()

    url = "https://example.com/article"
    _content_cache.put(url, {"content": "Cached body", "word_count": 2})

    result = SearchResult(
        title="Cached Article",
        url=url,
        snippet="Cached snippet",
        source="brave_search",
        citation_id=1,
    )

    enhanced = await service._enhance_single_result(result)
    await service.close()

    assert enhanced.content == "Cached body"
    assert enhanced.word_count == 2