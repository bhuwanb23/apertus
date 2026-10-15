"""
config.py - Single source of truth for all evaluation settings.

Change NOTHING else when switching between 8B and 70B. Both models are
described by entries in MODELS; every other module refers to them by key.

Backends
--------
openai  Official OpenAI Python SDK. Needs the `openai` package.
        Use for CSCS / Phoenix / any hosted OpenAI-compatible endpoint.
http    Stdlib urllib against the same OpenAI wire protocol. No third-party
        dependency at all. Use for a local llama.cpp / vLLM server.
mock    Deterministic offline stand-in. NEVER produces a publishable number -
        every artefact it touches is stamped is_mock=true and every summary
        prints a banner. Exists so the harness itself can be tested before
        model access is set up, and so parser/scoring code has a regression
        test.

Model access is chosen entirely by environment variables - see eval/.env.example.

Run:  python -c "import sys; sys.path.insert(0,'eval'); import config; config.describe()"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- paths
EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = EVAL_DIR / "results"
RAW_RESPONSES_DIR = RESULTS_DIR / "raw_responses"
PARSED_DIR = RESULTS_DIR / "parsed"
SCORES_DIR = RESULTS_DIR / "scores"
LOGS_DIR = RESULTS_DIR / "logs"
PROMPTS_USED_PATH = RESULTS_DIR / "prompts_used.json"

ALL_DIRS = [RAW_RESPONSES_DIR, PARSED_DIR, SCORES_DIR, LOGS_DIR, RESULTS_DIR]


# --------------------------------------------------------------------- env loading
def load_dotenv(path: Optional[Path] = None) -> None:
    """
    Load .env into os.environ without overwriting real environment variables.

    Uses python-dotenv when installed, otherwise a small stdlib parser. The
    fallback exists so `mock` and `http` backends need zero third-party
    packages at all.
    """
    path = path or (EVAL_DIR / ".env")
    if not path.exists():
        return

    try:
        from dotenv import load_dotenv as _ld  # type: ignore

        _ld(path, override=False)
        return
    except ImportError:
        pass

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()


# ------------------------------------------------------------------ model definition
@dataclass
class ModelConfig:
    """Everything needed to talk to one model. Nothing about 8B vs 70B lives in code."""

    name: str                       # our key: "8b" / "70b"
    backend: str                    # "openai" | "http" | "mock"
    model_id: str                   # what the endpoint expects
    api_base: str = ""              # "" for mock
    api_key: str = ""
    max_tokens: int = 512
    timeout_seconds: int = 180
    # ---- FIXED EVALUATION CONDITIONS - do not change mid-project ----
    # Changing any of these invalidates comparison against baselines already run.
    temperature: float = 0.0
    top_p: float = 1.0
    seed: int = 42

    @property
    def is_mock(self) -> bool:
        return self.backend == "mock"

    def provenance(self) -> dict:
        """Recorded in every saved artefact so a number can always be traced back."""
        return {
            "model_key": self.name,
            "model_id": self.model_id,
            "backend": self.backend,
            "api_base": self.api_base,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "is_mock": self.is_mock,
        }


def _build(key: str, default_model_id: str, default_api_base: str = "") -> ModelConfig:
    """Assemble one ModelConfig from environment variables."""
    prefix = f"APERTUS_{key.upper()}"
    return ModelConfig(
        name=key,
        backend=os.getenv(f"{prefix}_BACKEND", "").strip().lower(),
        model_id=os.getenv(f"{prefix}_MODEL_ID", default_model_id).strip(),
        api_base=os.getenv(f"{prefix}_API_BASE", default_api_base).strip().rstrip("/"),
        api_key=os.getenv(f"{prefix}_API_KEY", "").strip(),
        max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", "512")),
        timeout_seconds=int(os.getenv(f"{prefix}_TIMEOUT", "180")),
    )


def _default_models() -> dict[str, ModelConfig]:
    """Build the model table fresh from the environment."""
    # Default is a TEXT-ONLY 4-bit extract. See eval/README.md for why:
    # swiss-ai/Apertus-v1.5-8B is the full Omni model (8.9 B params, ~19 GB
    # bf16 storage incl. vision + wav tokenizers) and does not fit an 8 GB
    # card. Every pillar of this benchmark is text, so the text-only extract
    # is the right instrument - but the substitution MUST be disclosed.
    #
    # Set APERTUS_8B_MODEL_ID in eval/.env to whatever your server actually
    # loaded. llama-server ignores the value for single-model servers, but it
    # is recorded in every artefact for provenance.
    return {
        "8b": _build("8b", "Apertus-v1.5-8B-text-Q4_K_M",
                     "http://127.0.0.1:8080/v1"),
        # No route arranged yet. When there is one:
        #   hosted endpoint -> BACKEND=openai, API_KEY=<key>
        #   local vLLM      -> BACKEND=http,   API_KEY=EMPTY
        # With nothing set this resolves to `mock`, which stamps every artefact
        # and prints a banner. That is intentional: an absent model must be
        # visible, never silently absent.
        "70b": _build("70b", "swiss-ai/Apertus-v1.5-70B"),
    }


class EvalConfig:
    """Project-wide settings. Everything is overridable by environment variable."""

    MODELS: dict[str, ModelConfig] = _default_models()

    def __init__(self) -> None:
        # Build per instance rather than sharing the class-level dict.
        #
        # Two reasons, and the second is the one that bit us:
        #  1. _resolve_backends() MUTATES the ModelConfig objects. If two
        #     instances shared them, resolving one would leak into the other.
        #  2. An unconfigured model must be resolved to `mock` so that it is
        #     visibly fake. This class previously relied on __post_init__ to do
        #     that, but it is not a dataclass, so __post_init__ was never
        #     called: backend stayed as the empty string, which is not a valid
        #     backend AND is not `mock` - so `is_mock` was False for a model
        #     that could not possibly answer anything. A missing model looked
        #     like a live one.
        self.MODELS = _default_models()
        self._resolve_backends()

    # ---------------------------------------------------------------- dataset
    data_dir: Path = DATA_DIR
    knowledge_split: str = "dev"     # "dev" during development; "test" ONLY in Phase 4.1
    dialect_dir: Path = DATA_DIR / "dialect"

    # Named prompt variant, not a free-text override. Changing this mid-project
    # invalidates comparison against earlier runs, so it is recorded in every
    # artefact. See prompts.py KNOWLEDGE_SYSTEM_VARIANTS for the escalation
    # order used when the parse error rate exceeds 10%.
    knowledge_prompt_variant: str = os.getenv("EVAL_KNOWLEDGE_VARIANT", "v1_letter_only")

    # ---------------------------------------------------------------- runtime
    batch_size: int = 10
    retry_attempts: int = int(os.getenv("EVAL_RETRY_ATTEMPTS", "3"))
    retry_delay_seconds: int = int(os.getenv("EVAL_RETRY_DELAY", "5"))
    request_delay_seconds: float = float(os.getenv("EVAL_REQUEST_DELAY", "0.5"))
    smoke_test_size: int = 5

    # ---------------------------------------------------------------- judging
    judge_model: str = "70b"
    manual_audit_fraction: float = 0.2

    # ------------------------------------------------------------- versioning
    prompt_version: str = "1.0"
    run_id: str = ""

    # ------------------------------------------------------------------ paths
    results_dir: Path = RESULTS_DIR
    prompts_dir: Path = RESULTS_DIR
    logs_dir: Path = LOGS_DIR


    # ------------------------------------------------------------------ helpers
    def _resolve_backends(self) -> None:
        """
        Decide each model's backend.

        An unconfigured live endpoint silently degrading to `mock` is the one
        failure mode that could corrupt the whole benchmark, because it produces
        plausible-looking numbers. So the fallback exists but is LOUD: it is
        recorded in every artefact and reported in describe().
        """
        for key, m in self.MODELS.items():
            if m.backend:
                continue
            if m.api_base:
                # A base URL was supplied but no backend named. stdlib http has
                # no install cost and speaks the same wire protocol.
                m.backend = "http"
            else:
                m.backend = "mock"

    def model(self, key: str) -> ModelConfig:
        if key not in self.MODELS:
            raise ValueError(f"unknown model key {key!r}; have {sorted(self.MODELS)}")
        return self.MODELS[key]

    def validate(self) -> list[str]:
        """Startup self-check. Returns a list of problems; empty means fine."""
        problems = []
        for key, m in self.MODELS.items():
            if m.temperature != 0.0:
                problems.append(f"{key}: temperature is {m.temperature}, must be 0.0 "
                                f"- changing it invalidates existing baselines")
            if m.backend not in {"mock", "http", "openai"}:
                problems.append(f"{key}: unknown backend {m.backend!r}")
            if m.backend == "openai" and not m.api_base:
                problems.append(f"{key}: openai backend with no api_base")
        return problems

    def ensure_dirs(self) -> None:
        for d in ALL_DIRS:
            d.mkdir(parents=True, exist_ok=True)

    def data_path(self, *parts: str) -> Path:
        return self.data_dir.joinpath(*parts)

    def live_models(self) -> list[str]:
        return [k for k, m in self.MODELS.items() if not m.is_mock]

    def any_mock(self) -> bool:
        return any(m.is_mock for m in self.MODELS.values())

    # ------------------------------------------------------------------ reporting
    def describe(self) -> str:
        lines = [
            "=" * 72,
            "EVAL CONFIG",
            "=" * 72,
            f"data_dir      : {self.data_dir}",
            f"results_dir   : {self.results_dir}",
            f"split         : {self.knowledge_split}",
            f"temperature   : {next(iter(self.MODELS.values())).temperature}  (FIXED)",
            f"judge_model   : {self.judge_model}",
            "",
        ]
        for key, m in self.MODELS.items():
            flag = "  <-- MOCK, NOT A RESULT" if m.is_mock else ""
            lines += [
                f"[{key}]",
                f"  backend    : {m.backend}{flag}",
                f"  model_id   : {m.model_id}",
                f"  api_base   : {m.api_base or '(none)'}",
                f"  api_key    : {'set' if m.api_key else '(none)'}",
                f"  temp/top_p : {m.temperature} / {m.top_p}   seed {m.seed}",
                f"  max_tokens : {m.max_tokens}",
                "",
            ]
        if self.any_mock():
            lines += [
                "*" * 72,
                "* AT LEAST ONE MODEL IS MOCKED.",
                "* Numbers produced with it are pipeline self-tests only.",
                "* They MUST NOT appear in the README, charts or submission.",
                "* Set APERTUS_<KEY>_BACKEND and APERTUS_<KEY>_API_BASE to go live.",
                "*" * 72,
            ]
        lines.append("=" * 72)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = {
            "knowledge_split": self.knowledge_split,
            "judge_model": self.judge_model,
            "manual_audit_fraction": self.manual_audit_fraction,
            "retry_attempts": self.retry_attempts,
            "request_delay_seconds": self.request_delay_seconds,
            "models": {k: asdict(v) for k, v in self.MODELS.items()},
        }
        return d


config = EvalConfig()