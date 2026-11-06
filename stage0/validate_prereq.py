"""Check that every quote in data/stage0/prereqs/*.json occurs on its cached source page."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from stage1.validate import page_plain, squash  # noqa: E402

bad = 0
for p in sys.argv[1:]:
    d = json.load(open(p))
    errs = []
    for r in d.get("requirements", []):
        txt = page_plain(r["source_url"])
        if squash(r["quote"]) not in txt.replace("’", "'") and squash(r["quote"]).replace("’", "'") not in txt.replace("’", "'"):
            errs.append(f"quote not found on {r['source_url']}: {r['quote'][:80]!r}")
    print(f"{p}: {len(errs)} problems, {len(d.get('requirements', []))} requirement quotes")
    for e in errs:
        print("   ", e)
    bad += bool(errs)
sys.exit(1 if bad else 0)
