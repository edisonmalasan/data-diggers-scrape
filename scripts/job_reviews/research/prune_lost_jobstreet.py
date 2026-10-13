"""One-time recovery: re-open jobstreet_done.json for companies whose kept
rows were lost when the 2025 re-sweep died before its final append.

Reads the crashed run's log, finds every `kept>=1` company (their rows lived
only in memory), backs up the done-set, and removes exactly those slugs so the
relaunch re-fetches them. Companies with kept=0 stay done — nothing to redo.
"""
import json
import re
from pathlib import Path

ST = Path(__file__).resolve().parents[1] / ".storage"
LOG = ST / "jobstreet_2025_resweep.log"
DONE = ST / "jobstreet_done.json"
BAK = ST / "jobstreet_done_1440.bak.json"

raw = LOG.read_bytes()
if raw.startswith((b"\xff\xfe", b"\xfe\xff")):   # Tee-Object writes UTF-16
    log = raw.decode("utf-16")
else:
    log = raw.decode("utf-8", errors="replace")
lost = set(re.findall(r"^\[\d+/2000\] ([a-z0-9\-]+): reviews=\d+ kept=[1-9]\d*",
                      log, re.M))
done = json.loads(DONE.read_text(encoding="utf-8"))
BAK.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")
new = [d for d in done if d not in lost]
DONE.write_text(json.dumps(new, indent=0), encoding="utf-8")
print(f"backed up {len(done)} done -> {BAK.name}")
print(f"pruned {len(done) - len(new)} slugs with lost rows: "
      f"done {len(done)} -> {len(new)}; todo ~= {2000 - len(new)}")
