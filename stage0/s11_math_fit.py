"""Classify programs against the applicant's math background (data/applicant_profile.json)
using the quoted official prerequisites in data/stage0/prereqs/*.json.

status
  required_unmet    a REQUIRED topic the applicant lacks (e.g. real analysis)      -> drop
  uncertain         requires probability / mathematical statistics: depends on whether the
                    applicant's statistics courses count                           -> keep, flag
  recommended_unmet only recommended / strongly recommended topics missing          -> keep, flag
  met               all stated requirements satisfied                              -> keep
  not_stated        no accessible official page states math prerequisites         -> keep
  unverifiable      file missing or pages blocked                                  -> keep, flag
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROF = json.load(open(ROOT / "data" / "applicant_profile.json"))
HAVE = set(PROF["math_completed"]) | set(PROF["stats_completed"]) | {"programming"}
UNCERTAIN = {"probability", "mathematical_statistics"}


def classify(d):
    reqs = d.get("requirements") or []
    if not reqs:
        return ("not_stated" if d.get("not_stated") else "unverifiable"), [], []
    missing_req, missing_rec, unc = set(), set(), set()
    for r in reqs:
        topics = set(r.get("topics") or [])
        lack = {t for t in topics if t not in HAVE and not t.startswith("other:programming")}
        if r["kind"] == "required":
            missing_req |= lack - UNCERTAIN
            unc |= lack & UNCERTAIN
        elif r["kind"] in ("strongly_recommended", "recommended", "typical_background"):
            missing_rec |= lack
    if missing_req:
        return "required_unmet", sorted(missing_req), sorted(missing_rec | unc)
    if unc:
        return "uncertain", sorted(unc), sorted(missing_rec)
    if missing_rec:
        return "recommended_unmet", [], sorted(missing_rec)
    return "met", [], []


def main():
    out = {}
    for p in sorted(glob.glob(str(ROOT / "data" / "stage0" / "prereqs" / "*.json"))):
        d = json.load(open(p))
        st, req, rec = classify(d)
        out[d["key"]] = {"school": d["school"], "program": d["program"], "status": st,
                         "missing_required": req, "missing_recommended": rec,
                         "quotes": [(r["kind"], r["quote"], r["source_url"]) for r in d.get("requirements", [])],
                         "problems": d.get("problems", [])}
    json.dump(out, open(ROOT / "data" / "stage0" / "math_fit.json", "w"), indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(f"{k:20} {v['status']:18} req-missing={v['missing_required']} rec-missing={v['missing_recommended']}")


if __name__ == "__main__":
    main()
