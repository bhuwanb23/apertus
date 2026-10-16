"""
Wire-format check for the http backend.

Starts a throwaway OpenAI-compatible server in-process, points eval's http
backend at it, and prints the exact JSON payload the client sent. This is the
check that has to pass before pointing it at llama-server, because a silently
wrong temperature or a missing `seed` would invalidate every number in the
project and nothing downstream would notice.

Run:  python eval/check_http_backend.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CAPTURED: list = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode("utf-8"))
        CAPTURED.append({
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
            "content_type": self.headers.get("Content-Type"),
            "payload": body,
        })
        resp = {
            "id": "stub", "object": "chat.completion", "model": body.get("model"),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "B"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
        }
        raw = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def main() -> int:
    port = 8098
    srv = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    os.environ["APERTUS_8B_BACKEND"] = "http"
    os.environ["APERTUS_8B_API_BASE"] = f"http://127.0.0.1:{port}/v1"
    os.environ["APERTUS_8B_API_KEY"] = "EMPTY"
    os.environ["APERTUS_8B_MODEL_ID"] = "stub-model"

    import importlib

    import config as config_mod
    importlib.reload(config_mod)
    from client import ApertusClient

    client = ApertusClient(config_mod.config.model("8b"))
    print(f"backend resolved: {client.config.backend} -> {client.request_params()['endpoint']}")

    from run_knowledge import build_prompt, extract_answer, load_questions

    q = load_questions("dev", limit=1)[0]
    system, prompt = build_prompt(q)
    r = client.generate(prompt, system_prompt=system)

    srv.shutdown()

    ok = True
    if not CAPTURED:
        print("FAIL: server captured no request")
        return 1
    cap = CAPTURED[-1]
    p = cap["payload"]

    print("\n--- what the server received ---")
    print(f"  POST path       : {cap['path']}")
    print(f"  Authorization   : {cap['authorization']}")
    print(f"  Content-Type    : {cap['content_type']}")
    print(f"  payload keys    : {sorted(p)}")
    for k in ("model", "temperature", "top_p", "seed", "max_tokens"):
        print(f"  {k:15} : {p.get(k)!r}")
    print("  messages        :")
    for m in p["messages"]:
        preview = m["content"][:72].replace("\n", " / ")
        print(f"      {m['role']:6} -> {preview!r}")

    checks = [
        ("POSTs to /chat/completions", cap["path"].endswith("/chat/completions")),
        ("sends temperature=0.0", p.get("temperature") == 0.0),
        ("sends seed", p.get("seed") is not None),
        ("sends max_tokens", isinstance(p.get("max_tokens"), int)),
        ("sends exactly 2 messages", len(p.get("messages", [])) == 2),
        ("first message is system", p["messages"][0]["role"] == "system"),
        ("second message is user", p["messages"][1]["role"] == "user"),
        ("bearer auth header sent", (cap["authorization"] or "").startswith("Bearer ")),
        ("no placeholder left in prompt", "{question}" not in p["messages"][1]["content"]),
        ("response parsed to a letter", extract_answer(r["text"]) == "B"),
    ]

    print("\n--- checks ---")
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL':4}] {name}")
        ok = ok and passed

    print("\nHTTP BACKEND " + ("OK - wire format matches OpenAI /v1 spec." if ok else "BROKEN."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())