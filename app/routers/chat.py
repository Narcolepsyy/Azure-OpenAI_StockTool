"""Chat API routes for conversational AI functionality."""
import ast
import json
import logging
import re
import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple, Set
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openai import AzureOpenAI

from app.models.database import get_db, User, Log
from app.models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessage
from app.auth.dependencies import get_current_user
from app.core.config import DEFAULT_MODEL
from app.utils.conversation import (
    conv_clear, conv_get, estimate_tokens, MAX_TOKENS_PER_TURN,
    prepare_conversation_messages_with_memory, store_conversation_messages_with_memory
)
from app.utils.tools import TOOL_REGISTRY, build_tools_for_request
from app.utils.connection_pool import connection_pool
from app.utils.request_cache import (
    get_cached_response, cache_response, is_request_in_flight,
    mark_request_in_flight, clear_request_in_flight
)
from app.utils.query_optimizer import (
    is_simple_query, get_fast_model_recommendation, should_skip_rag_and_web_search
)


router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Optimized Japanese directive - shorter and more efficient
_JAPANESE_DIRECTIVE = "\n\n日本語で回答してください。"

# Thread pool for async tool execution
_tool_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool-exec")

# Pre-serialized common response structures to reduce JSON overhead
_PRECOMPILED_RESPONSES = {
    'start': lambda conv_id, model: f'"type":"start","conversation_id":"{conv_id}","model":"{model}"',
    'tool_running': lambda name: f'"type":"tool_call","name":"{name}","status":"running"',
    'tool_completed': lambda name: f'"type":"tool_call","name":"{name}","status":"completed"',
    'tool_error': lambda name, error: f'"type":"tool_call","name":"{name}","status":"error","error":"{json.dumps(error)[1:-1]}"',
    'content': lambda delta: f'"type":"content","delta":{json.dumps(delta)}'
}

# --- Smart truncation helpers for synthesized answers (Perplexity-style) ---
_TRUNC_MAX_CHARS = 1500  # Target max visible chars for synthesized answers in tool payloads

_WEB_SEARCH_TOOL_NAMES = {
    "perplexity_search",
    "web_search",
    "web_search_news",
    "augmented_rag_search",
    "financial_context_search",
    "augmented_rag_web",
}

_WEB_SEARCH_METADATA_KEYS = ("confidence", "method", "timings", "search_time", "latency_ms")

_PARTIAL_CITATION_RE = re.compile(r"\[[0-9]{0,3}$")  # Trailing partial like '[1' or '['
_ORPHAN_NUM_RE = re.compile(r"(?<!\])(?:(?<=\s)|^)[0-9]{1,2}$")  # Trailing small number not closed by ]
_BROKEN_CITATION_FRAGMENT_RE = re.compile(r"\[[0-9]{1,3}\s+[^\]]*$")  # e.g. '[1 Some partial'

# Pattern to detect raw JSON tool call outputs from GPT-5 (filter these out)
_RAW_TOOL_CALL_JSON_RE = re.compile(
    r'\{\s*"query"\s*:\s*"[^"]*",\s*"max_results"\s*:\s*\d+,\s*"synthesize_answer"\s*:\s*true,\s*"include_recent"\s*:\s*true\s*\}',
    re.IGNORECASE | re.DOTALL
)

def _is_raw_tool_call_output(text: str) -> bool:
    """
    Detect if text contains raw JSON tool call output that should be hidden from user.
    GPT-5 sometimes outputs raw JSON instead of using proper function calling API.
    """
    if not text or len(text.strip()) < 10:
        return False
    
    # Check for JSON tool call patterns
    if _RAW_TOOL_CALL_JSON_RE.search(text):
        return True
    
    # Check for multiple JSON objects in succession (tool call spam)
    json_brace_count = text.count('{')
    if json_brace_count >= 3 and '"query"' in text and '"max_results"' in text:
        return True
    
    return False

def _smart_truncate_answer(answer: str, max_chars: int = _TRUNC_MAX_CHARS) -> str:
    """Truncate synthesized answer safely, avoiding broken citation/artifacts.
    Rules:
    - Cut at max_chars boundary (soft) and roll back to last whitespace if mid-word
    - Remove dangling partial citation patterns (e.g. '[1', '[12')
    - Remove orphan trailing numbers (e.g. solitary '0' left after slice)
    - Preserve existing full citations like '[12]'
    - Append ellipsis if truncated
    """
    if not answer or len(answer) <= max_chars:
        return answer

    cut = answer[:max_chars]

    # If we cut in the middle of a word and we have sufficient earlier whitespace, roll back
    if not cut.endswith((" ", "\n", "\t")):
        last_space = cut.rfind(" ")
        if last_space > max_chars * 0.6:  # Only roll back if it preserves most content
            cut = cut[:last_space]

    # Remove trailing partial citation like '[1' or '['
    cut = _PARTIAL_CITATION_RE.sub("", cut)

    # Remove broken citation fragments missing closing bracket
    cut = _BROKEN_CITATION_FRAGMENT_RE.sub("", cut)

    # Remove trailing orphan number (e.g., stray '0') that is not part of [n]
    if _ORPHAN_NUM_RE.search(cut.rstrip()):
        cut = _ORPHAN_NUM_RE.sub("", cut.rstrip())

    # Clean dangling punctuation / unmatched opening brackets
    cut = cut.rstrip(" ,;:\n\t-[")

    return cut + "..."

def _sanitize_perplexity_result(result: Any) -> Any:
    """Apply smart truncation & cleanup to perplexity_search tool result structure.
    Ensures no stray '0' or partial citation artifacts remain after truncation.
    """
    try:
        if not isinstance(result, dict):
            return result
        answer = result.get("answer")
        if isinstance(answer, str) and answer:
            truncated = _smart_truncate_answer(answer, _TRUNC_MAX_CHARS)
            # Remove any '[0]' citations (model sometimes enumerates from zero) – shift discouraged
            truncated = truncated.replace("[0]", "")
            # Remove lingering broken citation fragments inside (conservative: only if near end)
            tail = truncated[-120:]
            cleaned_tail = _BROKEN_CITATION_FRAGMENT_RE.sub("", tail)
            if tail != cleaned_tail:
                truncated = truncated[:-120] + cleaned_tail
            result = {**result, "answer": truncated}
        return result
    except Exception:
        return result


def _select_top_sources_for_context(result: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """Extract a compact list of sources for model context while preserving citation ids."""
    candidates: List[Dict[str, Any]] = []
    for key in ("sources", "raw_sources", "results"):
        value = result.get(key)
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))

    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for item in candidates:
        citation_id = item.get("citation_id") or item.get("citationId") or item.get("id")
        url = item.get("url") or item.get("link") or item.get("source")
        title = item.get("title") or item.get("name")
        dedupe_key = str(citation_id).strip() if citation_id is not None else (url or title)
        if not dedupe_key:
            continue
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        summary = {
            "citation_id": citation_id,
            "title": title,
            "url": url,
        }

        snippet = item.get("snippet") or item.get("description") or item.get("content") or item.get("text")
        if snippet:
            summary["snippet"] = snippet

        domain = item.get("domain")
        if not domain and isinstance(url, str):
            try:
                parsed = urlparse(url if re.match(r"^https?://", url, re.IGNORECASE) else f"https://{url}")
                domain = parsed.hostname or parsed.path.split("/")[0]
                if domain and domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                domain = None
        if domain:
            summary["domain"] = domain

        publish_date = (
            item.get("publish_date")
            or item.get("publishDate")
            or item.get("timestamp")
            or item.get("date")
        )
        if publish_date:
            summary["publish_date"] = publish_date

        score = item.get("score") or item.get("relevance_score")
        if score is not None:
            summary["score"] = score

        selected.append(summary)
        if len(selected) >= limit:
            break

    return selected


def _build_web_search_tool_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Create a compact payload for web search tools that preserves inline citations."""
    payload: Dict[str, Any] = {}

    answer = result.get("answer")
    if isinstance(answer, str) and answer:
        payload["answer"] = _smart_truncate_answer(answer, _TRUNC_MAX_CHARS)

    citations = result.get("citations")
    if isinstance(citations, dict) and citations:
        payload["citations"] = citations

    # Preserve citation styling if available
    for key in ("css", "styles", "style_tag"):
        value = result.get(key)
        if value:
            payload[key] = value
            break

    metadata = {}
    for key in _WEB_SEARCH_METADATA_KEYS:
        value = result.get(key)
        if value is not None:
            metadata[key] = value
    synthesized_query = result.get("synthesized_query") or result.get("query")
    if synthesized_query:
        metadata["query"] = synthesized_query
    if metadata:
        payload["metadata"] = metadata

    sources = _select_top_sources_for_context(result)
    if sources:
        payload["top_sources"] = sources

    return payload

def _normalize_content_piece(piece: Any) -> str:
    """Extract text from various content shapes safely."""
    try:
        if piece is None:
            return ""
        if isinstance(piece, str):
            return piece
        # Content piece could be dict-like {type: 'text', 'text': '...'}
        if isinstance(piece, dict):
            txt = piece.get("text") or piece.get("content") or ""
            return txt if isinstance(txt, str) else json.dumps(piece)[:2000]
        # Fallback stringify
        return str(piece)
    except Exception:
        return ""


def _safe_tool_result_json(payload: Any) -> str:
    """Serialize tool payloads without raising on non-JSON types."""
    try:
        return json.dumps(payload, default=str)
    except Exception:
        try:
            return json.dumps(str(payload))
        except Exception:
            return "\"\""

# --- Pseudo tool-call compatibility (e.g., OSS models emitting special markup) ---
_PSEUDO_TOOL_RE = re.compile(
    r"<\|start\|>assistant<\|channel\|>commentary\s+to=(?:functions\.)?(\w+)(?:<\|channel\|>commentary\s+json|(?:\s+<\|constrain\|>json)?)\s*<\|message\|>(\{.*?\})<\|call\|>",
    re.DOTALL | re.IGNORECASE,
)

_TOOL_NAME_MAPPING = {
    "perplexity_search": "perplexity_search",
    "functions.get_augmented_news": "get_augmented_news",
    "functions.get_company_profile": "get_company_profile",
    "functions.get_stock_quote": "get_stock_quote",
    "functions.get_historical_prices": "get_historical_prices",
    "functions.get_risk_assessment": "get_risk_assessment",
    "functions.rag_search": "rag_search",
    "functions.augmented_rag_search": "augmented_rag_search",
}

_SUGGESTED_TOOL_WHITELIST = {
    "perplexity_search",
    "augmented_rag_search",
    "rag_search",
}

_CODE_BLOCK_RE = re.compile(r"```(?:[\w+-]+)?\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_SUGGESTED_CALL_RE = re.compile(r"(perplexity_search\s*\(.*?\))", re.DOTALL | re.IGNORECASE)
_QUOTED_QUERY_RE = re.compile(r"[\"'“”『「](.*?)[\"'“”』」]")

MAX_SUGGESTED_TOOL_ROUNDS = 2


def _normalize_tool_name_and_args(name: str, args_dict: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    mapped_name = _TOOL_NAME_MAPPING.get(name, name)
    args = dict(args_dict or {})

    if "ticker" in args and "symbol" not in args:
        args["symbol"] = args.pop("ticker")

    if mapped_name in {"web_search", "perplexity_search"}:
        if "max_results" not in args:
            for alt_key in ("top_k", "top_n", "num_results", "limit"):
                if alt_key in args:
                    try:
                        args["max_results"] = int(args.pop(alt_key))
                    except (TypeError, ValueError):
                        args.pop(alt_key, None)
                    break

        if "recency_days" in args and "include_recent" not in args:
            recency_days = args.pop("recency_days")
            try:
                args["include_recent"] = int(recency_days) <= 7
            except (TypeError, ValueError):
                args["include_recent"] = True

        if "source" in args:
            source = args.pop("source")
            if source == "news":
                args["include_recent"] = True
                args["synthesize_answer"] = True
            elif source == "academic":
                args["include_recent"] = False
                args["synthesize_answer"] = True

    return mapped_name, args


def _safe_literal_eval_node(node: ast.AST) -> Optional[Any]:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    if isinstance(node, ast.Num):  # pragma: no cover - legacy AST nodes
        return node.n
    if isinstance(node, ast.NameConstant):  # pragma: no cover - legacy AST nodes
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _safe_literal_eval_node(node.operand)
        if operand is None:
            return None
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.List):
        items: List[Any] = []
        for elt in node.elts:
            value = _safe_literal_eval_node(elt)
            if value is None:
                return None
            items.append(value)
        return items
    if isinstance(node, ast.Tuple):
        items: List[Any] = []
        for elt in node.elts:
            value = _safe_literal_eval_node(elt)
            if value is None:
                return None
            items.append(value)
        return tuple(items)
    if isinstance(node, ast.Dict):
        result: Dict[Any, Any] = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = _safe_literal_eval_node(key_node)
            value = _safe_literal_eval_node(value_node)
            if key is None or value is None:
                return None
            result[key] = value
        return result
    return None


def _parse_suggested_tool_call(expr: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        return None

    call = getattr(tree, "body", None)
    if not isinstance(call, ast.Call):
        return None

    func = call.func
    if isinstance(func, ast.Attribute):
        func_name = func.attr
    elif isinstance(func, ast.Name):
        func_name = func.id
    else:
        return None

    func_name = func_name.strip()
    if func_name not in _SUGGESTED_TOOL_WHITELIST:
        return None

    args_dict: Dict[str, Any] = {}

    if call.args:
        first_value = _safe_literal_eval_node(call.args[0])
        if first_value is not None:
            if func_name in {"perplexity_search", "web_search", "augmented_rag_search", "rag_search"}:
                args_dict.setdefault("query", first_value)
            elif func_name.startswith("get_") and isinstance(first_value, str):
                args_dict.setdefault("symbol", first_value)

    for kw in call.keywords or []:
        if not kw.arg:
            continue
        value = _safe_literal_eval_node(kw.value)
        if value is None:
            continue
        args_dict[kw.arg] = value

    mapped_name, normalized_args = _normalize_tool_name_and_args(func_name, args_dict)
    return mapped_name, normalized_args


def _extract_suggested_tool_calls(text: str, max_calls: int = 2) -> List[Dict[str, Any]]:
    if not text:
        return []

    candidates: List[str] = []

    for block_match in _CODE_BLOCK_RE.finditer(text):
        block = block_match.group(1)
        if not block:
            continue
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        # Skip language specifiers (e.g., ```python)
        if len(lines) > 1 and re.match(r"^[A-Za-z][\w+-]*$", lines[0]) and "(" not in lines[0]:
            lines = lines[1:]
        for line in lines:
            candidates.append(line)

    for inline_match in _INLINE_CODE_RE.finditer(text):
        snippet = inline_match.group(1).strip()
        if snippet:
            candidates.append(snippet)

    for call_match in _SUGGESTED_CALL_RE.finditer(text):
        candidate = call_match.group(1).strip()
        if candidate:
            candidates.append(candidate)

    suggestions: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    counter = 0

    for candidate in candidates:
        if not any(name in candidate for name in _SUGGESTED_TOOL_WHITELIST):
            continue
        parsed = _parse_suggested_tool_call(candidate)
        if not parsed:
            continue
        mapped_name, normalized_args = parsed
        try:
            args_json = json.dumps(normalized_args)
        except Exception:
            continue
        key = (mapped_name, args_json)
        if key in seen:
            continue
        seen.add(key)
        counter += 1
        suggestions.append({
            "id": f"suggested-{counter}",
            "type": "function",
            "function": {"name": mapped_name, "arguments": args_json},
        })
        if len(suggestions) >= max_calls:
            break

    if len(suggestions) < max_calls:
        text_lower = text.lower()
        if "perplexity_search" in text_lower:
            quoted_queries: List[str] = []
            for match in _QUOTED_QUERY_RE.findall(text):
                query = match.strip()
                if not query:
                    continue
                query = " ".join(part.strip() for part in query.splitlines() if part.strip())
                if len(query) < 3:
                    continue
                quoted_queries.append(query)

            if not quoted_queries:
                bullet_re = re.compile(r"^[\-\u2022\u30FB\u2219]\s*(.+)$")
                for line in text.splitlines():
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    bullet_match = bullet_re.match(line_stripped)
                    if bullet_match:
                        candidate_query = bullet_match.group(1).strip()
                        candidate_query = candidate_query.strip("\"'“”『』「」")
                        if len(candidate_query) >= 3:
                            quoted_queries.append(candidate_query)

            for query in quoted_queries:
                try:
                    normalized_query = query.strip()
                    if not normalized_query:
                        continue
                    mapped_name, normalized_args = _normalize_tool_name_and_args(
                        "perplexity_search",
                        {
                            "query": normalized_query,
                            "synthesize_answer": True,
                            "include_recent": True,
                        },
                    )
                    args_json = json.dumps(normalized_args)
                    key = (mapped_name, args_json)
                    if key in seen:
                        continue
                    seen.add(key)
                    counter += 1
                    suggestions.append({
                        "id": f"suggested-{counter}",
                        "type": "function",
                        "function": {"name": mapped_name, "arguments": args_json},
                    })
                    if len(suggestions) >= max_calls:
                        break
                except Exception:
                    continue

    return suggestions

# Human-readable previews for common tool results (module-level for reuse)
def _human_preview_company_profile(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        name = result.get("longName") or ""
        sector = result.get("sector") or ""
        industry = result.get("industry") or ""
        country = result.get("country") or ""
        currency = result.get("currency") or ""
        website = result.get("website") or ""
        parts = []
        title = f"Company profile for {sym}: {name}".strip()
        parts.append(title)
        si = ", ".join([p for p in [sector, industry] if p])
        if si:
            parts.append(si)
        if country:
            parts.append(country)
        if currency:
            parts.append(f"Currency: {currency}")
        if website:
            parts.append(website)
        return "\n".join(parts)
    except Exception:
        try:
            s = json.dumps(result)
            return (s[:280] + ("..." if len(s) > 280 else ""))
        except Exception:
            return ""

def _human_preview_quote(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        price = result.get("price")
        currency = result.get("currency") or ""
        as_of = result.get("as_of") or ""
        if price is not None:
            return f"{sym} latest close: {price} {currency} (as of {as_of})"
        return ""
    except Exception:
        try:
            s = json.dumps(result)
            return (s[:280] + ("..." if len(s) > 280 else ""))
        except Exception:
            return ""

# Japanese versions of preview functions
def _human_preview_company_profile_jp(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        name = result.get("longName") or ""
        sector = result.get("sector") or ""
        industry = result.get("industry") or ""
        country = result.get("country") or ""
        currency = result.get("currency") or ""
        
        parts = []
        if sym and name:
            parts.append(f"**{sym} - {name}**")
        if sector or industry:
            sector_info = f"{sector}" + (f" / {industry}" if industry else "")
            parts.append(f"業種: {sector_info}")
        if country:
            parts.append(f"国: {country}")
        if currency:
            parts.append(f"通貨: {currency}")
        
        formatted = "\n".join(parts)
        
        # Add data source
        formatted += "\n\n**データ出典**: Yahoo Finance 企業情報"
        
        return formatted
    except Exception:
        return _human_preview_company_profile(result)

def _human_preview_quote_jp(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        price = result.get("price")
        currency = result.get("currency") or ""
        as_of = result.get("as_of") or ""
        
        if price is not None:
            if currency == "JPY":
                formatted = f"**{sym}**: {price:,.0f}円"
            else:
                formatted = f"**{sym}**: {price:,.2f} {currency}"
        else:
            formatted = f"**{sym}**: データなし"
        
        if as_of:
            formatted += f"\n取得時刻: {as_of}"
        
        return formatted
    except Exception:
        return _human_preview_quote(result)

def _human_preview_historical_jp(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        currency = result.get("currency") or ""
        count = result.get("count", 0)
        period = result.get("period", "")
        rows = result.get("rows", [])
        
        if not rows:
            return f"{sym} 過去データ：データなし"
        
        # Get latest row for trend info
        latest = rows[-1] if rows else {}
        if len(rows) > 1:
            prev = rows[-2]
            current_price = latest.get("close")
            prev_price = prev.get("close")
            
            if current_price and prev_price:
                change = current_price - prev_price
                change_pct = (change / prev_price) * 100
                trend = "上昇" if change > 0 else "下落" if change < 0 else "横ばい"
                currency_jp = {"JPY": "円", "USD": "ドル", "EUR": "ユーロ"}.get(currency, currency)
                
                return f"**{sym} 過去{period}データ：**\n最新終値 {current_price:,} {currency_jp} (前日比 {change:+.1f} {currency_jp}, {change_pct:+.2f}%, {trend})"
        
        return f"**{sym} 過去{period}データ** ({count}件のデータポイント)"
    except Exception:
        try:
            return f"{result.get('symbol', '')} historical data: {result.get('count', 0)} points"
        except Exception:
            return ""

def _build_news_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """Create a concise summary for augmented news results suitable for model consumption."""
    sym = (result.get("symbol") or "").upper()
    items = result.get("items") or []
    headlines: List[Dict[str, Any]] = []
    for it in items[:5]:
        try:
            t = (it.get("title") or "").strip()
            pub = (it.get("publisher") or "").strip() or None
            dt = (it.get("published_at") or "").strip() or None
            link = (it.get("link") or "").strip() or None
            content = (it.get("content") or "").strip()
            if len(t) > 160:
                t = t[:160] + "..."
            if content and len(content) > 280:
                content = content[:280] + "..."
            headlines.append({
                "title": t,
                "publisher": pub,
                "published_at": dt,
                "summary": content or None,
                "link": link,
            })
        except Exception:
            continue
    return {
        "symbol": sym,
        "count": len(items),
        "headlines": headlines,
        "note": "summarized for brevity from get_augmented_news"
    }

def _human_preview_from_summary(summary: Dict[str, Any]) -> str:
    """Create human preview from news summary."""
    sym = summary.get("symbol") or ""
    lines = [f"Top headlines for {sym}:"]
    for h in summary.get("headlines", [])[:3]:
        bits = [h.get("title") or "Untitled"]
        if h.get("publisher"):
            bits.append(f"({h['publisher']}")
            if h.get("published_at"):
                bits[-1] = bits[-1][:-1] + f", {h['published_at'][:10]})"
        elif h.get("published_at"):
            bits.append(f"({h['published_at'][:10]})")
        lines.append(" - " + " ".join(bits))
    return "\n".join(lines)

def _human_preview_historical(result: Dict[str, Any]) -> str:
    try:
        sym = (result.get("symbol") or "").upper()
        currency = result.get("currency") or ""
        count = result.get("count", 0)
        period = result.get("period", "")
        rows = result.get("rows", [])
        
        if not rows:
            return f"{sym} historical data: No data"
        
        # Get latest row for trend info
        latest = rows[-1] if rows else {}
        if len(rows) > 1:
            prev = rows[-2]
            current_price = latest.get("close")
            prev_price = prev.get("close")
            
            if current_price and prev_price:
                change = current_price - prev_price
                change_pct = (change / prev_price) * 100
                trend = "up" if change > 0 else "down" if change < 0 else "flat"
                
                return f"{sym} {period} data: Latest {current_price} {currency} ({change:+.1f} {currency}, {change_pct:+.2f}%, {trend})"
        
        return f"{sym} {period} data ({count} points)"
    except Exception:
        try:
            return f"{result.get('symbol', '')} historical data: {result.get('count', 0)} points"
        except Exception:
            return ""

def _human_preview_nikkei_news_jp(result: Dict[str, Any]) -> str:
    try:
        count = result.get("count", 0)
        summaries = result.get("summaries", [])
        error = result.get("error")
        
        if error:
            return f"日経平均ニュース：{error}"
        
        if not summaries:
            return "日経平均ニュース：該当するニュースがありませんでした"
        
        lines = ["**日経平均の直近ニュース：**"]
        for i, item in enumerate(summaries[:5], 1):
            sentiment = item.get("sentiment_jp", "ニュートラル")
            summary = item.get("summary", "")
            publisher = item.get("publisher", "")
            
            # Format: number. summary (sentiment) - publisher
            line = f"{i}. {summary}"
            if sentiment:
                line += f" ({sentiment})"
            if publisher:
                line += f" - {publisher}"
            lines.append(line)
        
        return "\n".join(lines)
    except Exception:
        try:
            return f"日経平均ニュース：{result.get('count', 0)}件"
        except Exception:
            return "日経平均ニュース取得完了"

def _extract_pseudo_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Parse pseudo tool calls embedded in assistant text into standard tool_call format."""
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls
    try:
        matches = list(_PSEUDO_TOOL_RE.finditer(text))
        counter = 0
        for m in matches:
            # Extract tool name from group 1 and JSON payload from group 2
            tool_name = m.group(1)
            raw_json = m.group(2)
            
            try:
                payload = json.loads(raw_json)
            except Exception:
                continue
            
            # Use tool name from regex match or fallback to payload
            name = tool_name or payload.get("tool") or payload.get("name")
            if not name:
                continue
            
            # Build args, remapping common parameter variations
            args_dict = {
                k: v for k, v in payload.items() if k not in ("tool", "name") and v is not None
            }

            mapped_name, normalized_args = _normalize_tool_name_and_args(name, args_dict)
            
            try:
                args_json = json.dumps(normalized_args)
            except Exception:
                args_json = "{}"
            counter += 1
            calls.append({
                "id": f"pseudo-{counter}",
                "type": "function",
                "function": {"name": mapped_name, "arguments": args_json}
            })
    except Exception:
        return []
    return calls

def _strip_pseudo_tool_markup(text: str) -> str:
    """Remove pseudo tool-call markup blocks from assistant text for clean display."""
    if not text:
        return text
    try:
        return _PSEUDO_TOOL_RE.sub("", text)
    except Exception:
        return text

def _convert_latex_format(text: str) -> str:
    """Normalize LaTeX math delimiters to `\(`, `\)`, `\[`, and `\]` as required by frontend rendering."""
    if not text:
        return text
    try:
        # 1. Convert block math expressed with $$ ... $$ to \[ ... \]
        def _replace_block(match: re.Match[str]) -> str:
            inner = match.group(1).strip()
            return f'\\[{inner}\\]'

        converted = re.sub(r'\$\$(.+?)\$\$', _replace_block, text, flags=re.DOTALL)

        # 2. Convert inline math expressed with single $ ... $ to \( ... \)
        def _replace_inline(match: re.Match[str]) -> str:
            inner = match.group(1).strip()
            return f'\\({inner}\\)'

        converted = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', _replace_inline, converted, flags=re.DOTALL)

        # 3. Convert custom bracket style [ \command ... ] to inline math
        def _replace_bracket(match: re.Match[str]) -> str:
            content = match.group(0)
            inner = content[1:-1].strip()
            return f'\\({inner}\\)'

        converted = re.sub(r'\[\s*\\[a-zA-Z]+.*?\]', _replace_bracket, converted, flags=re.DOTALL)

        return converted
    except Exception as e:
        logger.warning(f"Failed to convert LaTeX format: {e}")
        return text

@router.get("/models")
@router.head("/models")
def list_models():
    """List available AI models with enhanced selection support."""
    from app.services.openai_client import get_available_models

    available_models = get_available_models()

    # Format for frontend consumption
    models_list = []
    for model_key, config in available_models.items():
        models_list.append({
            "id": model_key,
            "name": config["display_name"],
            "description": config["description"],
            "provider": config["provider"],
            "available": config["available"],
            "default": config.get("default", False)
        })

    # Sort by availability first, then by default, then alphabetically
    models_list.sort(key=lambda x: (not x["available"], not x.get("default", False), x["name"]))

    return {
        "default": DEFAULT_MODEL,
        "available": models_list,
        "total_count": len(models_list),
        "available_count": len([m for m in models_list if m["available"]])
    }

@router.post("/stream")
async def chat_stream_endpoint(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Streaming chat endpoint with real-time response streaming, caching, and performance optimizations."""
    # Import performance optimizations
    from app.services.response_cache import (
        get_cached_response, should_use_fast_model
    )

    # Check cache first for performance boost
    cached_response = get_cached_response(req.prompt, req.deployment or DEFAULT_MODEL)
    if cached_response:
        # Return cached response as stream
        async def serve_cached():
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': cached_response.get('conversation_id', ''), 'model': 'cached', 'cached': True})}\n\n"
            content = cached_response.get('content', '')
            # Stream cached content in chunks for consistent UX
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'delta': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(serve_cached(), media_type="text/event-stream")

    # Use enhanced memory-aware message preparation with optimization
    # Inject locale-specific instruction into system prompt if requested
    sys_prompt = req.system_prompt
    if (req.locale or "en").lower().startswith("ja"):
        sys_prompt = (sys_prompt or "").rstrip() + _JAPANESE_DIRECTIVE

    messages, conv_id = await prepare_conversation_messages_with_memory(
        req.prompt, sys_prompt, req.conversation_id or "", req.reset, str(user.id)
    )

    # Performance optimization: detect simple queries and use fast model
    is_simple, query_type = is_simple_query(req.prompt)
    model_key = req.deployment or DEFAULT_MODEL
    
    if is_simple and not req.deployment:
        fast_model = get_fast_model_recommendation(req.prompt)
        if fast_model:
            logger.info(f"Using fast model {fast_model} for simple query type: {query_type}")
            model_key = fast_model
    
    # Performance optimization: skip heavy tools for simple queries
    skip_heavy = should_skip_rag_and_web_search(req.prompt)
    selected_tools = build_tools_for_request(req.prompt, getattr(req, "capabilities", None), skip_heavy_tools=skip_heavy)
    selected_tool_names = {tool.get("function", {}).get("name") for tool in selected_tools}
    logger.debug(
        "Selected tools for request %s: %s",
        conv_id,
        sorted(name for name in selected_tool_names if name),
    )

    # Use the enhanced model selection system with optimizations
    from app.services.openai_client import get_client_for_model

    # Set timeout based on query complexity
    timeout = 30 if is_simple else None

    try:
        client, model_name, resolved_config = get_client_for_model(model_key, timeout)
        logger.info(
            f"Using model: {model_key} -> {model_name} (timeout: {resolved_config.get('timeout', 'default')})"
        )
    except Exception as e:
        logger.error(f"Failed to get client for model {model_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Model '{model_key}' is not available: {e}")

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        nonlocal messages
        tool_call_results: List[Dict[str, Any]] = []
        suggested_tool_rounds = 0
        full_content = ""

        logger.debug("[chat_stream] Entered generate_stream for conversation %s model_key=%s", conv_id, model_key)

        # Track which tools we've already announced as running to the client
        announced_tools: set[str] = set()

        from app.core.config import AVAILABLE_MODELS
        model_metadata = AVAILABLE_MODELS.get(model_key, {})

        token_param_key = model_metadata.get("completion_token_param")
        if not token_param_key:
            model_identifier = model_metadata.get("model") or model_name
            if isinstance(model_identifier, str) and (model_identifier.startswith("gpt-5") or model_identifier.startswith("gpt-o3")):
                token_param_key = "max_completion_tokens"
            else:
                token_param_key = "max_tokens"

        def _apply_token_limit(params: Dict[str, Any], value: int) -> None:
            """Apply the correct token limit parameter based on model requirements."""
            params.pop("max_tokens", None)
            params.pop("max_completion_tokens", None)
            params[token_param_key] = value

        def _resolve_timeout(default: int = 60) -> int:
            return resolved_config.get("timeout", model_metadata.get("timeout", default))

        def _resolve_temperature(default: float = 0.7) -> float:
            if model_metadata.get("temperature_fixed"):
                return model_metadata["temperature"]
            return resolved_config.get("temperature", model_metadata.get("temperature", default))

        def _resolve_max_tokens(default: int) -> int:
            if "max_completion_tokens" in resolved_config:
                return resolved_config["max_completion_tokens"]
            if "max_completion_tokens" in model_metadata:
                return model_metadata["max_completion_tokens"]
            if "max_tokens" in model_metadata:
                return model_metadata["max_tokens"]
            return default

        def _resolve_max_tokens_with_cap(default: int) -> int:
            resolved = _resolve_max_tokens(default)
            return min(resolved, default)

        def _execute_single_tool(tc: Dict[str, Any]) -> tuple[str, Dict[str, Any], Optional[str]]:
            """Execute a single tool call. Returns (tool_call_id, result, error_message)."""
            try:
                tool_call_id = tc.get("id")
                fn = tc.get("function") or {}
                name = fn.get("name")
                raw_args = fn.get("arguments") or "{}"

                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception as e:
                    logger.warning(f"Failed to parse tool arguments for {name}: {e}")
                    args = {}

                impl = TOOL_REGISTRY.get(name)
                if not impl:
                    result = {"error": f"unknown tool: {name}"}
                else:
                    start_time = time.perf_counter()
                    result = impl(**(args or {}))
                    execution_time = time.perf_counter() - start_time
                    
                    # Special handling: summarize augmented news to keep context small 
                    if name == "get_augmented_news" and isinstance(result, dict):
                        summary = _build_news_summary(result)
                        result = {**summary}
                    # Truncate large generic tool results to control costs
                    elif isinstance(result, dict) and "items" in result and name != "get_augmented_news":
                        if len(result.get("items", [])) > 5:
                            result["items"] = result["items"][:5]
                            result["truncated"] = True
                    
                    logger.debug(f"Tool {name} executed in {execution_time:.3f}s")

                # Apply perplexity_search specific sanitation
                if name == "perplexity_search" and isinstance(result, dict):
                    result = _sanitize_perplexity_result(result)

                return tool_call_id, result, None
            except Exception as e:
                logger.error(f"Tool execution error for {tc}: {e}")
                return tc.get("id"), {"error": str(e)}, str(e)

        async def _run_tools_async(tc_list: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
            """Execute tool calls asynchronously with parallelization and yield progress updates."""
            nonlocal messages, tool_call_results
            
            # Validate tool calls first
            valid_tool_calls = []
            for tc in tc_list:
                try:
                    if (tc.get("type") or "function") != "function":
                        continue
                    if not tc.get("id") or not tc.get("function", {}).get("name"):
                        logger.warning(f"Skipping invalid tool call: {tc}")
                        continue
                    valid_tool_calls.append(tc)
                except Exception as e:
                    logger.error(f"Error validating tool call {tc}: {e}")
                    continue
            
            if not valid_tool_calls:
                return
            
            # Submit all tool calls to thread pool for parallel execution
            loop = asyncio.get_running_loop()
            
            # Create tasks with metadata
            task_to_tc = {}
            for tc in valid_tool_calls:
                task = loop.run_in_executor(_tool_executor, _execute_single_tool, tc)
                task_to_tc[task] = tc
            
            # Process results as they complete using asyncio.wait with FIRST_COMPLETED
            completed_tools = []
            pending_tasks = set(task_to_tc.keys())
            
            while pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    try:
                        tool_call_id, result, error = await task
                        tc = task_to_tc[task]
                        name = tc.get("function", {}).get("name", "unknown")
                        
                        # Truncate tool result content for token management, preserving web search citations
                        if name in _WEB_SEARCH_TOOL_NAMES and isinstance(result, dict):
                            payload = _build_web_search_tool_payload(result)
                            result_str = _safe_tool_result_json(payload)
                            if estimate_tokens(result_str) > 768:
                                compact_payload = dict(payload)
                                compact_payload.pop("top_sources", None)
                                result_str = _safe_tool_result_json(compact_payload)
                        else:
                            result_str = _safe_tool_result_json(result)
                            if estimate_tokens(result_str) > 512:
                                result_str = result_str[:2000] + "... [truncated]"

                        # Add tool result message
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_str,
                        })
                        
                        # Track results and yield updates
                        if error:
                            tool_call_results.append({"id": tool_call_id, "name": name, "error": error})
                            yield f"data: {{{_PRECOMPILED_RESPONSES['tool_error'](name, error)}}}\n\n"
                        else:
                            tool_call_results.append({"id": tool_call_id, "name": name, "result": result})
                            yield f"data: {{{_PRECOMPILED_RESPONSES['tool_completed'](name)}}}\n\n"
                        
                        completed_tools.append(name)
                        
                    except Exception as e:
                        logger.error(f"Error processing completed tool task: {e}")
                        tc = task_to_tc.get(task, {})
                        name = tc.get("function", {}).get("name", "unknown")
                        yield f"data: {{{_PRECOMPILED_RESPONSES['tool_error'](name, str(e))}}}\n\n"
            
            logger.info(f"Completed {len(completed_tools)} tool calls: {completed_tools}")

        # Send initial metadata with pre-compiled response
        yield f"data: {{{_PRECOMPILED_RESPONSES['start'](conv_id, model_name)}}}\n\n"

        try:
            # Handle tool calling with streaming (1 round only for faster responses)
            for iteration in range(1):
                # Check token budget before each API call - use cached token calculations
                from app.utils.token_utils import calculate_total_tokens, optimize_messages_for_token_budget
                
                current_tokens = calculate_total_tokens(messages)
                if current_tokens > MAX_TOKENS_PER_TURN * 0.95:  # Increased from 0.9 to 0.95
                    logger.warning(f"Approaching token limit ({current_tokens}), optimizing messages")
                    messages = optimize_messages_for_token_budget(
                        messages, 
                        int(MAX_TOKENS_PER_TURN * 0.9),
                        preserve_system=True,
                        preserve_recent_user=2  # Keep last 2 user messages
                    )
                
                # Final validation: ensure complete tool call/response pairs before API call
                from app.utils.conversation import _validate_message_sequence
                messages = _validate_message_sequence(messages)

                # Create streaming completion
                try:
                    model_timeout = _resolve_timeout()
                    # Increase max_tokens for better AI responses, especially after tool execution
                    # Normalize config key: some configs may still name it max_completion_tokens
                    max_tokens = _resolve_max_tokens(min(4000, MAX_TOKENS_PER_TURN // 2))
                    temperature = _resolve_temperature()

                    logger.info(
                        f"Creating stream for {model_key} with timeout={model_timeout}, "
                        f"{token_param_key}={max_tokens}"
                    )

                    # Build completion parameters
                    completion_params = {
                        "model": model_name,
                        "messages": messages,
                        "tools": selected_tools,
                        "tool_choice": "auto",
                        "stream": True,
                        "timeout": model_timeout,
                    }
                    _apply_token_limit(completion_params, max_tokens)
                    if not isinstance(client, AzureOpenAI):
                        # Optimize OpenAI streaming performance; Azure does not support stream_options
                        completion_params["stream_options"] = {"include_usage": False}
                    
                    # Only include temperature if model supports it
                    if not model_metadata.get("temperature_fixed"):
                        completion_params["temperature"] = temperature
                    
                    stream = client.chat.completions.create(**completion_params)
                except Exception as api_error:
                    logger.error(f"Failed to create streaming completion with {model_name}: {api_error}")
                    # Fallback to non-streaming once
                    try:
                        fallback_default = min(2000, MAX_TOKENS_PER_TURN // 4)
                        fallback_params = {
                            "model": model_name,
                            "messages": messages,
                            "tools": selected_tools,
                            "tool_choice": "auto",
                            "timeout": _resolve_timeout(),
                        }
                        _apply_token_limit(
                            fallback_params,
                            _resolve_max_tokens_with_cap(fallback_default)
                        )
                        # Only include temperature if model supports it
                        if not model_metadata.get("temperature_fixed"):
                            fallback_params["temperature"] = _resolve_temperature()
                        
                        completion = client.chat.completions.create(**fallback_params)
                        choice = (completion.choices or [None])[0]
                        msg = getattr(choice, "message", None)
                        content = getattr(msg, "content", "") if msg else ""
                        # Normalize content if it's a structured payload
                        if isinstance(content, list):
                            content = "".join(_normalize_content_piece(p) for p in content)
                        content = content or ""
                        if content:
                            full_content += content
                            yield f"data: {json.dumps({'type': 'content', 'delta': content})}\n\n"
                            messages.append({"role": "assistant", "content": content})
                            break
                        else:
                            yield f"data: {json.dumps({'type': 'error', 'error': 'No content returned by model'})}\n\n"
                            return
                    except Exception as e2:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'Model API error: {str(e2)}'})}\n\n"
                        return

                assistant_msg: Dict[str, Any] = {"role": "assistant", "content": ""}
                collected_tool_calls = []

                # Process streaming chunks with timeout protection
                try:
                    chunk_count = 0
                    any_text = False
                    for chunk in stream:
                        chunk_count += 1

                        # Safety check for runaway streams
                        if chunk_count > 1000:
                            logger.warning(f"Stream exceeded chunk limit for model {model_name}")
                            break

                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta

                        # Handle content streaming (support string or list shards)
                        if hasattr(delta, 'content') and delta.content:
                            if isinstance(delta.content, list):
                                # Join any textual pieces
                                piece_text = "".join(_normalize_content_piece(p) for p in delta.content)
                                if piece_text:
                                    # Skip raw tool call JSON outputs from GPT-5
                                    if _is_raw_tool_call_output(piece_text):
                                        logger.debug(f"Filtered out raw tool call JSON from {model_name}")
                                        continue
                                    
                                    # Convert LaTeX format for frontend compatibility
                                    converted_text = _convert_latex_format(piece_text)
                                    assistant_msg["content"] += converted_text
                                    full_content += converted_text
                                    any_text = True
                                    # Use pre-compiled response for better performance
                                    yield f"data: {{{_PRECOMPILED_RESPONSES['content'](converted_text)}}}\n\n"
                            elif isinstance(delta.content, str):
                                # Skip raw tool call JSON outputs from GPT-5
                                if _is_raw_tool_call_output(delta.content):
                                    logger.debug(f"Filtered out raw tool call JSON from {model_name}")
                                    continue
                                
                                # Convert LaTeX format for frontend compatibility
                                converted_text = _convert_latex_format(delta.content)
                                assistant_msg["content"] += converted_text
                                full_content += converted_text
                                any_text = True
                                # Use pre-compiled response for better performance
                                yield f"data: {{{_PRECOMPILED_RESPONSES['content'](converted_text)}}}\n\n"

                        # Handle tool calls streamed by the model
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            newly_seen: List[str] = []
                            for tc in delta.tool_calls:
                                # Extend or create tool call entries
                                idx = 0
                                try:
                                    idx = int(getattr(tc, 'index', 0) or 0)
                                except Exception:
                                    idx = 0
                                while len(collected_tool_calls) <= idx:
                                    collected_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })

                                if getattr(tc, 'id', None):
                                    collected_tool_calls[idx]["id"] = tc.id
                                if getattr(tc, 'function', None) and getattr(tc.function, 'name', None):
                                    name = tc.function.name
                                    collected_tool_calls[idx]["function"]["name"] = name
                                    if name and name not in announced_tools:
                                        announced_tools.add(name)
                                        newly_seen.append(name)
                                        # Emit an immediate running status for this tool with pre-compiled response
                                        yield f"data: {{{_PRECOMPILED_RESPONSES['tool_running'](name)}}}\n\n"
                                if getattr(tc, 'function', None) and getattr(tc.function, 'arguments', None):
                                    collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

                            # Also emit a batched tool list once, when we first see any
                            if newly_seen:
                                yield f"data: {json.dumps({'type': 'tool_calls', 'tools': newly_seen})}\n\n"
                except Exception as stream_error:
                    logger.error(f"Error processing stream chunks for model {model_name}: {stream_error}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Streaming error: {str(stream_error)}'})}\n\n"
                    return

                # If we have tool calls, execute them
                if collected_tool_calls:
                    # Validate all tool calls have required fields before adding to messages
                    valid_tool_calls = []
                    for tc in collected_tool_calls:
                        if tc.get("id") and tc.get("function", {}).get("name"):
                            valid_tool_calls.append(tc)
                        else:
                            logger.warning(f"Skipping invalid tool call: {tc}")
                    
                    if valid_tool_calls:
                        assistant_msg["tool_calls"] = valid_tool_calls
                        messages.append(assistant_msg)

                        # If not yet announced (e.g., non-stream tool_calls), notify
                        yield f"data: {json.dumps({'type': 'tool_calls', 'tools': [tc['function']['name'] for tc in valid_tool_calls]})}\n\n"

                        # Execute tools asynchronously and yield updates as they complete
                        async for update in _run_tools_async(valid_tool_calls):
                            yield update

                        # Continue loop for next iteration
                        continue
                    else:
                        logger.warning("All tool calls were invalid, treating as regular assistant message")
                        # Treat as regular message if no valid tool calls
                        messages.append(assistant_msg)
                        break
                else:
                    # Pseudo tool call fallback: parse assistant content for OSS-style tool markup
                    if assistant_msg.get("content"):
                        pseudo_calls = _extract_pseudo_tool_calls(assistant_msg["content"]) or []
                        if pseudo_calls:
                            # Strip markup from content for display
                            assistant_msg["content"] = _strip_pseudo_tool_markup(assistant_msg["content"]) or ""
                            messages.append(assistant_msg)
                            yield f"data: {json.dumps({'type': 'content', 'delta': assistant_msg['content']})}\n\n"

                            # Notify and execute pseudo tool calls
                            yield f"data: {json.dumps({'type': 'tool_calls', 'tools': [tc['function']['name'] for tc in pseudo_calls], 'pseudo': True})}\n\n"
                            async for update in _run_tools_async(pseudo_calls):
                                yield update
                            # Continue loop to allow the model to use tool results
                            continue

                        suggested_calls = _extract_suggested_tool_calls(assistant_msg["content"]) or []
                        if suggested_calls:
                            if suggested_tool_rounds >= MAX_SUGGESTED_TOOL_ROUNDS:
                                logger.info(
                                    "Skipping suggested tool calls due to round limit (round=%s, tools=%s)",
                                    suggested_tool_rounds,
                                    [call["function"]["name"] for call in suggested_calls],
                                )
                            else:
                                next_round = suggested_tool_rounds + 1
                                augmented_calls: List[Dict[str, Any]] = []
                                for idx, call in enumerate(suggested_calls, start=1):
                                    function_payload = dict(call.get("function", {}))
                                    augmented_calls.append({
                                        "id": f"suggested-{next_round}-{idx}",
                                        "type": "function",
                                        "function": function_payload,
                                    })

                                assistant_msg["tool_calls"] = augmented_calls
                                messages.append(assistant_msg)
                                suggested_tool_rounds = next_round

                                yield f"data: {json.dumps({'type': 'tool_calls', 'tools': [tc['function']['name'] for tc in augmented_calls], 'suggested': True, 'round': suggested_tool_rounds})}\n\n"
                                async for update in _run_tools_async(augmented_calls):
                                    yield update
                                continue

                    # No tool calls; if no streamed text, fallback to single-shot completion
                    if not assistant_msg.get("content"):
                        try:
                            no_stream_default = min(2000, MAX_TOKENS_PER_TURN // 4)
                            no_stream_params = {
                                "model": model_name,
                                "messages": messages,
                                "tools": selected_tools,
                                "tool_choice": "auto",
                                "timeout": _resolve_timeout(),
                            }
                            _apply_token_limit(
                                no_stream_params,
                                _resolve_max_tokens_with_cap(no_stream_default)
                            )
                            if not model_metadata.get("temperature_fixed"):
                                no_stream_params["temperature"] = _resolve_temperature()
                                
                            completion = client.chat.completions.create(**no_stream_params)
                            choice = (completion.choices or [None])[0]
                            msg = getattr(choice, "message", None)
                            content = getattr(msg, "content", "") if msg else ""
                            if isinstance(content, list):
                                content = "".join(_normalize_content_piece(p) for p in content)
                            content = content or ""
                            if content:
                                converted_content = _convert_latex_format(content)
                                assistant_msg["content"] = converted_content
                                full_content += converted_content
                                yield f"data: {json.dumps({'type': 'content', 'delta': converted_content})}\n\n"
                            else:
                                logger.info("Model returned empty content after stream; sending empty message")
                        except Exception as e:
                            logger.error(f"Fallback non-stream completion failed: {e}")

                    messages.append(assistant_msg)
                    break

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        # FORCE AI to generate response when tools were executed - don't just use fallback
        if tool_call_results and not full_content:
            # Try one more time to get AI response with emphasis on responding
            try:
                # Add a message to encourage AI response
                response_prompt = "Based on the tool results above, please provide a comprehensive response to the user's question in the appropriate language."
                messages.append({"role": "user", "content": response_prompt})
                
                retry_default = min(4000, MAX_TOKENS_PER_TURN // 2)
                ai_retry_params = {
                    "model": model_name,
                    "messages": messages,
                    "timeout": _resolve_timeout(),
                }
                _apply_token_limit(
                    ai_retry_params,
                    _resolve_max_tokens_with_cap(retry_default)
                )
                if not model_metadata.get("temperature_fixed"):
                    ai_retry_params["temperature"] = _resolve_temperature()
                    
                completion = client.chat.completions.create(**ai_retry_params)
                choice = (completion.choices or [None])[0]
                msg = getattr(choice, "message", None)
                content = getattr(msg, "content", "") if msg else ""
                if isinstance(content, list):
                    content = "".join(_normalize_content_piece(p) for p in content)
                
                if content and content.strip():
                    converted_content = _convert_latex_format(content)
                    full_content += converted_content
                    yield f"data: {json.dumps({'type': 'content', 'delta': converted_content})}\n\n"
                    messages.append({"role": "assistant", "content": converted_content})
                    
            except Exception as ai_retry_error:
                logger.error(f"Failed to force AI response: {ai_retry_error}")
                
        # If AI still didn't respond after retry, use fallback
        if tool_call_results and not full_content:
            # Fallback: provide a comprehensive summary when AI completely fails
            try:
                # Check if this is a Japanese request to format appropriately
                is_japanese = False
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        if any(ord(c) > 0x3000 for c in content):  # Contains Japanese characters
                            is_japanese = True
                            break
                
                fallback_parts = []
                
                # Process all tool results, not just the last one
                for tool_result in tool_call_results:
                    if not isinstance(tool_result, dict):
                        continue
                    
                    name = tool_result.get("name")
                    res = tool_result.get("result") or {}
                    
                    if name == "get_company_profile" and isinstance(res, dict):
                        if is_japanese:
                            fallback_parts.append(_human_preview_company_profile_jp(res))
                        else:
                            fallback_parts.append(_human_preview_company_profile(res))
                    elif name == "get_stock_quote" and isinstance(res, dict):
                        if is_japanese:
                            fallback_parts.append(_human_preview_quote_jp(res))
                        else:
                            fallback_parts.append(_human_preview_quote(res))
                    elif name == "get_historical_prices" and isinstance(res, dict):
                        if is_japanese:
                            fallback_parts.append(_human_preview_historical_jp(res))
                        else:
                            fallback_parts.append(_human_preview_historical(res))
                
                # Combine all parts or use generic fallback
                if fallback_parts:
                    fallback = "\n\n".join(fallback_parts)
                else:
                    # Generic JSON fallback for unhandled tools
                    try:
                        last = tool_call_results[-1] if tool_call_results else None
                        fallback = _safe_tool_result_json(last.get("result"))[:400] + "..."  # soft limit
                    except Exception:
                        fallback = "(tool result received)"
                
                converted_fallback = _convert_latex_format(fallback)
                full_content += converted_fallback
                yield f"data: {json.dumps({'type': 'content', 'delta': converted_fallback})}\n\n"
                # Also append to messages so it persists in history
                messages.append({"role": "assistant", "content": converted_fallback})
            except Exception as e:
                logger.error(f"Fallback generation error: {e}")
                pass

        # Store conversation with enhanced memory
        try:
            await store_conversation_messages_with_memory(conv_id, messages, str(user.id))

            db.add(Log(
                user_id=int(user.id),
                action="chat_stream",
                conversation_id=conv_id,
                prompt=req.prompt[:1000] if len(req.prompt) > 1000 else req.prompt,
                response=full_content[:2000] if len(full_content) > 2000 else full_content,
                tool_calls=tool_call_results
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Database error in streaming: {e}")
            db.rollback()

        # Send completion status
        completion_data = {
            'type': 'done', 
            'conversation_id': conv_id, 
            'tool_calls': tool_call_results
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Main chat endpoint with AI conversation, tool calling, and enhanced memory."""
    # If streaming is requested, redirect to streaming endpoint
    if req.stream:
        raise HTTPException(status_code=400, detail="Use /chat/stream endpoint for streaming responses")

    # Use the new enhanced model selection system
    from app.services.openai_client import get_client_for_model

    # Resolve model key - use deployment parameter as model key, fallback to default
    model_key = req.deployment or DEFAULT_MODEL
    
    # Performance optimization: use fast model for simple queries
    is_simple, query_type = is_simple_query(req.prompt)
    if is_simple and not req.deployment:
        # User didn't specify a model, so we can use fast model
        fast_model = get_fast_model_recommendation(req.prompt)
        if fast_model:
            logger.info(f"Using fast model {fast_model} for simple query type: {query_type}")
            model_key = fast_model
    
    # Check request cache for identical queries (performance optimization)
    sys_prompt = req.system_prompt or ""
    if not req.reset and not req.conversation_id:
        # Only cache for new conversations without reset
        cached = get_cached_response(req.prompt, model_key, sys_prompt)
        if cached:
            logger.info(f"Returning cached response for prompt hash")
            return ChatResponse(**cached)
        
        # Check if an identical request is already being processed
        if is_request_in_flight(req.prompt, model_key, sys_prompt):
            logger.info(f"Identical request already in flight, waiting...")
            # Wait a bit and check cache again (the in-flight request might complete)
            import asyncio
            await asyncio.sleep(0.5)
            cached = get_cached_response(req.prompt, model_key, sys_prompt)
            if cached:
                return ChatResponse(**cached)
        
        # Mark this request as in-flight
        mark_request_in_flight(req.prompt, model_key, sys_prompt)

    # Use enhanced memory-aware message preparation
    # Inject locale-specific instruction into system prompt if requested
    sys_prompt = req.system_prompt
    if (req.locale or "en").lower().startswith("ja"):
        sys_prompt = (sys_prompt or "").rstrip() + _JAPANESE_DIRECTIVE

    messages, conv_id = await prepare_conversation_messages_with_memory(
        req.prompt, sys_prompt, req.conversation_id or "", req.reset, str(user.id), model_key
    )

    # Performance optimization: skip heavy tools for simple queries
    skip_heavy = should_skip_rag_and_web_search(req.prompt)
    selected_tools = build_tools_for_request(req.prompt, getattr(req, "capabilities", None), skip_heavy_tools=skip_heavy)
    selected_tool_names = {tool.get("function", {}).get("name") for tool in selected_tools}
    logger.debug(
        "Selected tools for request %s: %s",
        conv_id,
        sorted(name for name in selected_tool_names if name),
    )

    try:
        client, model_name, client_config = get_client_for_model(model_key)
        logger.info(f"Using model: {model_key} -> {model_name}")
    except Exception as e:
        logger.error(f"Failed to get client for model {model_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Model '{model_key}' is not available: {e}")

    tool_call_results: List[Dict[str, Any]] = []
    suggested_tool_rounds = 0

    from app.core.config import AVAILABLE_MODELS
    model_metadata = AVAILABLE_MODELS.get(model_key, {})

    token_param_key = model_metadata.get("completion_token_param")
    if not token_param_key:
        model_identifier = model_metadata.get("model") or model_name
        if isinstance(model_identifier, str) and model_identifier.startswith("gpt-5"):
            token_param_key = "max_completion_tokens"
        else:
            token_param_key = "max_tokens"

    def apply_token_limit(params: Dict[str, Any], value: int) -> None:
        params.pop("max_tokens", None)
        params.pop("max_completion_tokens", None)
        params[token_param_key] = value

    def resolve_timeout(default: int = 60) -> int:
        return client_config.get("timeout", model_metadata.get("timeout", default))

    def resolve_temperature(default: float = 0.7) -> float:
        if model_metadata.get("temperature_fixed"):
            return model_metadata["temperature"]
        return client_config.get("temperature", model_metadata.get("temperature", default))

    def resolve_max_tokens(default: int) -> int:
        if "max_completion_tokens" in client_config:
            return client_config["max_completion_tokens"]
        if "max_completion_tokens" in model_metadata:
            return model_metadata["max_completion_tokens"]
        if "max_tokens" in model_metadata:
            return model_metadata["max_tokens"]
        return default

    def resolve_max_tokens_with_cap(default: int) -> int:
        resolved = resolve_max_tokens(default)
        return min(resolved, default)


    def _run_tools(tc_list: List[Dict[str, Any]], max_rounds: int = 2):
        """Execute tool calls and append results to messages."""
        pending_calls: List[Dict[str, Any]] = list(tc_list or [])
        rounds_executed = 0

        while pending_calls and rounds_executed < max_rounds:
            rounds_executed += 1

            # Only process valid tool calls to avoid OpenAI validation errors
            valid_tool_calls: List[Dict[str, Any]] = []
            for tc in pending_calls:
                try:
                    if (tc.get("type") or "function") != "function":
                        continue

                    tool_call_id = tc.get("id")
                    if not tool_call_id:
                        logger.warning(f"Tool call missing ID: {tc}")
                        continue

                    fn = tc.get("function") or {}
                    name = fn.get("name")
                    if not name:
                        logger.warning(f"Tool call missing function name: {tc}")
                        continue

                    valid_tool_calls.append(tc)
                except Exception as e:
                    logger.error(f"Error validating tool call {tc}: {e}")
                    continue

            if not valid_tool_calls:
                break

            pending_calls = []  # Reset; may be repopulated in future enhancements

            for tc in valid_tool_calls:
                try:
                    tool_call_id = tc.get("id")
                    fn = tc.get("function") or {}
                    name = fn.get("name")

                    raw_args = fn.get("arguments") or "{}"

                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    except Exception as e:
                        logger.warning(f"Failed to parse tool arguments for {name}: {e}")
                        args = {}

                    impl = TOOL_REGISTRY.get(name)
                    if not impl:
                        result = {"error": f"unknown tool: {name}"}
                    else:
                        try:
                            result = impl(**(args or {}))
                            if name == "get_augmented_news" and isinstance(result, dict):
                                result = _build_news_summary(result)
                            if isinstance(result, dict) and "items" in result and name != "get_augmented_news":
                                if len(result.get("items", [])) > 5:
                                    result["items"] = result["items"][:5]
                                    result["truncated"] = True
                            if name == "perplexity_search" and isinstance(result, dict):
                                result = _sanitize_perplexity_result(result)
                        except Exception as e:
                            logger.error(f"Tool execution error for {name}: {e}")
                            result = {"error": str(e)}

                    if name in _WEB_SEARCH_TOOL_NAMES and isinstance(result, dict):
                        payload = _build_web_search_tool_payload(result)
                        result_str = _safe_tool_result_json(payload)
                        if estimate_tokens(result_str) > 768:
                            compact_payload = dict(payload)
                            compact_payload.pop("top_sources", None)
                            result_str = _safe_tool_result_json(compact_payload)
                    else:
                        result_str = _safe_tool_result_json(result)
                        if estimate_tokens(result_str) > 512:
                            result_str = result_str[:2000] + "... [truncated]"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str,
                    })
                    tool_call_results.append({"id": tool_call_id, "name": name, "result": result})
                except Exception as e:
                    logger.error(f"Unexpected error processing tool call {tc}: {e}")
                    tool_call_id = tc.get("id") if isinstance(tc, dict) else None
                    if tool_call_id:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps({"error": f"Tool execution failed: {str(e)}"}),
                        })
                    tool_call_results.append({
                        "id": tool_call_id,
                        "name": (tc.get("function") or {}).get("name") if isinstance(tc, dict) else "unknown",
                        "error": str(e)
                    })

    # Single round of tool calling for faster responses
    final_content: Optional[str] = None
    for iteration in range(1):
        try:
            # Check token budget before each API call - use cached token calculations
            from app.utils.token_utils import calculate_total_tokens, optimize_messages_for_token_budget
            
            current_tokens = calculate_total_tokens(messages)
            if current_tokens > MAX_TOKENS_PER_TURN * 0.95:  # Increased from 0.9 to 0.95
                logger.warning(f"Approaching token limit ({current_tokens}), optimizing messages")
                messages = optimize_messages_for_token_budget(
                    messages, 
                    int(MAX_TOKENS_PER_TURN * 0.9),
                    preserve_system=True,
                    preserve_recent_user=2  # Keep last 2 user messages
                )
            
            # Final validation: ensure complete tool call/response pairs before API call
            from app.utils.conversation import _validate_message_sequence
            messages = _validate_message_sequence(messages)

            completion_params = {
                "model": model_name,
                "messages": messages,
                "tools": selected_tools,
                "tool_choice": "auto",
                "timeout": resolve_timeout(),
            }
            apply_token_limit(
                completion_params,
                resolve_max_tokens(min(4000, MAX_TOKENS_PER_TURN // 2))
            )
            
            # Only include temperature if model supports it
            if not model_metadata.get("temperature_fixed"):
                completion_params["temperature"] = resolve_temperature()
                
            completion = client.chat.completions.create(**completion_params)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

        choice = (completion.choices or [None])[0]
        if not choice or not getattr(choice, "message", None):
            raise HTTPException(status_code=500, detail="No completion returned")

        msg = getattr(choice, "message", None)
        # Normalize to dict
        raw_content = getattr(msg, "content", None) if msg else ""
        if isinstance(raw_content, list):
            # Join structured content parts if any
            content_joined = "".join(
                (p.get("text") if isinstance(p, dict) and isinstance(p.get("text"), str) else str(p))
                for p in raw_content
            )
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content_joined}
        else:
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": raw_content}

        # Handle tool calls
        tc = []
        try:
            tc = [
                {
                    "id": t.id,
                    "type": t.type,
                    "function": {"name": t.function.name, "arguments": t.function.arguments},
                }
                for t in (msg.tool_calls or [])
            ] if msg else []
        except Exception:
            # Already dicts
            tc = getattr(msg, "tool_calls", None) or []

        if tc:
            # Validate all tool calls have required fields before adding to messages
            valid_tool_calls = []
            for tool_call in tc:
                if tool_call.get("id") and tool_call.get("function", {}).get("name"):
                    valid_tool_calls.append(tool_call)
                else:
                    logger.warning(f"Skipping invalid tool call: {tool_call}")
            
            if valid_tool_calls:
                assistant_msg["tool_calls"] = valid_tool_calls
                messages.append(assistant_msg)
                _run_tools(valid_tool_calls)
                # Continue the loop to send tool outputs back to the model
                continue
            else:
                logger.warning("All tool calls were invalid, treating as regular assistant message")
                # Treat as regular message if no valid tool calls
                messages.append(assistant_msg)

        # Fallback: check for pseudo tool-calls embedded in text
        if assistant_msg.get("content"):
            pseudo_calls = _extract_pseudo_tool_calls(assistant_msg["content"]) or []
            if pseudo_calls:
                assistant_msg["content"] = _strip_pseudo_tool_markup(assistant_msg["content"]) or ""
                messages.append(assistant_msg)
                _run_tools(pseudo_calls)
                # Continue loop to send tool outputs back to the model
                continue

        if assistant_msg.get("content"):
            suggested_calls = _extract_suggested_tool_calls(assistant_msg["content"]) or []
            if suggested_calls:
                if suggested_tool_rounds >= MAX_SUGGESTED_TOOL_ROUNDS:
                    logger.info(
                        "Skipping suggested tool calls in sync flow due to round limit (round=%s, tools=%s)",
                        suggested_tool_rounds,
                        [call["function"]["name"] for call in suggested_calls],
                    )
                else:
                    next_round = suggested_tool_rounds + 1
                    augmented_calls: List[Dict[str, Any]] = []
                    for idx, call in enumerate(suggested_calls, start=1):
                        function_payload = dict(call.get("function", {}))
                        augmented_calls.append({
                            "id": f"suggested-{next_round}-{idx}",
                            "type": "function",
                            "function": function_payload,
                        })

                    assistant_msg["tool_calls"] = augmented_calls
                    messages.append(assistant_msg)
                    suggested_tool_rounds = next_round
                    _run_tools(augmented_calls)
                    continue

        # No tool calls; finalize
        final_content = assistant_msg.get("content") or ""
        if isinstance(final_content, list):
            final_content = "".join(
                (p.get("text") if isinstance(p, dict) and isinstance(p.get("text"), str) else str(p))
                for p in final_content
            )
        
        # Filter out raw tool call JSON outputs from GPT-5
        if _is_raw_tool_call_output(final_content):
            logger.info(f"Filtered out raw tool call JSON from non-streaming response")
            final_content = "検索を実行中です。しばらくお待ちください。"  # "Executing search. Please wait."
        
        # Convert LaTeX format for frontend compatibility
        final_content = _convert_latex_format(final_content)
        assistant_msg["content"] = final_content
        messages.append(assistant_msg)
        break
    # Store conversation with enhanced memory
    await store_conversation_messages_with_memory(conv_id, messages, str(user.id))

    # FORCE AI to generate response when tools were executed - don't just use fallback
    if (not final_content or not str(final_content).strip()) and tool_call_results:
        try:
            # Add a message to encourage AI response
            response_prompt = "Based on the tool results above, please provide a comprehensive response to the user's question in the appropriate language."
            messages.append({"role": "user", "content": response_prompt})
            
            retry_default = min(4000, MAX_TOKENS_PER_TURN // 2)
            final_retry_params = {
                "model": model_name,
                "messages": messages,
                "timeout": resolve_timeout(),
            }
            apply_token_limit(
                final_retry_params,
                resolve_max_tokens_with_cap(retry_default)
            )
            # Only include temperature if model supports it
            if not model_metadata.get("temperature_fixed"):
                final_retry_params["temperature"] = resolve_temperature()
                
            completion = client.chat.completions.create(**final_retry_params)
            choice = (completion.choices or [None])[0]
            msg = getattr(choice, "message", None)
            content = getattr(msg, "content", "") if msg else ""
            if isinstance(content, list):
                content = "".join(_normalize_content_piece(p) for p in content)
            
            if content and content.strip():
                final_content = _convert_latex_format(content)
            
        except Exception as ai_retry_error:
            logger.error(f"Failed to force AI response in non-streaming: {ai_retry_error}")
    
    # If AI still didn't respond after retry, use fallback
    if (not final_content or not str(final_content).strip()) and tool_call_results:
        try:
            # Check if this is a Japanese request
            is_japanese = False
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if any(ord(c) > 0x3000 for c in content):  # Contains Japanese characters
                        is_japanese = True
                        break
            
            fallback_parts = []
            
            # Process all tool results, not just the last one
            for tool_result in tool_call_results:
                if not isinstance(tool_result, dict):
                    continue
                
                name = tool_result.get("name")
                res = tool_result.get("result") or {}
                
                if name == "get_company_profile" and isinstance(res, dict):
                    if is_japanese:
                        fallback_parts.append(_human_preview_company_profile_jp(res))
                    else:
                        fallback_parts.append(_human_preview_company_profile(res))
                elif name == "get_stock_quote" and isinstance(res, dict):
                    if is_japanese:
                        fallback_parts.append(_human_preview_quote_jp(res))
                    else:
                        fallback_parts.append(_human_preview_quote(res))
                elif name == "get_historical_prices" and isinstance(res, dict):
                    if is_japanese:
                        fallback_parts.append(_human_preview_historical_jp(res))
                    else:
                        fallback_parts.append(_human_preview_historical(res))
            
            # Combine all parts or use generic fallback
            if fallback_parts:
                final_content = _convert_latex_format("\n\n".join(fallback_parts))
            else:
                # Generic JSON fallback for unhandled tools
                try:
                    last = tool_call_results[-1] if tool_call_results else None
                    final_content = _convert_latex_format(
                        _safe_tool_result_json(last.get("result"))[:400] + "..."
                    )
                except Exception:
                    final_content = "(tool result received)"
        except Exception as e:
            logger.error(f"Non-streaming fallback generation error: {e}")
            pass

    # Use final content as the enhanced content (already converted in the loop above)
    enhanced_content = final_content or ""

    # Prepare response
    response = ChatResponse(
        content=enhanced_content or "", 
        tool_calls=tool_call_results or None, 
        conversation_id=conv_id
    )
    
    # Cache the response for future identical requests (if new conversation)
    if not req.reset and not req.conversation_id:
        try:
            cache_response(req.prompt, model_key, sys_prompt, response.dict())
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
        finally:
            # Always clear in-flight marker
            clear_request_in_flight(req.prompt, model_key, sys_prompt)

    # Log action
    try:
        db.add(Log(
            user_id=int(user.id),
            action="chat",
            conversation_id=conv_id,
            prompt=req.prompt[:1000] if len(req.prompt) > 1000 else req.prompt,
            response=enhanced_content[:2000] if enhanced_content and len(enhanced_content) > 2000 else enhanced_content,
            tool_calls=tool_call_results
        ))
        db.commit()
    except Exception:
        db.rollback()

    return response

@router.post("/clear")
def chat_clear(payload: Dict[str, Any], _: User = Depends(get_current_user)):
    """Clear a conversation history."""
    conv_id = (payload.get("conversation_id") or "").strip()
    if not conv_id:
        raise HTTPException(status_code=400, detail="conversation_id required")
    
    existed = conv_clear(conv_id)
    return {"conversation_id": conv_id, "cleared": existed}

@router.get("/history/{conversation_id}", response_model=ChatHistoryResponse)
def chat_history(
    conversation_id: str, 
    include_system: bool = False, 
    max_messages: Optional[int] = None, 
    _: User = Depends(get_current_user)
):
    """Get conversation history."""
    msgs = conv_get(conversation_id)
    out: List[Dict[str, Any]] = []
    
    for m in msgs:
        role = m.get("role")
        if not include_system and role == "system":
            continue
        if role in {"user", "assistant", "system"}:
            out.append({"role": role, "content": m.get("content") or ""})
    
    if isinstance(max_messages, int) and max_messages > 0:
        out = out[-max_messages:]
    
    return ChatHistoryResponse(
        conversation_id=conversation_id, 
        found=bool(msgs), 
        messages=[ChatMessage(**mm) for mm in out]
    )

# Cleanup function for graceful shutdown
async def cleanup_chat_resources():
    """Cleanup chat-related resources like thread pools and connection pools."""
    try:
        # Shutdown thread pool
        _tool_executor.shutdown(wait=True, cancel_futures=False)
        logger.info("Tool executor thread pool shut down")
        
        # Cleanup connection pools
        await connection_pool.cleanup()
        logger.info("Connection pools cleaned up")
    except Exception as e:
        logger.error(f"Error during chat resource cleanup: {e}")
