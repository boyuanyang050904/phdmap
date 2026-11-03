"""Print the heuristic shortlist (top N by score) with their best works, for review."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
pid, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 15
d = json.load(open(ROOT / "data/stage1/faculty" / f"{pid}.json"))
# all candidates with works are only stored for 'top'; re-run keeps full list in all_scores
full = {x["name"]: x for x in d.get("all_full", [])} or {x["name"]: x for x in d["top"]}
for x in sorted(d["all_full"] if "all_full" in d else d["top"], key=lambda x: -x["score"])[:n]:
    print(f"## {x['name']} | score {x['score']} (A {x['score_A']}, B {x['score_B']}) | dir {x['direction']} "
          f"| at-school works {x.get('works_at_school')}/{x.get('works_in_window')} | aff ok {x['affiliation_check']['matches_school']}")
    for w in x["top_works"][:4]:
        print(f"   - {w['year']} [{w['role']}, {'M' if w['methods'] else 'app'}, {','.join(w['subtopics'])}] {w['title'][:110]}")
