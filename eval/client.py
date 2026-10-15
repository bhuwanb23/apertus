"""
client.py - One interface for every model, for every backend.

Responsibilities, in order of importance:
  1. Treat 8B and 70B identically. Nothing here branches on model size; the
     only difference between the two is the ModelConfig they were built with.
  2. Log the exact request parameters of every call, so "was temperature really 0"
     is answerable from the log file rather than from memory.
  3. Never lose a response. Raw text is written to disk before it is parsed.
  4. Be honest about failure. An error is recorded as an error, not silently
     scored as a wrong answer.

Backends
--------
openai : official OpenAI SDK (third-party dependency)
http   : stdlib urllib speaking the same OpenAI wire protocol (no dependency)
mock   : deterministic offline stand-in, for testing the harness itself

Run:  python eval/client.py            # connectivity + determinism self-check
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOGS_DIR, ModelConfig, config  # noqa: E402


# ------------------------------------------------------------------------ logging
def setup_logging(name: str = "eval", echo: bool = True) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOGS_DIR / f"{name}_{stamp}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    if echo:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    logger.propagate = False
    return logger


logger = setup_logging("eval")


# ---------------------------------------------------------------------- mock engine
_MOCK_LETTERS = ["A", "B", "C", "D"]
# Deterministic output shapes, so extract_answer() is exercised against the same
# variety of formats a real model produces, and the PARSE_ERROR branch is
# reachable in a test instead of being dead code.
_MOCK_SHAPES = [
    "{L}",                             # bare letter
    "{L}.",                            # letter + full stop
    "Answer: {L}",                # labelled
    "The answer is {L}.",              # phrased
    "{L}) ",                           # letter + option marker, trailing space
    "The correct answer is {L} because it is the only figure stated by an official Swiss source.",
    "Switzerland's rules differ here, so I would choose {L}.",
    "I'm not certain enough to pick one of the options from memory.",   # PARSE_ERROR
]


class MockBackend:
    """
    Deterministic offline stand-in.

    It derives its answer from a hash of (model_id, system, user) and never
    looks at the correct answer, so accuracy sits near chance. That is the
    point: it validates the pipeline without flattering it. Two identical calls
    always return identical text, which is what makes the determinism check in
    eval/smoke_test.py meaningful.
    """

    def __init__(self, model_config: ModelConfig):
        self.mc = model_config

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        blob = "\x00".join([self.mc.model_id, self.mc.backend, system_prompt, user_prompt])
        digest = hashlib.sha256(blob.encode("utf-8")).digest()

        if "required_present" in system_prompt:
            # A values-judge prompt. Returning an MCQ-shaped string here would
            # leave parse_judge_output() completely untested and would make the
            # values pipeline look broken rather than mocked.
            req_ids = re.findall(r"^\s+(R\d+):", user_prompt, re.M)
            forb_ids = re.findall(r"^\s+(F\d+):", user_prompt, re.M)
            n_req = len(req_ids)
            n_present = digest[0] % (n_req + 1)
            n_forbidden = digest[1] % 3 if forb_ids else 0
            present = sorted(req_ids)[:n_present]
            forbidden = sorted(forb_ids)[:n_forbidden]
            if forbidden:
                score = 0
            elif n_present == 0:
                score = 0
            elif n_present >= n_req - 1:
                score = 2
            else:
                score = 1
            text = json.dumps({
                "required_present": present,
                "forbidden_present": forbidden,
                "score": score,
                "reason": "mock judge: deterministic offline observation",
            })
        else:
            letter = _MOCK_LETTERS[digest[0] % 4]
            shape = _MOCK_SHAPES[digest[1] % len(_MOCK_SHAPES)]
            text = shape.format(L=letter)

        prompt_tokens = max(1, len(blob) // 4)
        return {
            "text": text,
            "finish_reason": "stop" if len(text) < max_tokens else "length",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": max(1, len(text) // 4),
            },
            "raw": None,
        }


# ------------------------------------------------------------------- http backend
class HttpBackend:
    """
    Stdlib urllib against an OpenAI-compatible /v1/chat/completions endpoint.

    Used for local llama.cpp / vLLM servers, where pulling in the SDK buys
    nothing. Identical wire format to the SDK backend.
    """

    def __init__(self, model_config: ModelConfig):
        self.mc = model_config
        if not self.mc.api_base:
            raise ValueError(f"{self.mc.name}: http backend requires api_base")
        self.endpoint = f"{self.mc.api_base}/chat/completions"

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.mc.model_id,
            "messages": messages,
            "temperature": self.mc.temperature,
            "top_p": self.mc.top_p,
            "max_tokens": max_tokens,
            "seed": self.mc.seed,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.mc.api_key}"} if self.mc.api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.mc.timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        choice = body["choices"][0]
        usage = body.get("usage") or {}
        msg = choice["message"] or {}
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()

        # Apertus v1.5 is a REASONING model: it emits a thinking block before the
        # answer, which llama-server surfaces as `reasoning_content`. Reading only
        # `content` is a live landmine - if max_tokens is consumed by the thinking
        # block, `content` comes back as an empty string and the whole evaluation
        # silently scores near zero. That failure is invisible, so it is handled
        # explicitly here rather than hoped away upstream.
        #
        # The reasoning trace is concatenated into `text` because the answer is
        # frequently referenced positionally ("as shown above, the answer is C"),
        # and dropping the trace would lose information the parser needs. Both
        # halves stay separately available for auditing.
        text = f"{reasoning}\n{content}".strip() if reasoning else content
        return {
            "text": text,
            "content": content,
            "reasoning": reasoning,
            "finish_reason": choice.get("finish_reason"),
            "spent_all_tokens_on_reasoning": bool(reasoning) and not content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", -1),
                "completion_tokens": usage.get("completion_tokens", -1),
            },
            "raw": body,
        }


# ------------------------------------------------------------------ openai backend
class OpenAIBackend:
    """Official OpenAI SDK. Lazily imported so the package is optional."""

    def __init__(self, model_config: ModelConfig):
        self.mc = model_config
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                f"{self.mc.name}: backend 'openai' needs the openai package "
                f"(pip install -r eval/requirements.txt), or use backend 'http'."
            ) from exc
        self._OpenAI = OpenAI
        self.client = OpenAI(
            base_url=self.mc.api_base,
            api_key=self.mc.api_key or "EMPTY",   # local servers often need a non-empty value
        )

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=self.mc.model_id,
            messages=messages,
            temperature=self.mc.temperature,
            top_p=self.mc.top_p,
            max_tokens=max_tokens,
            seed=self.mc.seed,
        )
        choice = response.choices[0]
        usage = response.usage
        return {
            "text": (choice.message.content or choice.message.reasoning_content or "").strip(),
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", -1),
                "completion_tokens": getattr(usage, "completion_tokens", -1),
            },
            "raw": response.model_dump() if hasattr(response, "model_dump") else None,
        }


BACKENDS = {"mock": MockBackend, "http": HttpBackend, "openai": OpenAIBackend}


# ------------------------------------------------------------------------- client
class ApertusClient:
    def __init__(self, model_config: ModelConfig):
        self.config = model_config
        if model_config.backend not in BACKENDS:
            raise ValueError(
                f"{model_config.name}: unknown backend {model_config.backend!r}; "
                f"expected one of {sorted(BACKENDS)}"
            )
        self.backend = BACKENDS[model_config.backend](model_config)
        self.call_count = 0

    # ---- the request parameters that must appear in the log for every call ----
    def request_params(self, max_tokens: Optional[int] = None) -> dict:
        return {
            "model": self.config.model_id,
            "backend": self.config.backend,
            "endpoint": getattr(self.backend, "endpoint", "(in-process)"),
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "seed": self.config.seed,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        One generation call with retries.

        Returns a dict that ALWAYS has 'text', 'ok' and 'provenance'. On
        failure it returns ok=False with the error text, and the caller decides
        what that means - it is never silently converted into a wrong answer.
        """
        params = self.request_params(max_tokens)
        logger.info(
            "REQ #%d %s | model=%s temp=%s top_p=%s seed=%s max_tokens=%s",
            self.call_count + 1, self.config.name, params["model"],
            params["temperature"], params["top_p"], params["seed"], params["max_tokens"],
        )

        result = None
        last_error = ""
        for attempt in range(config.retry_attempts):
            try:
                result = self.backend.generate(system_prompt, prompt, params["max_tokens"])
                last_error = ""
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            except Exception as exc:  # SDK errors, malformed responses
                last_error = f"{type(exc).__name__}: {exc}"

            logger.warning("attempt %d/%d failed: %s",
                           attempt + 1, config.retry_attempts, last_error)
            if attempt < config.retry_attempts - 1:
                time.sleep(config.retry_delay_seconds * (attempt + 1))

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if result is None:
            logger.error("all %d attempts failed for %s", config.retry_attempts, self.config.name)
            return {
                "text": "",
                "ok": False,
                "error": last_error,
                "attempt": config.retry_attempts,
                "usage": {},
                "finish_reason": None,
                "request_params": params,
                "provenance": self.provenance(),
                "timestamp": ts,
            }

        self.call_count += 1
        out = {
            "text": result["text"],
            "ok": True,
            "error": None,
            "attempt": attempt + 1,
            "usage": result.get("usage", {}),
            "finish_reason": result.get("finish_reason"),
            "request_params": params,
            "provenance": self.provenance(),
            "timestamp": ts,
        }
        logger.info(
            "RES #%d %s | ok | %s completion tokens | finish=%s | %r",
            self.call_count, self.config.name,
            result.get("usage", {}).get("completion_tokens", -1),
            result.get("finish_reason"), (result["text"][:80] + ("..." if len(result["text"]) > 80 else "")),
        )
        return out

    def provenance(self) -> dict:
        p = self.config.provenance()
        p["prompt_version"] = None   # filled by the caller, which knows the templates
        return p

    # ---------------------------------------------------------------- persistence
    def save_response(self, response: dict, item_id: str, eval_type: str,
                      out_dir: Optional[Path] = None, prompt_version: str = "") -> Path:
        """
        Write the raw response to disk BEFORE anything parses it. If parsing is
        wrong, the raw text is still there to re-score - which is what makes a
        later fix to extract_answer() cheap instead of requiring a full re-run.
        """
        base = Path(out_dir) if out_dir else config.results_dir / "raw_responses" / eval_type
        base.mkdir(parents=True, exist_ok=True)
        safe_id = str(item_id).replace("/", "_")
        payload = dict(response)
        if prompt_version:
            payload.setdefault("provenance", {})
            payload["provenance"] = {**payload.get("provenance", {}), "prompt_version": prompt_version}
        path = base / f"{safe_id}_{self.config.name}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


def get_client(model_name: str = "8b") -> ApertusClient:
    return ApertusClient(config.model(model_name))


# ------------------------------------------------------------------------ self-check
def smoke(client: ApertusClient) -> int:
    """
    Connectivity + determinism check. Prints the actual request parameters, so
    'temperature is 0' is verified against what was sent, not against the config.
    """
    mc = client.config
    print(f"\n--- client self-check: {mc.name} [{mc.backend}] ---")
    print(f"endpoint      : {client.request_params()['endpoint']}")
    print(f"model_id      : {mc.model_id}")
    print(f"temperature   : {mc.temperature}")
    print(f"top_p         : {mc.top_p}")
    print(f"seed          : {mc.seed}")
    print(f"max_tokens    : {mc.max_tokens}")
    if mc.is_mock:
        print("NOTE         : MOCK backend - this proves the harness, not the model.")

    probe = "In one sentence: what is the Swiss Federal Council?"
    r1 = client.generate(probe, system_prompt="You are a helpful assistant.")
    r2 = client.generate(probe, system_prompt="You are a helpful assistant.")

    ok = r1.get("ok", False)
    print(f"call 1 ok     : {ok}")
    if not ok:
        print(f"error         : {r1.get('error')}")
        return 1
    print(f"response      : {r1['text'][:200]}")
    print(f"determinism   : {'IDENTICAL' if r1['text'] == r2['text'] else 'DIFFERS'}")

    config.ensure_dirs()
    p = client.save_response(r1, "SELFCHECK", "smoke", prompt_version="1.0")
    print(f"saved         : {p} ({p.stat().st_size} bytes)")

    nonzero_temp = mc.temperature != 0.0
    if nonzero_temp:
        print(f"FAIL          : temperature is {mc.temperature}, must be 0.0")
        return 1
    print(f"temperature   : verified 0.0 in the request that produced this")
    return 0


if __name__ == "__main__":
    print(config.describe())
    targets = sys.argv[1:] or ["8b"]
    failures = 0
    for key in targets:
        failures += smoke(get_client(key))
    sys.exit(1 if failures else 0)