"""
canonical_dialect.py - the dialect label mapping, in one place.

Three defects in `data/dialect/dialect_items.json`, none of which any existing
check caught:

1. The public `dialect` field held raw source spellings. `zurich` (3 items) and
   `zurich-with-umlaut` (4 items) are the same city, so the field advertised seven
   varieties where there are six. A per-variety analysis would silently split
   Zurich in half and report it as two findings. `_canon_dialect` already held the
   right answer; it was just not the field anyone reads.

2. `orthography` had two spellings of one string - 9 items said "the Alemannic
   Wikipedia house system" and 21 said "Alemannic Wikipedia house system". Grouping
   by it would split a single orthography into two categories.

3. There was no ISO 639-3 code anywhere. Every item is Alemannic (`gsw`); the city
   is a variety within it, not a separate language. A dataset published without
   language identifiers cannot be filtered by language at all.

Nothing here changes a question, an answer or a source. It changes labels, and it
keeps the pre-normalisation value under an explicit `*_as_sourced` key so the
edit is reversible from the file alone.

verify_dialect.py imports this and applies it as it assembles
data/dialect/dialect_items.json. Nothing else writes that file.

Originally this was also a script that edited dialect_items.json in place, which
looked like it worked and was then silently undone by the next assembler run.
Keep the mapping here; keep the writing there.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ROOT / "data" / "dialect" / "dialect_items.json"

# ISO 639-3. Every item is Alemannic; the city names below are varieties WITHIN
# Alemannic, not separate languages. Basel, Zurich, Bern and Valais German are all
# `gsw`, as is Walser.
ISO639_3 = {
    "basel": "gsw",
    "zurich": "gsw",
    "bern": "gsw",
    "walser": "gsw",
    "valais": "gsw",
    # The source did not let us place the variety. The TEXT is still Alemannic, so
    # the language is known even where the city is not - which is why this is
    # `gsw` with a flag rather than `und`.
    "uncertain": "gsw",
}

# Raw source spellings -> canonical. Keys are compared after stripping case,
# diacritics and whitespace, so both `zurich` and `zürich` land here.
CANON = {
    "basel": "basel",
    "zurich": "zurich",
    "bern": "bern",
    "walser": "walser",
    "valais": "valais",
    "uncertain": "uncertain",
}

ORTHOGRAPHY_CANON = "semi-Dieth (Alemannic Wikipedia house system)"

# Human-readable names for the dataset card.
VARIETY_EN = {
    "basel": "Basel German",
    "zurich": "Zurich German",
    "bern": "Bernese German",
    "walser": "Walser German",
    "valais": "Valais German",
    "uncertain": "Alemannic, specific variety not determinable from the source",
}


def _fold(s: str) -> str:
    """Casefold and strip diacritics and spaces, so Zurich and Zurich compare equal."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


FOLDED = {_fold(k): v for k, v in CANON.items()}


def canonical_dialect(raw: str, item_id: str = "?") -> str:
    """Canonical label for a dialect, or a loud failure.

    An unrecognised label must not pass through. A dataset whose language labels
    silently accumulate typos is a dataset nobody can filter.
    """
    canon = FOLDED.get(_fold(raw))
    if canon is None:
        raise KeyError(
            f"{item_id}: unknown dialect {raw!r}. Add it to CANON in "
            f"canonical_dialect.py rather than letting it through unlabelled."
        )
    return canon


def apply_labels(item: dict) -> dict:
    """Normalise one item in place: labels, ISO 639-3, and human names."""
    raw = item.get("dialect")
    canon = canonical_dialect(raw, item.get("id", "?"))

    if raw != canon:
        item.setdefault("dialect_as_sourced", raw)
        item["dialect"] = canon

    if item.get("orthography") != ORTHOGRAPHY_CANON:
        item.setdefault("orthography_as_sourced", item.get("orthography"))
        item["orthography"] = ORTHOGRAPHY_CANON

    item["glottocode"] = ISO639_3[canon]
    item["language_name"] = VARIETY_EN[canon]
    if canon == "uncertain":
        item["variety_uncertain"] = True
    return item
