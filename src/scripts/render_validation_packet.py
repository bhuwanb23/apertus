"""
Render data/dialect/VALIDATION_PACKET.md with the 30 items and a blank answer
sheet inlined, so the packet a native speaker receives contains the actual data
rather than a placeholder.

Run:  python scripts/render_validation_packet.py
"""

import json
import unicodedata
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
DIALECT = ROOT / "data" / "dialect"
TEMPLATE = DIALECT / "VALIDATION_PACKET.md"
OUT = DIALECT / "VALIDATION_PACKET_FILLED.md"


def clean(s):
    """Render Alemannic orthography so it reads correctly in a proportional font."""
    s = unicodedata.normalize("NFC", s)
    return s


items = json.loads((DIALECT / "dialect_items.json").read_text(encoding="utf-8"))
items.sort(key=lambda i: i["id"])

blocks, sheet = [], []
by_type = defaultdict(list) if False else {}

for it in items:
    iid = it["id"]
    kind = it["task_type"]
    dialect = it["dialect"]
    sg = it.get("swiss_german_text") or it.get("prompt")

    if kind == "translation":
        lines = [
            f"### {iid} — translation ({dialect})",
            "",
            f"**Swiss German:**  *{clean(sg)}*",
            "",
            f"**My Standard German:**  {clean(it['standard_german_reference'])}",
            "",
            f"*(dialect difficulty: {it['difficulty']})*",
        ]
    else:
        lines = [
            f"### {iid} — {kind.replace('_', ' ')} ({dialect})",
            "",
            f"**Swiss German:**  *{clean(sg)}*",
            "",
            f"**My question:**  {clean(it['question'])}",
            "",
        ]
        for k in "ABCD":
            mark = " **<-- my answer key: check this one**" if k == it["correct_answer"] else ""
            lines.append(f"- **{k}.** {clean(it['options'][k])}{mark}")
        lines += ["", f"*(dialect difficulty: {it['difficulty']})*"]

    blocks.append("\n".join(lines))
    sheet.append(
        f"- [ ] {iid} · 1. {iid}: ___  2. {iid}: ___  3. {iid}: ___  4. {iid}: ___  5. {iid}: __________"
    )

tpl = TEMPLATE.read_text(encoding="utf-8")
tpl = tpl.replace("<!-- ITEMS -->", "\n\n---\n\n".join(blocks))
tpl = tpl.replace(
    "<!-- ANSWER_SHEET -->",
    "Copy this block into an email or DM and fill it in. `yes / mostly / no`, and leave blank if you skip the item.\n\n"
    "```\n" + "\n".join(sheet) + "\n```",
)
OUT.write_text(tpl, encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}  ({len(items)} items inlined)")
print(f"chars: {len(tpl)}")
