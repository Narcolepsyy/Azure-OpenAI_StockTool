"""Chat API routes for conversational AI functionality."""
import json
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Log
from app.models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessage
from app.auth.dependencies import get_current_user
from app.core.config import DEFAULT_MODEL
from app.utils.conversation import (
    conv_clear, conv_get, estimate_tokens, MAX_TOKENS_PER_TURN,
    prepare_conversation_messages_with_memory, store_conversation_messages_with_memory
)
from app.utils.tools import tools_spec, TOOL_REGISTRY

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# --- Pseudo tool-call compatibility (e.g., OSS models emitting special markup) ---
_PSEUDO_TOOL_RE = re.compile(
    r"<\|start\|>assistant<\|channel\|>commentary<\|message\|>(\{.*?\})<\|call\|>",
    re.DOTALL | re.IGNORECASE,
)

def _extract_pseudo_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Parse pseudo tool calls embedded in assistant text into standard tool_call format."""
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls
    try:
        matches = list(_PSEUDO_TOOL_RE.finditer(text))
        counter = 0
        for m in matches:
            raw_json = m.group(1)
            try:
                payload = json.loads(raw_json)
            except Exception:
                continue
            name = payload.get("tool") or payload.get("name")
            if not name:
                continue
            # Build args, remapping ticker->symbol if present
            args_dict = {k: v for k, v in payload.items() if k not in ("tool", "name")}
            if "ticker" in args_dict and "symbol" not in args_dict:
                args_dict["symbol"] = args_dict.pop("ticker")
            try:
                args_json = json.dumps(args_dict)
            except Exception:
                args_json = "{}"
            counter += 1
            calls.append({
                "id": f"pseudo-{counter}",
                "type": "function",
                "function": {"name": name, "arguments": args_json}
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

@router.get("/models")
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
    messages, conv_id = await prepare_conversation_messages_with_memory(
        req.prompt, req.system_prompt, req.conversation_id or "", req.reset, str(user.id)
    )

    # Smart model selection based on query complexity
    model_key = req.deployment or DEFAULT_MODEL
    use_fast_model, fast_model = should_use_fast_model(req.prompt)

    if use_fast_model and not req.deployment:  # Only override if no specific model requested
        model_key = fast_model
        logger.info(f"Using fast model {fast_model} for simple query")

    # Use the enhanced model selection system with optimizations
    from app.services.openai_client import get_client_for_model

    # Set timeout based on query complexity
    timeout = 30 if use_fast_model else None

    try:
        client, model_name, model_config = get_client_for_model(model_key, timeout)
        logger.info(f"Using model: {model_key} -> {model_name} (timeout: {model_config.get('timeout', 'default')})")
    except Exception as e:
        logger.error(f"Failed to get client for model {model_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Model '{model_key}' is not available: {e}")

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

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        nonlocal messages
        tool_call_results: List[Dict[str, Any]] = []
        full_content = ""

        def _run_tools_sync(tc_list: List[Dict[str, Any]]) -> List[str]:
            """Execute tool calls synchronously and return updates."""
            nonlocal messages, tool_call_results
            updates = []

            for tc in tc_list:
                try:
                    if (tc.get("type") or "function") != "function":
                        continue

                    fn = tc.get("function") or {}
                    name = fn.get("name")
                    raw_args = fn.get("arguments") or "{}"

                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    except Exception:
                        args = {}

                    impl = TOOL_REGISTRY.get(name)
                    if not impl:
                        result = {"error": f"unknown tool: {name}"}
                    else:
                        try:
                            result = impl(**(args or {}))
                            # Special handling: summarize augmented news to keep context small and user-visible
                            if name == "get_augmented_news" and isinstance(result, dict):
                                summary = _build_news_summary(result)
                                preview = _human_preview_from_summary(summary)
                                # Replace result with summary for the model
                                result = {**summary}
                                # Stream a short preview to the user immediately
                                updates.append(f"data: {json.dumps({'type': 'content', 'delta': preview + '\n'})}\n\n")
                            # Truncate large generic tool results to control costs
                            if isinstance(result, dict) and "items" in result and name != "get_augmented_news":
                                if len(result.get("items", [])) > 5:
                                    result["items"] = result["items"][:5]
                                    result["truncated"] = True
                        except Exception as e:
                            result = {"error": str(e)}

                    # Truncate tool result content for token management
                    result_str = json.dumps(result)
                    if estimate_tokens(result_str) > 512:
                        result_str = result_str[:2000] + "... [truncated]"

                    # Append tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": result_str,
                    })
                    tool_call_results.append({"id": tc.get("id"), "name": name, "result": result})

                    # Add tool execution update
                    updates.append(f"data: {json.dumps({'type': 'tool_call', 'name': name, 'status': 'completed'})}\n\n")

                except Exception as e:
                    tool_call_results.append({
                        "id": tc.get("id"),
                        "name": (tc.get("function") or {}).get("name"),
                        "error": str(e)
                    })
                    updates.append(f"data: {json.dumps({'type': 'tool_call', 'name': (tc.get('function') or {}).get('name', 'unknown'), 'status': 'error', 'error': str(e)})}\n\n")

            return updates

        # Send initial metadata
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id, 'model': model_name})}\n\n"

        try:
            # Handle tool calling with streaming
            for iteration in range(3):
                # Check token budget before each API call
                current_tokens = sum(estimate_tokens(json.dumps(m)) for m in messages)
                if current_tokens > MAX_TOKENS_PER_TURN * 0.9:
                    logger.warning(f"Approaching token limit ({current_tokens}), truncating messages")
                    essential_msgs = [m for m in messages if m.get("role") in {"system", "user"}]
                    tool_msgs = [m for m in messages if m.get("role") == "tool"][-3:]
                    messages = essential_msgs + tool_msgs

                # Create streaming completion
                try:
                    # Get model-specific configuration
                    from app.core.config import AVAILABLE_MODELS
                    model_config = AVAILABLE_MODELS.get(model_key, {})
                    model_timeout = model_config.get("timeout", 60)
                    max_tokens = model_config.get("max_completion_tokens", min(2000, MAX_TOKENS_PER_TURN // 4))
                    temperature = model_config.get("temperature", 0.7)

                    logger.info(f"Creating stream for {model_key} with timeout={model_timeout}, max_tokens={max_tokens}")

                    stream = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        tools=tools_spec,
                        tool_choice="auto",
                        max_completion_tokens=max_tokens,
                        temperature=temperature,
                        stream=True,
                        timeout=model_timeout,
                        # Optimize for streaming performance
                        stream_options={"include_usage": False}  # Reduce overhead
                    )
                except Exception as api_error:
                    logger.error(f"Failed to create streaming completion with {model_name}: {api_error}")
                    # Fallback to non-streaming once
                    try:
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            tools=tools_spec,
                            tool_choice="auto",
                            max_completion_tokens=min(2000, MAX_TOKENS_PER_TURN // 4),
                        )
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
                                    assistant_msg["content"] += piece_text
                                    full_content += piece_text
                                    any_text = True
                                    yield f"data: {json.dumps({'type': 'content', 'delta': piece_text})}\n\n"
                            elif isinstance(delta.content, str):
                                assistant_msg["content"] += delta.content
                                full_content += delta.content
                                any_text = True
                                yield f"data: {json.dumps({'type': 'content', 'delta': delta.content})}\n\n"

                        # Handle tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
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
                                    collected_tool_calls[idx]["function"]["name"] = tc.function.name
                                if getattr(tc, 'function', None) and getattr(tc.function, 'arguments', None):
                                    collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                except Exception as stream_error:
                    logger.error(f"Error processing stream chunks for model {model_name}: {stream_error}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Streaming error: {str(stream_error)}'})}\n\n"
                    return

                # If we have tool calls, execute them
                if collected_tool_calls:
                    assistant_msg["tool_calls"] = collected_tool_calls
                    messages.append(assistant_msg)

                    # Send tool call notification
                    yield f"data: {json.dumps({'type': 'tool_calls', 'tools': [tc['function']['name'] for tc in collected_tool_calls]})}\n\n"

                    # Execute tools and yield updates
                    tool_updates = _run_tools_sync(collected_tool_calls)
                    for update in tool_updates:
                        yield update

                    # Continue loop for next iteration
                    continue
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
                            tool_updates = _run_tools_sync(pseudo_calls)
                            for update in tool_updates:
                                yield update
                            # Continue loop to allow the model to use tool results
                            continue

                    # No tool calls; if no streamed text, fallback to single-shot completion
                    if not assistant_msg.get("content"):
                        try:
                            completion = client.chat.completions.create(
                                model=model_name,
                                messages=messages,
                                tools=tools_spec,
                                tool_choice="auto",
                                max_completion_tokens=min(2000, MAX_TOKENS_PER_TURN // 4),
                                temperature=0.7
                            )
                            choice = (completion.choices or [None])[0]
                            msg = getattr(choice, "message", None)
                            content = getattr(msg, "content", "") if msg else ""
                            if isinstance(content, list):
                                content = "".join(_normalize_content_piece(p) for p in content)
                            content = content or ""
                            if content:
                                assistant_msg["content"] = content
                                full_content += content
                                yield f"data: {json.dumps({'type': 'content', 'delta': content})}\n\n"
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

        # Store conversation with enhanced memory
        try:
            await store_conversation_messages_with_memory(conv_id, messages, str(user.id))

            db.add(Log(
                user_id=int(user.id),
                action="chat_stream",
                conversation_id=conv_id,
                prompt=req.prompt[:1000] if len(req.prompt) > 1000 else req.prompt,
                response=full_content[:2000] if len(full_content) > 2000 else full_content,
                tool_calls=tool_call_results,
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Database error in streaming: {e}")
            db.rollback()

        # Send completion
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'tool_calls': tool_call_results})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx proxy buffering if present
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

    # Use enhanced memory-aware message preparation
    messages, conv_id = await prepare_conversation_messages_with_memory(
        req.prompt, req.system_prompt, req.conversation_id or "", req.reset, str(user.id), model_key
    )

    try:
        client, model_name, _config = get_client_for_model(model_key)
        logger.info(f"Using model: {model_key} -> {model_name}")
    except Exception as e:
        logger.error(f"Failed to get client for model {model_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Model '{model_key}' is not available: {e}")

    tool_call_results: List[Dict[str, Any]] = []

    def _build_news_summary(result: Dict[str, Any]) -> Dict[str, Any]:
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

    def _run_tools(tc_list: List[Dict[str, Any]]):
        """Execute tool calls and append results to messages."""
        for tc in tc_list:
            try:
                if (tc.get("type") or "function") != "function":
                    continue
                
                fn = tc.get("function") or {}
                name = fn.get("name")
                raw_args = fn.get("arguments") or "{}"
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    args = {}
                
                impl = TOOL_REGISTRY.get(name)
                if not impl:
                    result = {"error": f"unknown tool: {name}"}
                else:
                    try:
                        result = impl(**(args or {}))
                        # Special handling: summarize augmented news to keep context small
                        if name == "get_augmented_news" and isinstance(result, dict):
                            result = _build_news_summary(result)
                        # Truncate large tool results to control costs (generic tools)
                        if isinstance(result, dict) and "items" in result and name != "get_augmented_news":
                            if len(result.get("items", [])) > 5:
                                result["items"] = result["items"][:5]
                                result["truncated"] = True
                    except Exception as e:
                        result = {"error": str(e)}

                # Truncate tool result content for token management
                result_str = json.dumps(result)
                if estimate_tokens(result_str) > 512:  # CHUNK_MAX_TOKENS equivalent
                    result_str = result_str[:2000] + "... [truncated]"

                # Append tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": result_str,
                })
                tool_call_results.append({"id": tc.get("id"), "name": name, "result": result})
            except Exception as e:
                tool_call_results.append({
                    "id": tc.get("id"), 
                    "name": (tc.get("function") or {}).get("name"), 
                    "error": str(e)
                })

    # Up to two rounds of tool calling then final answer
    final_content: Optional[str] = None
    for iteration in range(3):
        try:
            # Check token budget before each API call
            current_tokens = sum(estimate_tokens(json.dumps(m)) for m in messages)
            if current_tokens > MAX_TOKENS_PER_TURN * 0.9:  # 90% threshold
                logger.warning(f"Approaching token limit ({current_tokens}), truncating messages")
                # Keep essential messages
                essential_msgs = [m for m in messages if m.get("role") in {"system", "user"}]
                tool_msgs = [m for m in messages if m.get("role") == "tool"][ -3: ]  # Last 3 tool results
                messages = essential_msgs + tool_msgs

            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools_spec,
                tool_choice="auto",
                max_tokens=min(2000, MAX_TOKENS_PER_TURN // 4),  # Conservative response limit
                temperature=0.7
            )
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
            assistant_msg["tool_calls"] = tc
            messages.append(assistant_msg)
            _run_tools(tc)
            # Continue the loop to send tool outputs back to the model
            continue

        # Fallback: check for pseudo tool-calls embedded in text
        if assistant_msg.get("content"):
            pseudo_calls = _extract_pseudo_tool_calls(assistant_msg["content"]) or []
            if pseudo_calls:
                assistant_msg["content"] = _strip_pseudo_tool_markup(assistant_msg["content"]) or ""
                messages.append(assistant_msg)
                _run_tools(pseudo_calls)
                # Continue loop to send tool outputs back to the model
                continue

        # No tool calls; finalize
        final_content = assistant_msg.get("content") or ""
        if isinstance(final_content, list):
            final_content = "".join(
                (p.get("text") if isinstance(p, dict) and isinstance(p.get("text"), str) else str(p))
                for p in final_content
            )
        messages.append(assistant_msg)
        break
    # ...existing code...

    # Store conversation with enhanced memory
    await store_conversation_messages_with_memory(conv_id, messages, str(user.id))

    # Log action with cost tracking metadata
    try:
        db.add(Log(
            user_id=int(user.id),
            action="chat",
            conversation_id=conv_id,
            prompt=req.prompt[:1000] if len(req.prompt) > 1000 else req.prompt,
            response=final_content[:2000] if final_content and len(final_content) > 2000 else final_content,
            tool_calls=tool_call_results,
        ))
        db.commit()
    except Exception:
        db.rollback()

    return ChatResponse(
        content=final_content or "", 
        tool_calls=tool_call_results or None, 
        conversation_id=conv_id
    )

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
