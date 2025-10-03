"""Test citation URL normalization and structured citation output."""
import re
import pytest

pytest.importorskip("aiohttp")

from app.services.perplexity_web_search import PerplexityWebSearchService, SearchResult


def test_citation_url_normalization():
    service = PerplexityWebSearchService()
    # Mock results with tracking params and mixed schemes
    raw_results = [
        SearchResult(
            title="Sample Brave Result",
            url="https://Example.COM:443/path///to/page/?utm_source=newsletter&gclid=ABC123&id=42",
            snippet="Snippet one",
            relevance_score=0.9,
            source='brave_search',
            citation_id=1
        ),
        SearchResult(
            title="DDGS Result",
            url="http://example.com:80/path/to/page/?ref=tracker&utm_medium=email",
            snippet="Snippet two",
            relevance_score=0.7,
            source='ddgs_search',
            citation_id=2
        )
    ]

    citations = service._build_citations(raw_results)
    assert 1 in citations and 2 in citations, "Citation IDs missing"
    c1 = citations[1]
    c2 = citations[2]
    # Ensure structured form
    assert isinstance(c1, dict), "Citation is not structured dict"
    # URL normalization expectations
    assert c1['url'].startswith('https://example.com'), c1['url']
    assert 'utm_' not in c1['url'] and 'gclid' not in c1['url'], c1['url']
    # Allow either upgraded https or original http depending on availability
    assert c2['url'].startswith(('https://example.com', 'http://example.com')), c2['url']
    assert 'ref=' not in c2['url'], c2['url']
    # Domain extraction
    assert c1['domain'] == 'example.com'
    assert c2['domain'] == 'example.com'
    # Display string preservation
    assert 'High-Quality Source' in c1['display']


def test_ensure_citations_in_answer_backfills_markers():
    service = PerplexityWebSearchService()
    results = [
        SearchResult(
            title="Source One",
            url="https://example.com/one",
            snippet="Details about revenue",
            source='brave_search',
            citation_id=1
        ),
        SearchResult(
            title="Source Two",
            url="https://example.com/two",
            snippet="Quarterly analysis",
            source='ddgs_search',
            citation_id=2
        ),
    ]

    answer = "Revenue grew by 10% quarter-over-quarter."
    enforced = service._ensure_citations_in_answer(answer, results)

    refs = set(re.findall(r'\[(\d+)\]', enforced))
    assert refs, "Citations should be injected when missing"
    assert refs.issubset({'1', '2'}), f"Unexpected citation IDs injected: {refs}"
    assert enforced.endswith((' [1]', ' [2]'))


def test_ensure_citations_in_answer_preserves_existing():
    service = PerplexityWebSearchService()
    results = [
        SearchResult(
            title="Source One",
            url="https://example.com/one",
            snippet="Details about revenue",
            source='brave_search',
            citation_id=1
        ),
        SearchResult(
            title="Source Two",
            url="https://example.com/two",
            snippet="Quarterly analysis",
            source='ddgs_search',
            citation_id=2
        ),
    ]

    answer = "Revenue grew by 10% quarter-over-quarter. [2]"
    enforced = service._ensure_citations_in_answer(answer, results)

    assert enforced == answer, "Existing valid citations should be preserved"


def test_merge_adjacent_citations_collapses_sequences():
    service = PerplexityWebSearchService()
    text = "Growth accelerated[1][2][4] due to macro trends[3]."
    merged = service._merge_adjacent_citations(text)
    assert merged == "Growth accelerated[1,2,4] due to macro trends[3]."


if __name__ == '__main__':
    test_citation_url_normalization()
    print('Citation URL normalization test passed.')
