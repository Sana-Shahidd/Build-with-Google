"""One-off generator: country_profiles.json and models/enums.py from the docs/migrations."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"

text = (ROOT / "docs" / "07_AI_AGENTS.md").read_text(encoding="utf-8")
start = text.index("## 12. Country profiles")
block = re.search(r"```json\n(.*?)```", text[start:], re.DOTALL).group(1)
profiles = json.loads(block)
(APP / "data" / "country_profiles.json").write_text(
    json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8"
)

sql = (ROOT / "supabase" / "migrations" / "0001_extensions_enums.sql").read_text(
    encoding="utf-8"
)
add = (ROOT / "supabase" / "migrations" / "0006a_enum_additions.sql").read_text(
    encoding="utf-8"
)
enums: dict[str, list[str]] = {}
for name, vals in re.findall(r"create type public\.(\w+) as enum\s*\(([^)]*)\)", sql):
    enums[name] = re.findall(r"'([^']+)'", vals)
for name, value in re.findall(
    r"alter type public\.(\w+)\s+add value if not exists '([^']+)'", add
):
    enums[name].append(value)

out = [
    '"""Python mirror of the DB enums (docs/05_DATABASE_SCHEMA.md §1 and 0006a)."""',
    "",
    "from enum import StrEnum",
    "",
]
for name, values in enums.items():
    cls = "".join(p.capitalize() for p in name.split("_"))
    out += ["", f"class {cls}(StrEnum):"]
    for v in values:
        key = v.replace("+", "_POS").replace("-", "_NEG").upper()
        out.append(f'    {key} = "{v}"')
out.append("")
(APP / "models" / "enums.py").write_text("\n".join(out), encoding="utf-8")
print(list(enums))
