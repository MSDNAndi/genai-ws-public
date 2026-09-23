# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""A tiny offline OpenAI-compatible server.

Not a model - it echoes deterministic canned answers. It exists so that every
sample in this repo can be smoke-tested without a key, and so that a broken
conference Wi-Fi does not end the lab.

    uv run tools/mock_server.py            # http://localhost:8080/v1
    GENAI_PROFILE=mock uv run samples/.../01_hello_model.py
"""

from __future__ import annotations

import base64
import io
import json
import math
import re
import struct
import sys
import time
import wave
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _png(width: int, height: int, grey: int = 160) -> bytes:
    """A valid grey PNG from the standard library (no Pillow on the mock)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + bytes([grey]) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def _wav_tone(seconds: float, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * i / rate)))
                               for i in range(int(seconds * rate))))
    return buf.getvalue()

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
MODEL = "mock-model-1"


def _from_schema(schema: dict, defs: dict | None = None) -> object:
    """Build a dummy value that satisfies a JSON schema - enough for structured-output demos."""
    defs = defs if defs is not None else schema.get("$defs", {})
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return _from_schema(defs.get(name, {}), defs)
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object":
        props = schema.get("properties", {})
        return {k: _from_schema(v, defs) for k, v in props.items()}
    if t == "array":
        return [_from_schema(schema.get("items", {"type": "string"}), defs)]
    if t == "integer":
        return 42
    if t == "number":
        return 4.2
    if t == "boolean":
        return True
    return "mock"


_TEXT_PARAMS = {"task", "query", "question", "input", "request", "text", "prompt", "message"}


def _text(content) -> str:
    if isinstance(content, list):  # content blocks (vision etc.)
        return " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _speaker(messages: list[dict]) -> str:
    """First words of the system prompt, so multi-agent output shows who answered."""
    for m in messages:
        if m.get("role") in ("system", "developer"):
            words = _text(m.get("content")).split()
            if words:
                return " ".join(words[:5])
    return ""


def _tool_call(index: int, fn: dict, user_text: str) -> dict:
    props = list((fn.get("parameters") or {}).get("properties", {}))
    # Free-text parameters get the user's words, so a delegated sub-agent
    # receives a real task; everything else gets a recognisable placeholder.
    args = {p: (user_text if p.lower() in _TEXT_PARAMS else f"value-for-{p}") for p in props}
    return {"id": f"call_mock_{index}", "type": "function",
            "function": {"name": fn["name"], "arguments": json.dumps(args)}}


_STOP = {"the", "and", "for", "you", "your", "are", "what", "how", "any", "use", "with",
         "this", "that", "from", "one", "all", "into", "about", "there", "then", "can"}


def _words(text: str) -> set[str]:
    words = {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3 and w not in _STOP}
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}  # invoices ~ invoice


def _relevance(fn: dict, user_text: str) -> int:
    """How well a tool matches the question - a crude stand-in for model judgement."""
    name = fn["name"].removeprefix("handoff_to_")
    return len(_words(user_text) & (_words(name.replace("_", " ")) | _words(fn.get("description") or "")))


def _pick_handoff(handoffs: list[dict], user_text: str) -> dict:
    """Route like a triage agent would: the target whose name or description best matches."""
    return max(handoffs, key=lambda fn: _relevance(fn, user_text))


def _answer(messages: list[dict], tools: list | None, response_format: dict | None = None) -> dict:
    user_index = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=-1)
    last = _text(messages[user_index].get("content")) if user_index >= 0 else ""
    who = _speaker(messages)
    # The message count makes memory visible: a session replays its history,
    # so the same question arrives with more context.
    context = f"{len(messages)} msg{'s' if len(messages) != 1 else ''} in context"
    tag = f"[mock | {who} | {context}]" if who else f"[mock | {context}]"

    if response_format and response_format.get("type") == "json_schema":
        schema = response_format["json_schema"].get("schema", {})
        return {"role": "assistant", "content": json.dumps(_from_schema(schema))}

    # Once tool results came back for this user turn, answer in prose -
    # otherwise the loop never ends.
    results = [_text(m.get("content")) for m in messages[user_index + 1:] if m.get("role") == "tool"]
    if results:
        return {"role": "assistant",
                "content": f"{tag} Based on {len(results)} tool result(s): {' | '.join(results)[:300]}"}

    # Tools on offer and none used yet this turn: use them, like a model would.
    if tools:
        functions = [t["function"] for t in tools if t.get("type") == "function"]
        handoffs = [f for f in functions if f["name"].startswith("handoff_to_")]
        if handoffs:  # handoff = route to the best match, but only if something matches;
            best = _pick_handoff(handoffs, last)  # a specialist should not bounce in-scope work
            calls = [_tool_call(1, best, last)] if _relevance(best, last) > 0 else []
        else:         # ordinary tools = call every relevant one, in parallel (up to 3)
            relevant = [fn for fn in functions if _relevance(fn, last) > 0][:3]
            calls = [_tool_call(i, fn, last) for i, fn in enumerate(relevant, start=1)]
        if calls:
            return {"role": "assistant", "content": None, "tool_calls": calls}

    return {"role": "assistant", "content": f"{tag} You said: {last[:200]}"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter console
        sys.stderr.write(f"  mock {self.path} {fmt % args}\n")

    def _send(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self, message: dict, model: str, include_usage: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(delta: dict, finish: str | None = None, usage: dict | None = None) -> None:
            chunk = {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [] if usage else [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            if usage:
                chunk["usage"] = usage
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()

        if message.get("tool_calls"):
            # Streamed tool calls arrive as indexed fragments, exactly like the real API.
            for index, call in enumerate(message["tool_calls"]):
                emit({"role": "assistant", "tool_calls": [{**call, "index": index}]})
            emit({}, "tool_calls")
        else:
            for word in (message.get("content") or "").split(" "):
                emit({"content": word + " "})
            emit({}, "stop")
        if include_usage:
            emit({}, usage={"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def do_GET(self) -> None:
        if self.path.endswith("/models"):
            self._send({"object": "list", "data": [{"id": MODEL, "object": "model"}]})
        else:
            self._send({"error": {"message": f"no route {self.path}"}}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        model = req.get("model", MODEL)

        if self.path.endswith("/embeddings"):
            inputs = req.get("input")
            inputs = [inputs] if isinstance(inputs, str) else inputs
            data = []
            for i, text in enumerate(inputs):
                # Deterministic pseudo-embedding: stable per text, 16 dims.
                seed = sum(ord(c) * (j + 1) for j, c in enumerate(str(text)))
                vec = [((seed >> k) % 1000) / 1000.0 for k in range(16)]
                data.append({"object": "embedding", "index": i, "embedding": vec})
            self._send({"object": "list", "data": data, "model": model,
                        "usage": {"prompt_tokens": 8, "total_tokens": 8}})
            return

        if self.path.endswith("/chat/completions"):
            message = _answer(req.get("messages", []), req.get("tools"), req.get("response_format"))
            if req.get("stream"):
                include_usage = bool((req.get("stream_options") or {}).get("include_usage"))
                self._send_stream(message, model, include_usage)
                return
            self._send({
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                }],
                "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
            })
            return

        if self.path.endswith("/images/generations"):
            # A flat grey square - enough for the image samples to decode, save and show a file.
            n = int(req.get("n") or 1)
            self._send({"created": int(time.time()),
                        "data": [{"b64_json": base64.b64encode(_png(64, 64)).decode()} for _ in range(n)]})
            return

        if self.path.endswith("/audio/speech"):
            # One second of a quiet 440 Hz tone: a real WAV file, so players and file checks work.
            body = _wav_tone(1.0)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.endswith("/responses"):
            text = str(req.get("input", ""))
            self._send({
                "id": "resp_mock",
                "object": "response",
                "model": model,
                "status": "completed",
                "output": [{
                    "type": "message", "id": "msg_mock", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": f"[mock] You said: {text[:200]}",
                                 "annotations": []}],
                }],
                "usage": {"input_tokens": 42, "output_tokens": 17, "total_tokens": 59},
            })
            return

        self._send({"error": {"message": f"no route {self.path}"}}, 404)


if __name__ == "__main__":
    print(f"mock OpenAI-compatible endpoint on http://localhost:{PORT}/v1  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
