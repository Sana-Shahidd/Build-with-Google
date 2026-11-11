"""One-off: extract the static JSON data files from docs/07_AI_AGENTS.md (§8, §9, §10)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
text = (ROOT / "docs" / "07_AI_AGENTS.md").read_text(encoding="utf-8")
DATA = ROOT / "backend" / "app" / "data"


def first_json_after(marker: str) -> dict:
    start = text.index(marker)
    block = re.search(r"```json\n(.*?)```", text[start:], re.DOTALL).group(1)
    return json.loads(block)


for marker, name in (
    ("`data/rules_keywords.json`", "rules_keywords.json"),
    ("## 9. Injury", "injury_capability_map.json"),
    ("## 10. First-aid content", "first_aid.json"),
):
    data = first_json_after(marker)
    (DATA / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(name, list(data)[:12])
