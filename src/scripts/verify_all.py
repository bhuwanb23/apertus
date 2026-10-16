"""Run the full Phase 1 verification suite. Exit 1 if any gate fails."""
import subprocess, sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
GATES = [
    ("Phase 1A.3  knowledge MCQs", "verify_knowledge.py"),
    ("Phase 1B    values scenarios", "verify_values.py"),
    ("Phase 1C    dialect items", "verify_dialect.py"),
]

failed = []
for label, script in GATES:
    r = subprocess.run([sys.executable, str(ROOT / "src" / "scripts" / script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=ROOT)
    tail = [l for l in (r.stdout or "").strip().splitlines() if l.strip()][-1:]
    status = "PASS" if r.returncode == 0 else "FAIL"
    print(f"  [{status}]  {label}")
    if tail:
        print(f"           {tail[0]}")
    if r.returncode != 0:
        failed.append(label)

print()
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
print("All Phase 1 gates pass.")
