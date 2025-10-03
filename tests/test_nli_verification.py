import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.perplexity_web_search import (
    PerplexityWebSearchService,
    SearchResult,
)


class FakeChatCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, *args, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content)
                )
            ]
        )


class FakeChat:
    def __init__(self, content: str):
        self.completions = FakeChatCompletions(content)


class FakeOpenAIClient:
    def __init__(self, content: str):
        self.chat = FakeChat(content)


@pytest.mark.asyncio
async def test_verify_citations_supported_updates_result():
    service = PerplexityWebSearchService()
    service._get_nli_client = AsyncMock(
        return_value=(FakeOpenAIClient('{"verdict":"SUPPORTED","confidence":0.88,"reason":"Evidence aligns","quote":"Revenue increased"}'), "fake-model", "openai")
    )

    result = SearchResult(
        title="Example Source",
        url="https://example.com/article",
        snippet="",
        content="The company reported that revenue increased by 20% year over year.",
        citation_id=1,
    )

    answer = "Revenue increased by twenty percent compared to last year [1]."

    verified_answer, notes, details = await service._verify_citations_nli(answer, [result])

    assert "Verification notes" not in verified_answer
    assert notes == []
    assert details["evaluations"][0]["status"] == "supported"
    assert result.nli_status == "supported"
    assert result.nli_confidence == pytest.approx(0.88, rel=1e-3)
    assert result.nli_last_claim.startswith("Revenue increased")

    await service._close_session()


@pytest.mark.asyncio
async def test_verify_citations_contradicted_adds_note():
    service = PerplexityWebSearchService()
    service._get_nli_client = AsyncMock(
        return_value=(FakeOpenAIClient('{"verdict":"CONTRADICTED","confidence":0.25,"reason":"Evidence reports a decline","quote":"Revenue decreased"}'), "fake-model", "openai")
    )

    result = SearchResult(
        title="Quarterly Report",
        url="https://example.com/report",
        snippet="",
        content="According to the quarterly filing, revenue decreased 5% compared to the prior year.",
        citation_id=2,
    )

    answer = "Management stated revenue surged significantly year over year [2]."

    verified_answer, notes, details = await service._verify_citations_nli(answer, [result])

    assert "**Verification notes:**" in verified_answer
    assert notes, "Expected verification notes for contradictions"
    assert any("[2]" in note for note in notes)
    assert details["evaluations"][0]["status"] == "contradicted"
    assert result.nli_status == "contradicted"
    assert result.nli_confidence == pytest.approx(0.25, rel=1e-3)
    assert "decline" in result.nli_reason.lower()

    await service._close_session()
