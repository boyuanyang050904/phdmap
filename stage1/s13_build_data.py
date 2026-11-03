"""Assemble data.json (input for the stage-2 map / tracker) from stage-1 files.

data.json
{
  "generated_at": ISO, "schema": 1,
  "schools":  {school_id: {id, name, lat, lng, city, region, geo_source_url, geo_fetched_at}},
  "programs": [{
      id, school_id, school, name, program_type, umbrella_name, discipline, directions,
      ranking: {subject, rank, source, match}, stage0: {n_relevant_faculty, n_possible_faculty},
      fields: {program_url, deadline, priority_deadline, application_fee, fee_waiver, gre_policy,
               letters_required, application_system_url, admissions_mode,
               contact_faculty_advice, stipend, guaranteed_years, pr_domestic,
               t32_citizen_pr_only},           # each {value, source_url, fetched_at, quote, ...}
      toefl: {waiver_conditions, waiver_basis, us_degree_waives, pr_exempt, min_total,
              min_subscores, validity_rule, di_code, self_report_accepted},
      direct_admission: bool|null,            # admissions_mode in (direct, both)
      faculty_list_source_urls: [...], n_faculty_scored: int,
      faculty: [{name, title{value,source_url,quote}, lab_url{...}, direction, score,
                 papers:[{title, year, url, venue, source_url, fetched_at}],
                 why:{text, based_on:[work ids]},
                 affiliation:{status: consistent|possibly_moved|unknown, openalex_recent:[...],
                              last_known:[...], source_url},
                 new_assistant_professor:{value, title, first_last_author_year, rule, ...},
                 openalex_id, openalex_url}],
      problems: [...], checked_at
  }]
}
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D1 = ROOT / "data" / "stage1"
SIMPLE = ["program_url", "deadline", "priority_deadline", "application_fee", "fee_waiver", "gre_policy",
          "letters_required", "application_system_url", "admissions_mode", "contact_faculty_advice",
          "stipend", "guaranteed_years", "pr_domestic", "t32_citizen_pr_only"]


def main():
    sel = json.load(open(D1 / "selection.json"))
    I = json.load(open(ROOT / "data" / "stage0" / "institutions.json"))
    cands = {(r["school"], r["program"]): r for r in csv.DictReader(open(ROOT / "candidates.csv"))}
    schools, programs = {}, []
    for pid, s in sel.items():
        pf, ff = D1 / "programs" / f"{pid}.json", D1 / "faculty" / f"{pid}.json"
        if not pf.exists():
            continue
        prog = json.load(open(pf))
        fac = json.load(open(ff)) if ff.exists() else {"top": [], "n_faculty": 0}
        inst = I.get(s["institution_id"], {})
        geo = inst.get("geo") or {}
        sid = s["institution_id"].rsplit("/", 1)[-1]
        schools[sid] = {"id": sid, "name": s["school"], "lat": geo.get("latitude"), "lng": geo.get("longitude"),
                        "city": geo.get("city"), "region": geo.get("region"),
                        "geo_source_url": f"https://api.openalex.org/institutions/{sid}",
                        "geo_fetched_at": inst.get("_fetched_at")}
        c = cands.get((s["school"], s["program"]), {})
        mode = ((prog.get("admissions_mode") or {}).get("value") or "")
        mode_l = str(mode).lower()
        out_fac = []
        for x in fac.get("top", []):
            r = {"why": x.get("why"), "papers": x.get("chosen_papers"),
                 "based_on": [w["id"] for w in x.get("chosen_papers") or []]} if x.get("why") else {}
            ac = x.get("affiliation_check") or {}
            ar = x.get("affiliation_recent") or {}
            status = ar.get("status") or "unknown"
            out_fac.append({
                "name": x["name"], "title": x.get("title_field"), "lab_url": x.get("lab_field"),
                "profile_url": x.get("profile_url"),
                "direction": x.get("direction"), "score": x.get("score"),
                "score_A": x.get("score_A"), "score_B": x.get("score_B"),
                "papers": [{"title": w["title"], "year": w["year"], "url": w["landing_url"], "venue": w.get("venue"),
                            "openalex_id": w["id"], "role": w.get("role"), "subtopics": w.get("subtopics"),
                            "source_url": w["source_url"], "fetched_at": w["fetched_at"]}
                           for w in (r.get("papers") or x.get("top_works", [])[:3])],
                "why": {"text": r.get("why"), "based_on": r.get("based_on", [])} if r else None,
                "affiliation": {"status": status, "recent_works": ar.get("recent_works"),
                                "rule": ar.get("rule"), "last_known": ac.get("last_known_institutions"),
                                "program_page": s["school"], "source_url": x.get("openalex_url")},
                "new_assistant_professor": x.get("new_assistant_professor"),
                "openalex_id": x.get("openalex_id"), "openalex_url": x.get("openalex_url")})
        dirs = sorted({d for f in out_fac for d in (f.get("direction") or "").split("+") if d}) or \
            (c.get("direction") or "").split("+")
        programs.append({
            "id": pid, "school_id": sid, "school": s["school"], "name": s["program"],
            "program_type": s.get("program_type"), "umbrella_name": s.get("umbrella_name"),
            "discipline": s.get("discipline"), "directions": [d for d in dirs if d],
            "ranking": {"subject": c.get("ranking_subject"), "rank": c.get("subject_rank"),
                        "source": c.get("rank_source"), "match": c.get("rank_match")},
            "stage0": {"n_relevant_faculty": c.get("n_relevant_faculty"),
                       "n_possible_faculty": c.get("n_possible_faculty")},
            "fields": {k: prog.get(k) for k in SIMPLE},
            "toefl": prog.get("toefl"),
            "direct_admission": (None if not mode_l else ("direct" in mode_l or "both" in mode_l)),
            "faculty_list_source_urls": (prog.get("faculty_list") or {}).get("source_urls"),
            "n_faculty_scored": fac.get("n_faculty"), "faculty": out_fac,
            "problems": prog.get("problems", []), "checked_at": prog.get("checked_at")})
    data = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "schema": 1,
            "schools": schools, "programs": programs}
    json.dump(data, open(ROOT / "data.json", "w"), indent=1, ensure_ascii=False)
    print("data.json:", len(schools), "schools,", len(programs), "programs,",
          sum(len(p["faculty"]) for p in programs), "faculty")


if __name__ == "__main__":
    main()
