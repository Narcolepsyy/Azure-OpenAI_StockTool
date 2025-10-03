import json
from app.routers.chat import _smart_truncate_answer, _sanitize_perplexity_result


def test_smart_truncate_removes_orphan_zero():
    # Create an answer that would end with a stray 0 after truncation
    base = "This is a long synthesized answer with multiple citations [1] and [2] providing details about the topic. "
    filler = "More context here. " * 100
    answer = base + filler + "0"  # Append orphan 0
    truncated = _smart_truncate_answer(answer, max_chars=180)
    assert not truncated.rstrip().endswith("0"), f"Unexpected orphan zero at end: {truncated[-10:]}"
    assert truncated.endswith("..."), "Expected ellipsis after truncation"


def test_sanitize_perplexity_result_cleans_answer():
    answer = "Key facts [1 Some partial citation leftover 0"
    result = {"answer": answer, "citations": {1: {"url": "https://example.com"}}}
    cleaned = _sanitize_perplexity_result(result)
    assert "[1 Some" not in cleaned["answer"], "Partial citation not removed"
    assert not cleaned["answer"].rstrip().endswith("0"), "Trailing zero not removed"

if __name__ == "__main__":
    test_smart_truncate_removes_orphan_zero()
    test_sanitize_perplexity_result_cleans_answer()
    print("All truncation sanitization tests passed")
