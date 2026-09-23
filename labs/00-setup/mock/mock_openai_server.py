#!/usr/bin/env python3
"""mock_openai_server.py - an OpenAI-compatible stand-in (stdlib only) for when the network, the key or the budget fails.

    python mock_openai_server.py 8123                         # then GENAI_BASE_URL=http://127.0.0.1:8123/v1
    MOCK_REQUIRE_API_KEY=test python mock_openai_server.py    # behave like the gateway: 401 without "api-key: test"
    MOCK_LOG=requests.jsonl python mock_openai_server.py      # log every request body: see what a framework really sends
    MOCK_HOST=0.0.0.0 python mock_openai_server.py            # serve the whole room: GENAI_BASE_URL=http://<your-ip>:8123/v1

Every lab script keeps running against it; answers are echoes, not intelligence. What it emulates:
  GET  /v1/models
  POST /v1/chat/completions  non-streaming + SSE; tools -> a call to the FIRST declared tool (arguments built from its
                             JSON schema: strings "Paris", integers 3), then after a tool result a final text answer;
                             response_format json_schema / json_object honoured
  POST /v1/responses         non-streaming + SSE (text and function_call items, function_call_output round-trip)
  POST /v1/embeddings        256-dim hashed bag-of-words vectors: similar wording -> similar vectors, so retrieval
                             in Lab 2 still finds lexically matching chunks offline
  POST /v1/images/generations  a small solid-colour PNG (b64_json)
  POST /v1/audio/speech      a short WAV beep
"""
import base64
import io
import json
import math
import os
import re
import struct
import sys
import time
import uuid
import wave
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
REQUIRE_KEY = os.environ.get("MOCK_REQUIRE_API_KEY")
LOG_FILE = os.environ.get("MOCK_LOG")    # MOCK_LOG=requests.jsonl -> every request body is appended (see what frameworks send)
DIMS = 256


def fake_args(schema):
    """Plausible arguments for a JSON schema: required (or all) properties get a placeholder of the right type."""
    schema = schema or {}
    props = schema.get("properties") or {}
    keys = schema.get("required") or list(props.keys())
    out = {}
    for k in keys:
        t = (props.get(k) or {}).get("type", "string")
        if isinstance(t, list):  # e.g. ["string", "null"] (MAF .NET handoff tools)
            t = next((x for x in t if x != "null"), "string")
        out[k] = {"integer": 3, "number": 3.0, "boolean": True, "array": [], "object": {}}.get(t, "Paris")
    return out or {"city": "Paris"}


def text_of(content):
    if isinstance(content, list):
        return " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content or "")


def embed(text: str) -> list[float]:
    v = [0.0] * DIMS
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        h = zlib.crc32(word.encode())
        v[h % DIMS] += 1.0 if (h >> 16) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def chat_response(body):
    msgs, tools, model = body.get("messages", []), body.get("tools") or [], body.get("model", "mock")
    has_tool_result = any(m.get("role") == "tool" for m in msgs)
    if tools and not has_tool_result:
        fn = tools[0].get("function", tools[0])
        msg = {"role": "assistant", "content": None,
               "tool_calls": [{"id": "call_" + uuid.uuid4().hex[:8], "type": "function",
                               "function": {"name": fn.get("name", "tool"), "arguments": json.dumps(fake_args(fn.get("parameters")))}}]}
        finish = "tool_calls"
    else:
        last_user = text_of(next((m.get("content") for m in reversed(msgs) if m.get("role") == "user"), ""))
        tool_txt = next((m.get("content") for m in reversed(msgs) if m.get("role") == "tool"), None)
        text = f"[mock:{model}] answer to '{last_user[:60]}'" + (f" using tool result '{str(tool_txt)[:40]}'" if tool_txt else "")
        rf = body.get("response_format") or {}
        if rf.get("type") == "json_schema":
            text = json.dumps(fake_args((rf.get("json_schema") or {}).get("schema")))
        elif rf.get("type") == "json_object":
            text = json.dumps({"answer": text})
        msg, finish = {"role": "assistant", "content": text}, "stop"
    return {"id": "chatcmpl-" + uuid.uuid4().hex[:12], "object": "chat.completion", "created": int(time.time()), "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49}}


def chat_stream(resp):
    msg = resp["choices"][0]["message"]
    base = {"id": resp["id"], "object": "chat.completion.chunk", "created": resp["created"], "model": resp["model"]}
    if msg.get("tool_calls"):
        tc = msg["tool_calls"][0]
        yield {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": tc["id"], "type": "function", "function": {"name": tc["function"]["name"], "arguments": ""}}]}, "finish_reason": None}]}
        yield {**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": tc["function"]["arguments"]}}]}, "finish_reason": None}]}
        yield {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
    else:
        yield {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]}
        for word in msg["content"].split(" "):
            yield {**base, "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}]}
        yield {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}], "usage": resp["usage"]}


def responses_response(body):
    inp, tools = body.get("input", ""), body.get("tools") or []
    items = inp if isinstance(inp, list) else [{"type": "message", "role": "user", "content": inp}]
    has_fc_out = any(isinstance(i, dict) and i.get("type") == "function_call_output" for i in items)
    fn_tools = [t for t in tools if t.get("type") == "function"]
    base = {"id": "resp_" + uuid.uuid4().hex[:8], "object": "response", "created_at": int(time.time()),
            "model": body.get("model", "mock"), "status": "completed", "error": None, "incomplete_details": None,
            "instructions": body.get("instructions"), "metadata": {}, "parallel_tool_calls": True, "tool_choice": "auto",
            "tools": tools, "temperature": 1.0, "top_p": 1.0, "previous_response_id": body.get("previous_response_id")}
    if fn_tools and not has_fc_out:
        out = [{"type": "function_call", "id": "fc_" + uuid.uuid4().hex[:8], "call_id": "call_" + uuid.uuid4().hex[:8],
                "name": fn_tools[0]["name"], "arguments": json.dumps(fake_args(fn_tools[0].get("parameters"))), "status": "completed"}]
    else:
        last_user = next((text_of(i.get("content")) for i in reversed(items) if isinstance(i, dict) and i.get("role") == "user"), "")
        fc_out = next((i.get("output") for i in reversed(items) if isinstance(i, dict) and i.get("type") == "function_call_output"), None)
        text = f"[mock-responses:{base['model']}] answer to '{last_user[:60]}'" + (f" using tool result '{str(fc_out)[:40]}'" if fc_out else "")
        fmt = (body.get("text") or {}).get("format") or {}
        if fmt.get("type") == "json_schema":
            text = json.dumps(fake_args(fmt.get("schema")))
        out = [{"type": "message", "id": "msg_" + uuid.uuid4().hex[:8], "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": [], "logprobs": []}]}]
    return {**base, "output": out, "usage": {"input_tokens": 40, "output_tokens": 8, "total_tokens": 48,
                                             "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}


def responses_stream(resp):
    seq = iter(range(10_000))
    started = {**resp, "status": "in_progress", "output": []}
    yield "response.created", {"type": "response.created", "sequence_number": next(seq), "response": started}
    yield "response.in_progress", {"type": "response.in_progress", "sequence_number": next(seq), "response": started}
    for oi, item in enumerate(resp["output"]):
        if item["type"] == "message":
            text = item["content"][0]["text"]
            yield "response.output_item.added", {"type": "response.output_item.added", "sequence_number": next(seq), "output_index": oi,
                                                 "item": {**item, "status": "in_progress", "content": []}}
            part = {"type": "output_text", "text": "", "annotations": [], "logprobs": []}
            yield "response.content_part.added", {"type": "response.content_part.added", "sequence_number": next(seq), "item_id": item["id"],
                                                  "output_index": oi, "content_index": 0, "part": part}
            for word in text.split(" "):
                yield "response.output_text.delta", {"type": "response.output_text.delta", "sequence_number": next(seq), "item_id": item["id"],
                                                     "output_index": oi, "content_index": 0, "delta": word + " ", "logprobs": []}
            yield "response.output_text.done", {"type": "response.output_text.done", "sequence_number": next(seq), "item_id": item["id"],
                                                "output_index": oi, "content_index": 0, "text": text, "logprobs": []}
            yield "response.content_part.done", {"type": "response.content_part.done", "sequence_number": next(seq), "item_id": item["id"],
                                                 "output_index": oi, "content_index": 0, "part": {**part, "text": text}}
        else:
            yield "response.output_item.added", {"type": "response.output_item.added", "sequence_number": next(seq), "output_index": oi,
                                                 "item": {**item, "arguments": "", "status": "in_progress"}}
            yield "response.function_call_arguments.delta", {"type": "response.function_call_arguments.delta", "sequence_number": next(seq),
                                                             "item_id": item["id"], "output_index": oi, "delta": item["arguments"]}
            yield "response.function_call_arguments.done", {"type": "response.function_call_arguments.done", "sequence_number": next(seq),
                                                            "item_id": item["id"], "output_index": oi, "arguments": item["arguments"]}
        yield "response.output_item.done", {"type": "response.output_item.done", "sequence_number": next(seq), "output_index": oi, "item": item}
    yield "response.completed", {"type": "response.completed", "sequence_number": next(seq), "response": resp}


def png(w: int, h: int, rgb: tuple) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def wav_beep(seconds=0.4, hz=660, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * hz * i / rate))) for i in range(int(seconds * rate))))
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, code, obj=None, raw: bytes | None = None, ctype="application/json"):
        data = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _sse(self, events):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("connection", "close")
        self.end_headers()
        for name, payload in events:
            prefix = f"event: {name}\n" if name else ""
            self.wfile.write(f"{prefix}data: {json.dumps(payload)}\n\n".encode())
        self.close_connection = True

    def do_GET(self):
        if self.path.split("?")[0].rstrip("/").endswith("/models"):
            return self._send(200, {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "mock"}
                                                               for m in ("mock-model", "mock-embed", "mock-image", "mock-tts")]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        raw_body = self.rfile.read(n) if n else b""
        if REQUIRE_KEY and self.headers.get("api-key") != REQUIRE_KEY:
            return self._send(401, {"statusCode": 401, "message": "Access denied due to missing subscription key. "
                                    "Make sure to include subscription key when making requests to an API."})
        body = json.loads(raw_body or b"{}")
        path = self.path.split("?")[0]
        if LOG_FILE:
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"path": path, "body": body}) + "\n")
        if path.endswith("/chat/completions"):
            resp = chat_response(body)
            if body.get("stream"):
                return self._chat_sse(resp)
            return self._send(200, resp)
        if path.endswith("/responses"):
            resp = responses_response(body)
            return self._sse(responses_stream(resp)) if body.get("stream") else self._send(200, resp)
        if path.endswith("/embeddings"):
            inp = body.get("input")
            inp = inp if isinstance(inp, list) else [inp]
            vectors = [embed(t if isinstance(t, str) else " ".join(map(str, t))) for t in inp]
            if body.get("encoding_format") == "base64":
                data = [{"object": "embedding", "index": i, "embedding": base64.b64encode(struct.pack(f"<{DIMS}f", *v)).decode()} for i, v in enumerate(vectors)]
            else:
                data = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vectors)]
            return self._send(200, {"object": "list", "model": body.get("model", "mock-embed"), "data": data,
                                    "usage": {"prompt_tokens": 5 * len(inp), "total_tokens": 5 * len(inp)}})
        if path.endswith("/images/generations"):
            h = zlib.crc32(str(body.get("prompt", "")).encode())
            img = base64.b64encode(png(64, 64, (h & 255, (h >> 8) & 255, (h >> 16) & 255))).decode()
            return self._send(200, {"created": int(time.time()), "data": [{"b64_json": img} for _ in range(int(body.get("n", 1)))]})
        if path.endswith("/audio/speech"):
            return self._send(200, raw=wav_beep(), ctype="audio/wav")
        self._send(404, {"error": f"no route {path}"})

    def _chat_sse(self, resp):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("connection", "close")
        self.end_headers()
        for c in chat_stream(resp):
            self.wfile.write(f"data: {json.dumps(c)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.close_connection = True


if __name__ == "__main__":
    HOST = os.getenv("MOCK_HOST", "127.0.0.1")   # 0.0.0.0 = reachable from other laptops in the room
    print(f"mock OpenAI-compatible server on http://{HOST}:{PORT}/v1"
          + (f" (requires api-key: {REQUIRE_KEY})" if REQUIRE_KEY else ""), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
