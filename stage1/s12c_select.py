"""Apply the reviewed faculty selection: data/stage1/faculty_reasons.json
  {program_id: [{"name": ..., "why": ..., "papers": ["title prefix", ...]}, ...]}
For each entry, the faculty record is taken from the heuristic run (all_full); the cited
papers must be among that person's scored works (matched by title prefix), so every reason
is tied to OpenAlex records.  Writes faculty/<id>.json "top" in the reviewed order.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D1 = ROOT / "data" / "stage1"


def main(pids):
    R = json.load(open(D1 / "faculty_reasons.json"))
    for pid in pids:
        p = D1 / "faculty" / f"{pid}.json"
        d = json.load(open(p))
        full = {x["name"]: x for x in d.get("all_full", [])}
        top = []
        for e in R[pid]:
            x = full.get(e["name"])
            if not x:
                sys.exit(f"{pid}: {e['name']} not in heuristic candidates")
            papers = []
            for pref in e["papers"]:
                w = next((w for w in x["top_works"] if (w["title"] or "").lower().startswith(pref.lower())), None)
                if not w:
                    sys.exit(f"{pid}/{e['name']}: paper not found among scored works: {pref}")
                papers.append(w)
            x = dict(x)
            x["chosen_papers"] = papers
            x["why"] = e["why"]
            top.append(x)
        d["top"] = top
        d["selection"] = "reviewed: heuristic shortlist (sum of 10 best relevant works) re-ranked by reading paper content"
        json.dump(d, open(p, "w"), indent=1)
        print(pid, [x["name"] for x in top])


if __name__ == "__main__":
    main(sys.argv[1:])
