"""Recommended shortlist (user-delegated): sets selected=1 in candidates.csv where the
user has not set anything, and pilot=1 for the stage-1 pilot programs.
Rules: n_relevant_faculty >= 5, or >= 4 with subject rank <= 25; whitelist / user-kept rows
count as rank 30; at most 2 programs per school (pilot programs extra) (most relevant faculty first); pilot
programs (data/stage1/selection.json) always selected.  Logged to decisions_log.md.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    rows = list(csv.DictReader(open(ROOT / "candidates.csv")))
    sel = json.load(open(ROOT / "data" / "stage1" / "selection.json"))
    pilot = {(v["school"], v["program"]) for v in sel.values()}
    per_school = defaultdict(int)
    chosen = []
    for r in rows:                                           # already sorted by relevant faculty
        key = (r["school"], r["program"])
        try:
            rank = int(r["subject_rank"])
        except ValueError:
            rank = 30
        n = int(r["n_relevant_faculty"] or 0)
        ok = key in pilot or n >= 5 or (n >= 4 and rank <= 25)
        if r.get("selected", "") == "" and ok and (per_school[r["school"]] < 2 or key in pilot):
            r["selected"] = "1"
            r["selected_by"] = "claude-recommended"
        if r.get("selected") == "1":
            per_school[r["school"]] += 1
            chosen.append(r)
        r["pilot"] = "1" if key in pilot else ""
    # access-limited rule: faculty pages unreadable (blocked / bot-protected), but the school has
    # many relevant OpenAlex authors and a top-10 subject rank -> 1 program per school
    PRIO = ["comp_bio", "genetics_genomics", "biostatistics", "biophysics", "umbrella_biomedical",
            "bioengineering", "statistics", "computer_science", "chemistry"]
    best = {}
    for r in rows:
        try:
            rank = int(r["subject_rank"])
        except ValueError:
            continue
        sc = int(r.get("school_core_authors_openalex") or 0)
        weak = r.get("faculty_page_readable") in ("False", "") or int(r["n_relevant_faculty"] or 0) <= 3
        if r.get("selected") or not weak or sc < 15 or rank > 10 or r["discipline"] not in PRIO:
            continue
        if per_school[r["school"]] >= 2:
            continue
        k = (PRIO.index(r["discipline"]), rank, -int(r["n_relevant_faculty"] or 0))
        if r["school"] not in best or k < best[r["school"]][0]:
            best[r["school"]] = (k, r)
    for _, r in best.values():
        r["selected"] = "1"
        r["selected_by"] = "claude-recommended (access-limited: faculty pages unreadable, school has many relevant authors)"
        per_school[r["school"]] += 1
        chosen.append(r)
    cols = list(rows[0].keys())
    for c in ("selected_by", "pilot"):
        if c not in cols:
            cols.append(c)
    with open(ROOT / "candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(ROOT / "decisions_log.md", "a") as f:
        f.write("\n## Recommended shortlist (candidates.csv selected=1)\n\n"
                "rule: >=5 relevant faculty, or >=4 with subject rank <=25; max 2 programs per school; "
                "pilot programs always included\n\n")
        for r in chosen:
            f.write(f"* {r['school']} / {r['program'][:70]} ({r['direction']}, {r['ranking_subject']} "
                    f"#{r['subject_rank']}, {r['n_relevant_faculty']} relevant faculty)"
                    f"{' [pilot]' if r['pilot'] else ''}\n")
    print(len(chosen), "selected;", sum(1 for r in chosen if r["pilot"]), "pilot")
    for r in chosen:
        print(f"  {r['school'][:34]:34} | {r['program'][:52]:52} | {r['direction']:3} | {r['n_relevant_faculty']}{' P' if r['pilot'] else ''}")


if __name__ == "__main__":
    main()
