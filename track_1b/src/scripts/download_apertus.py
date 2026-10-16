"""
Download the OFFICIAL Apertus v1.5 8B weights from swiss-ai on Hugging Face.

Provenance rule for this project: only the official repository is used.
No third-party conversion, no third-party quantisation. We download
swiss-ai/Apertus-v1.5-8B and then do the GGUF conversion and Q4_K_M
quantisation ourselves with pinned tooling, so the chain is:

    swiss-ai/Apertus-v1.5-8B  ->  our BF16 GGUF  ->  our Q4_K_M GGUF

The repo is GATED: it requires an HF account, acceptance of the Apache 2.0
licence and the Apertus 1.5 Acceptable Use Policy, and a token issued to an
account that has accepted. This script does none of that - it only reads an
already-issued read token.

The token is read from HF_READ_TOKEN in .env and is never printed, logged or
written to any artefact.

Run:  python scripts/download_apertus.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ID = "swiss-ai/Apertus-v1.5-8B"
LOCAL_DIR = ROOT / "models" / "Apertus-v1.5-8B"


def read_token() -> str:
    """Read HF_READ_TOKEN from .env without ever echoing it."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        sys.exit(f"[FATAL] {env_path} not found - cannot read HF_READ_TOKEN")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "HF_READ_TOKEN":
            tok = value.strip().strip('"').strip("'")
            if tok:
                # length only - never the value
                print(f"[ok] HF_READ_TOKEN found ({len(tok)} chars)")
                return tok
    sys.exit("[FATAL] HF_READ_TOKEN not present in .env")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="check access, download nothing")
    args = ap.parse_args()

    token = read_token()
    os.environ["HF_TOKEN"] = token

    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError:
        sys.exit("[FATAL] huggingface_hub not installed - pip install huggingface_hub")

    api = HfApi(token=token)

    print(f"\n[1/3] Checking gated access to {REPO_ID}")
    try:
        info = api.model_info(REPO_ID, files_metadata=True)
    except Exception as exc:
        print(f"[FATAL] Could not read repo metadata: {exc}")
        print("       If this is a 401/403, either the licence has not been accepted")
        print("       on the account owning this token, or the token lacks the read")
        print("       scope, or the token is not valid for gated repos.")
        return 1

    total = 0
    print(f"\n[2/3] Files in repo ({len(info.siblings)}):")
    for sib in sorted(info.siblings, key=lambda s: s.rfilename):
        size = getattr(sib, "size", None) or 0
        total += size
        if size:
            print(f"      {size / 1e9:7.2f} GB  {sib.rfilename}")
        else:
            print(f"              --  {sib.rfilename}")
    print(f"\n      TOTAL {total / 1e9:.2f} GB")

    if args.dry_run:
        print("\n[3/3] --dry-run: stopping before download.")
        return 0

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[3/3] Downloading to {LOCAL_DIR}")
    print("      (large: ~18 GB. Expect 20-90 min depending on bandwidth.)")

    t0 = time.time()
    path = snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(LOCAL_DIR),
        token=token,
        max_workers=4,
        resume_download=True,
    )
    dt = time.time() - t0

    print(f"\n[done] {path}")
    print(f"[done] {dt / 60:.1f} min elapsed")

    # Verify the four model shards are present and non-empty before anyone
    # spends an hour converting them.
    shards = sorted(LOCAL_DIR.glob("model-apertus-model-*.safetensors"))
    if len(shards) != 4:
        print(f"[WARN] expected 4 model shards, found {len(shards)}")
    for s in shards:
        mb = s.stat().st_size / 1e6
        flag = "" if mb > 1000 else "  <-- SUSPICIOUSLY SMALL"
        print(f"       {mb:8.0f} MB  {s.name}{flag}")

    for needed in ("config.json", "tokenizer.json", "chat_template.jinja"):
        if not (LOCAL_DIR / needed).exists():
            print(f"[WARN] missing {needed} - the GGUF conversion will likely fail")
    return 0


if __name__ == "__main__":
    sys.exit(main())