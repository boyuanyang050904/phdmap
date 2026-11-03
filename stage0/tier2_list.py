"""Pick second-wave institutions for program discovery:
 * education institutions not in wave 1 with >=1 core relevant author whose name
   matches (exact/campus_suffix/alias) any ranking table, and
 * independent institutes (non-university) with >=1 core or >=2 single-paper authors,
   excluding companies / government / national labs (not degree-granting by OpenAlex type).
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from stage0.s07_candidates import load_tables, match_school  # noqa

H = json.load(open(ROOT / "data/stage0/homes.json"))
G = set(sum(json.load(open(ROOT / "data/stage0/program_groups.json")), []))
T = load_tables()
edu, indep = [], []
for v in H["institutions"].values():
    if v["name"] in G:
        continue
    nc = len(v["A"]["core"]) + len(v["B"]["core"])
    npf = len(v["A"]["peripheral"]) + len(v["B"]["peripheral"])
    names = [v["name"]] + v.get("alternatives", [])
    hits = {t: m[0]["rank"] for t, rows in T.items() for m in [match_school(names, rows)] if m[0]}
    if v["type"] == "education" and nc >= 1 and hits:
        edu.append((nc, npf, v["name"], hits))
    elif v["type"] in ("nonprofit", "healthcare", "facility", "education") and (nc >= 1 or npf >= 2) \
            and not re.search(r"National|Laborator|Division of|Center for|Department of|Biohub|Broad|Klarman|"
                              r"Stanley|Hospital|Health$|Brigham|Mass General|Dana-Farber|Alliance|Consortium|"
                              r"Observatory|Genetic Alliance|Aligning|Henry Ford", v["name"]) \
            and not (v["type"] == "education" and not hits and re.search(r"University|College", v["name"])
                     and not re.search(r"Rockefeller|Baylor College of Medicine|Toyota", v["name"])):
        indep.append((nc, npf, v["name"], hits))
edu.sort(reverse=True); indep.sort(reverse=True)
print("EDU", len(edu)); [print("  ", r) for r in edu]
print("INDEP", len(indep)); [print("  ", r) for r in indep]
json.dump({"edu": [r[2] for r in edu], "indep": [r[2] for r in indep]}, open(ROOT / "data/stage0/tier2.json", "w"), indent=1)
