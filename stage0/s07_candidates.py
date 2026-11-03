"""0.5 + 0.6  Ranking filter -> candidates.csv / whitelist.csv / unresolved.csv / excluded.csv

Program discipline -> ranking table (user's mapping):
  comp_bio, genetics_genomics, umbrella_biomedical, biophysics -> biological_sciences
  bioengineering -> biomedical_engineering ; chemistry -> chemistry
  computer_science -> computer_science ; biostatistics (and statistics) -> statistics
  anything else (biochemistry, other:*) -> unresolved (user decides)

School-name matching (OpenAlex name + display_name_alternatives vs ranking names):
  exact      normalized equality (case, accents, punctuation, '--', 'the', 'at')
  campus_suffix  ranking name = OpenAlex name + campus suffix after '--' or ','
                 (e.g. "University of Michigan--Ann Arbor")
  no match   -> fuzzy look-up: similar name exists -> unresolved.csv (user confirms),
             otherwise -> excluded.csv (not in the ~top-60 table).
Independent institutes (non-university, grant PhDs) not found in the table ->
whitelist.csv (user confirms; kept regardless of rank once confirmed).

User decisions are read back on re-run:
  whitelist.csv  column `confirm` = 1 keeps the institute's programs
  unresolved.csv columns `user_rank` (number) or `keep` (1/0)
  candidates.csv column `selected` is preserved across re-runs.
"""
import csv
import difflib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "stage0"
R = ROOT / "rankings"
RANK_CUTOFF = 60

TABLE_OF = {
    "comp_bio": "biological_sciences", "genetics_genomics": "biological_sciences",
    "umbrella_biomedical": "biological_sciences", "biophysics": "biological_sciences",
    "bioengineering": "biomedical_engineering", "chemistry": "chemistry",
    "computer_science": "computer_science", "biostatistics": "statistics",
    "statistics": "statistics",
}
DIR_OF_DISC = {  # which direction(s) a program type serves (used when no author matched)
    "comp_bio": "A+B", "genetics_genomics": "A", "biostatistics": "A", "statistics": "A",
    "umbrella_biomedical": "A+B", "biophysics": "B", "bioengineering": "B", "chemistry": "B",
    "computer_science": "B", "biochemistry": "B",
}


def nkey(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ").replace("—", " ").replace("–", " ").replace("--", " ").replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    toks = [t for t in s.split() if t not in {"the", "at"}]
    return " ".join(toks)


def load_tables():
    T = {}
    for p in sorted(R.glob("*.csv")):
        rows = []
        with open(p) as f:
            for r in csv.DictReader(f):
                try:
                    rank = int(re.sub(r"[^0-9]", "", str(r["rank"])))
                except ValueError:
                    continue
                rows.append({"school": r["school"].strip(), "rank": rank, "source": r["source"].strip(),
                             "key": nkey(r["school"])})
        T[p.stem] = rows
    return T


def match_school(names, table):
    keys = [nkey(n) for n in names if n]
    for row in table:
        if row["key"] in keys:
            return row, "exact"
    for row in table:
        raw = row["school"]
        if "--" in raw or "," in raw:
            base = nkey(re.split(r"--|,", raw)[0])
            if base in keys:
                return row, "campus_suffix"
    return None, None


GENERIC = set("""university universities of the at and in college institute institution school state
technology medicine medical center centre health science sciences campus graduate biomedical system
main suny cuny""".split())


def dtoks(name):
    return {t for t in nkey(name).split() if t not in GENERIC}


def fuzzy(names, table, n=3):
    """Similarity on distinctive tokens (Jaccard), primary name only."""
    a = dtoks(names[0])
    scored = []
    for row in table:
        b = dtoks(re.split(r"--", row["school"])[0]) | dtoks(row["school"])
        if not a or not b or not (a & b):
            continue
        # "State" / "Tech" distinguish different schools (Georgia State vs Georgia Tech, Utah State vs Utah)
        ka, kb = nkey(names[0]).split(), nkey(row["school"]).split()
        if any((w in ka) != (w in kb) for w in ("state",)) or \
                any(any(t.startswith(w) for t in ka) != any(t.startswith(w) for t in kb)
                    for w in ("technolog", "polytechnic")):
            continue
        scored.append((round(len(a & b) / len(a | b), 2), row))
    scored.sort(key=lambda x: -x[0])
    return scored[:n]


def read_csv(path):
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def fmt_fac(m):
    dirs = "+".join(sorted(m["dirs"]))
    n = max(v["n_works"] for v in m["dirs"].values())
    tier = "core" if m["is_core"] else "1 methods paper"
    return f'{m["name"]} ({dirs}; {n} papers; {tier})'


def main():
    T = load_tables()
    if not T:
        sys.exit("no ranking tables in rankings/")
    H = json.load(open(D / "homes.json"))
    I = json.load(open(D / "institutions.json"))
    PM = json.load(open(D / "program_matches.json"))
    inst_by_name = {}
    for v in I.values():
        inst_by_name.setdefault(v["display_name"], v)

    wl_prev = {(r["school"]): r for r in read_csv(ROOT / "whitelist.csv")}
    un_prev = {(r["school"], r["program"]): r for r in read_csv(ROOT / "unresolved.csv")}
    sel_prev = {(r["school"], r["program"]): r.get("selected", "") for r in read_csv(ROOT / "candidates.csv")}

    hn = {v["name"]: v for v in H["institutions"].values()}

    def school_core(nm):
        v = hn.get(nm)
        if not v:
            return ""
        return len(set(v["A"]["core"]) | set(v["B"]["core"]))

    cands, excluded, unresolved, whitelist = [], [], [], {}
    today = date.today().isoformat()
    for inst in PM:
        name = inst["institution"]
        oa = inst_by_name.get(name, {})
        names = [name] + (oa.get("display_name_alternatives") or [])
        kind = inst.get("institution_kind") or ("university" if oa.get("type") == "education" else "independent_institute")
        if inst.get("grants_phd") is False:
            excluded.append({"school": name, "program": "(institution)", "reason":
                             "institution does not grant PhDs (program discovery evidence)",
                             "evidence_url": (inst.get("grants_phd_evidence") or {}).get("url")})
            continue
        for p in inst["programs"]:
            disc = p.get("discipline") or ""
            core = [m for m in p["matched"] if m["is_core"]]
            peri = [m for m in p["matched"] if not m["is_core"]]
            def core_dirs(m):
                cd = {d for d, v in m["dirs"].items() if v["tier"] == "core"}
                return cd or set(m["dirs"])
            dirs = sorted({d for m in (core or peri) for d in core_dirs(m)})
            direction = "+".join(dirs) if dirs else DIR_OF_DISC.get(disc, "?")
            readable = any(pg.get("readable") for pg in p.get("pages", []))
            fac_urls = [pg["url"] for pg in p.get("pages", [])]
            fetched = sorted({pg.get("fetched_at", "")[:10] for pg in p.get("pages", []) if pg.get("fetched_at")})
            row = {
                "school": name, "program": p["program_name"],
                "program_type": p.get("program_type"), "umbrella_name": p.get("umbrella_name") or "",
                "discipline": disc, "direction": direction,
                "n_relevant_faculty": len(core), "n_possible_faculty": len(peri),
                "n_core_A": sum("A" in core_dirs(m) for m in core), "n_core_B": sum("B" in core_dirs(m) for m in core),
                "top3_faculty": "; ".join(fmt_fac(m) for m in (core + peri)[:3]),
                "program_url": p.get("program_url") or "",
                "source_url": " | ".join(fac_urls) if fac_urls else (p.get("program_url") or ""),
                "fetched_at": ", ".join(fetched),
                "faculty_page_readable": readable,
                "institution_openalex_id": oa.get("id", ""),
                "school_core_authors_openalex": school_core(name),
            }
            table = TABLE_OF.get(disc)
            if not table:
                row.update(ranking_subject="", subject_rank="", reason=f"program type '{disc}' has no ranking mapping")
                if len(core) + len(peri) == 0:
                    excluded.append({**row, "reason": row["reason"] + "; and no relevant faculty matched"})
                    continue
                prev = un_prev.get((name, p["program_name"]), {})
                row.update(user_rank=prev.get("user_rank", ""), user_table=prev.get("user_table", ""),
                           keep=prev.get("keep", ""))
                if prev.get("keep") == "1" or prev.get("user_rank"):
                    pass  # user decision handled below
                else:
                    unresolved.append(row)
                    continue
            if table and table not in T:
                row.update(ranking_subject=table, subject_rank="", reason=f"ranking table {table}.csv missing")
                unresolved.append(row)
                continue
            if table:
                hit, how = match_school(names, T[table])
                row["ranking_subject"] = table
                if disc == "biostatistics":
                    row["rank_note"] = ("U.S. News 2026 ranks biostatistics separately; per the mapping the school's "
                                        "statistics rank is used as a proxy")
                if not hit and disc == "biostatistics" and kind != "independent_institute":
                    prev = un_prev.get((name, p["program_name"]), {})
                    if not (prev.get("user_rank") or prev.get("keep")):
                        row.update(reason="biostatistics program; school not in statistics.csv, which (2026 edition) "
                                   "covers statistics departments only - biostatistics is ranked separately",
                                   user_rank="", keep="")
                        unresolved.append(row)
                        continue
                if hit:
                    row.update(subject_rank=hit["rank"], rank_match=how, rank_school_name=hit["school"],
                               rank_source=hit["source"])
                    if hit["rank"] > RANK_CUTOFF:
                        excluded.append({**row, "reason": f"{table} rank {hit['rank']} > {RANK_CUTOFF}"})
                        continue
                else:
                    if kind == "independent_institute":
                        w = whitelist.setdefault(name, {
                            "school": name, "openalex_type": oa.get("type"), "programs": [],
                            "n_relevant_faculty": 0, "top_faculty": [],
                            "phd_evidence": (inst.get("grants_phd_evidence") or {}).get("url") or "",
                            "confirm": wl_prev.get(name, {}).get("confirm", "")})
                        w["programs"].append(p["program_name"])
                        w["n_relevant_faculty"] = max(w["n_relevant_faculty"], len(core))
                        w["top_faculty"] += [m["name"] for m in core[:3] if m["name"] not in w["top_faculty"]]
                        if w["confirm"] != "1":
                            continue
                        row.update(subject_rank="whitelist", rank_match="whitelist")
                    else:
                        prev = un_prev.get((name, p["program_name"]), {})
                        if prev.get("user_rank"):
                            r_ = int(prev["user_rank"])
                            row.update(subject_rank=r_, rank_match="user")
                            if r_ > RANK_CUTOFF:
                                excluded.append({**row, "reason": f"user rank {r_} > {RANK_CUTOFF}"})
                                continue
                        elif prev.get("keep") == "0":
                            excluded.append({**row, "reason": "user: drop"})
                            continue
                        elif prev.get("keep") == "1":
                            row.update(subject_rank="user-kept", rank_match="user")
                        else:
                            fz = fuzzy(names, T[table])
                            if fz and fz[0][0] >= 0.5:
                                row.update(reason="school name not found in ranking table; similar names: " +
                                           "; ".join(f'{r["school"]} (#{r["rank"]}, sim {s})' for s, r in fz),
                                           user_rank="", keep="")
                                unresolved.append(row)
                            else:
                                excluded.append({**row, "reason": f"school not in {table}.csv (top ~{RANK_CUTOFF}); "
                                                 f"closest: {fz[0][1]['school']} (sim {fz[0][0]})" if fz else "not in table"})
                            continue
            else:
                prev = un_prev.get((name, p["program_name"]), {})
                if prev.get("keep") == "0":
                    excluded.append({**row, "reason": "user: drop"})
                    continue
                row.update(subject_rank=prev.get("user_rank") or "user-kept", rank_match="user",
                           ranking_subject=prev.get("user_table", ""))
            if len(core) + len(peri) == 0 and readable:
                excluded.append({**row, "reason": "no relevant faculty matched on the program's faculty page(s)"})
                continue
            row["selected"] = sel_prev.get((name, p["program_name"]), "")
            cands.append(row)

    # institutions with relevant authors that had no program discovery
    done = {i["institution"] for i in PM}
    for v in H["institutions"].values():
        if v["name"] in done:
            continue
        nc = len(v["A"]["core"]) + len(v["B"]["core"])
        npf = len(v["A"]["peripheral"]) + len(v["B"]["peripheral"])
        if nc + npf == 0:
            continue
        t = v["type"]
        if t in ("company", "government", "funder", "archive", "other"):
            reason = f"OpenAlex institution type '{t}' (not a degree-granting university; not checked)"
        else:
            names = [v["name"]] + v.get("alternatives", [])
            ranked = [f"{tb}#{hit['rank']}" for tb, rows in T.items()
                      for hit, _ in [match_school(names, rows)] if hit]
            if not ranked:
                near = [(tb, s_, r_) for tb, rows in T.items() for s_, r_ in fuzzy(names, rows, 1) if s_ >= 0.5]
                if near and nc >= 1:
                    unresolved.append({"school": v["name"], "program": "(not enumerated)",
                                       "reason": "school name not found in ranking tables; similar names: " +
                                       "; ".join(f"{tb}: {r_['school']} (#{r_['rank']}, sim {s_})" for tb, s_, r_ in near),
                                       "n_relevant_faculty": nc, "n_possible_faculty": npf})
                    continue
            if t != "education":
                reason = (f"programs not enumerated: non-university research institute/hospital (OpenAlex type '{t}'); "
                          f"its faculty are matched via affiliated universities where listed; {nc} core + {npf} single-paper authors")
            else:
                near_txt = ""
                if not ranked:
                    near = [(tb, s_, r_) for tb, rows in T.items() for s_, r_ in fuzzy(names, rows, 1)]
                    if near:
                        tb, s_, r_ = max(near, key=lambda x: x[1])
                        near_txt = f" (closest name: {r_['school']} in {tb}, sim {s_})"
                reason = ("programs not enumerated: " +
                          (f"school ranked {', '.join(ranked)}" if ranked else
                           "school not found in any ranking table (top ~60)" + near_txt) +
                          f"; {nc} core + {npf} single-paper relevant authors")
        excluded.append({"school": v["name"], "program": "(not enumerated)", "reason": reason,
                         "n_relevant_faculty": nc, "n_possible_faculty": npf,
                         "institution_openalex_id": v["id"]})

    cands.sort(key=lambda r: (-r["n_relevant_faculty"], -r["n_possible_faculty"], r["school"]))
    ccols = ["school", "program", "program_type", "direction", "ranking_subject", "subject_rank",
             "n_relevant_faculty", "top3_faculty", "program_url", "source_url",
             "n_possible_faculty", "n_core_A", "n_core_B", "umbrella_name", "discipline", "rank_match", "rank_school_name",
             "rank_source", "rank_note", "fetched_at", "faculty_page_readable", "school_core_authors_openalex", "institution_openalex_id", "selected"]
    write_csv(ROOT / "candidates.csv", cands, ccols)
    write_csv(ROOT / "unresolved.csv", unresolved,
              ["school", "program", "discipline", "program_type", "direction", "ranking_subject", "reason",
               "n_relevant_faculty", "n_possible_faculty", "top3_faculty", "program_url", "source_url",
               "user_rank", "user_table", "keep"])
    write_csv(ROOT / "excluded.csv", excluded,
              ["school", "program", "reason", "discipline", "program_type", "direction", "ranking_subject",
               "subject_rank", "n_relevant_faculty", "n_possible_faculty", "top3_faculty", "program_url",
               "source_url", "evidence_url", "institution_openalex_id"])
    wl = []
    for w in whitelist.values():
        wl.append({**w, "programs": "; ".join(w["programs"]), "top_faculty": "; ".join(w["top_faculty"][:5])})
    write_csv(ROOT / "whitelist.csv", wl, ["school", "openalex_type", "programs", "n_relevant_faculty",
                                           "top_faculty", "phd_evidence", "confirm"])
    print(f"candidates {len(cands)} | whitelist {len(wl)} | unresolved {len(unresolved)} | excluded {len(excluded)}")


if __name__ == "__main__":
    main()
