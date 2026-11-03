"""Apply Claude's recommended stage-0 decisions (the user delegated these decisions on
2026-11-03: "接下来全按你推荐的来").  Only EMPTY decision fields are filled, so anything
the user sets by hand wins.  Every decision is logged to decisions_log.md.

Rules
 1. Program types without a ranking table -> user_discipline_map.json:
      life-science types (biochemistry, biology, cell/molecular, immunology, microbiology,
        cancer biology, pharmacology/pharmaceutical, translational, physiology, genetics)
        -> biological_sciences
      epidemiology / population / public health      -> biostatistics (statistics if absent)
      chemical / materials engineering               -> chemistry
      molecular / bio- engineering variants          -> biomedical_engineering
      math, computational science, data science, EE, informatics, health AI -> computer_science
      anything else -> not mapped (rule 3)
 2. whitelist.csv confirm = 1 if a PhD program was verified on a fetched page AND >=1 core
    relevant faculty matched; else 0.
 3. unresolved.csv keep:
      program rows with no mapping: keep=1 if >=2 relevant faculty matched, else 0
      '(no program verified)' schools: keep=1 (placeholder) if >=10 core OpenAlex authors,
        else 0
      '(not enumerated)' name-mismatch rows: keep=0 (OpenAlex mis-affiliation or a
        different school with a similar name)
"""
import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []


def table_for(disc, have_biostat):
    d = (disc or "").lower()
    if re.search(r"epidem|population|public_health", d):
        return "biostatistics" if have_biostat else "statistics"
    if re.search(r"biochem|biolog|cell|immun|microbio|cancer|pharma|translational|physiolog|genetic|genom|"
                 r"life_sci|biomedical_sci|molecular_med|neuro", d):
        return "biological_sciences"
    if re.search(r"chemical|materials", d):
        return "chemistry"
    if re.search(r"molecular_eng|bioeng|biological_eng|biomedical_eng", d):
        return "biomedical_engineering"
    if re.search(r"math|computational_sci|data_sci|electrical|informatics|health_ai|artificial|computing", d):
        return "computer_science"
    return None


def rows(p):
    p = ROOT / p
    return list(csv.DictReader(open(p))) if p.exists() else []


def write(p, rs):
    if not rs:
        return
    with open(ROOT / p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0].keys()))
        w.writeheader()
        w.writerows(rs)


def run_s07():
    subprocess.run([sys.executable, str(ROOT / "stage0" / "s07_candidates.py")], check=True)


def main():
    have_biostat = (ROOT / "rankings" / "biostatistics.csv").exists()
    # 1. discipline map
    um_path = ROOT / "user_discipline_map.json"
    um = json.load(open(um_path)) if um_path.exists() else {}
    for r in rows("unresolved.csv"):
        m = re.match(r"program type '(.+?)' has no ranking mapping", r.get("reason", ""))
        if m:
            disc = m.group(1)
            t = table_for(disc, have_biostat)
            if t and disc not in um:
                um[disc] = t
                LOG.append(f"map program type `{disc}` -> `{t}`")
    um["_comment"] = ("Program-type -> ranking-table rules. Entries were filled by Claude on "
                      f"{date.today()} under the user's delegation; edit freely and re-run s07.")
    json.dump(um, open(um_path, "w"), indent=1, ensure_ascii=False)
    run_s07()
    # second pass: types that only appear after the first re-run
    added = 0
    for r in rows("unresolved.csv"):
        m = re.match(r"program type '(.+?)' has no ranking mapping", r.get("reason", ""))
        if m and m.group(1) not in um:
            t = table_for(m.group(1), have_biostat)
            if t:
                um[m.group(1)] = t
                LOG.append(f"map program type `{m.group(1)}` -> `{t}`")
                added += 1
    if added:
        json.dump(um, open(um_path, "w"), indent=1, ensure_ascii=False)
        run_s07()
    # 2. whitelist
    wl = rows("whitelist.csv")
    for r in wl:
        if r.get("confirm", "") == "":
            verified = not r["programs"].startswith("(PhD programs NOT verified")
            n = int(r.get("n_relevant_faculty") or 0)
            r["confirm"] = "1" if verified and n >= 1 else "0"
            LOG.append(f"whitelist `{r['school']}` confirm={r['confirm']} "
                       f"({'PhD verified' if verified else 'PhD not verified'}, {n} core relevant faculty)")
    write("whitelist.csv", wl)
    # 3. unresolved keep
    un = rows("unresolved.csv")
    for r in un:
        if r.get("keep", "") or r.get("user_rank", "") or r.get("decision_status") == "decided":
            continue
        n = int(float(r.get("n_relevant_faculty") or 0))
        prog, reason = r["program"], r.get("reason", "")
        if prog == "(no program verified)":
            r["keep"] = "1" if n >= 10 else "0"
            why = f"school pages unreadable; {n} core OpenAlex authors"
        elif prog == "(not enumerated)":
            r["keep"] = "0"
            why = "name only resembles a ranked school (OpenAlex mis-affiliation / different school)"
        else:
            r["keep"] = "1" if n >= 2 else "0"
            why = f"{reason[:80]}; {n} relevant faculty matched"
        LOG.append(f"unresolved `{r['school']} / {prog[:60]}` keep={r['keep']} ({why})")
    write("unresolved.csv", un)
    run_s07()
    write_log()
    print(f"{len(LOG)} new decisions this run")


def write_log():
    """decisions_log.md = the CURRENT decision state (regenerated every run)."""
    um = json.load(open(ROOT / "user_discipline_map.json"))
    L = ["# Decisions log", "",
         "Recommended decisions applied by Claude under the user's delegation "
         "(\u201c接下来全按你推荐的来\u201d, 2026-11-03). Anything set by hand in whitelist.csv, "
         "unresolved.csv (keep / user_rank) or user_discipline_map.json takes precedence; re-run "
         "`python3 stage0/s07_candidates.py` after editing.", "",
         "## Ranking-table mapping for program types without a table (user_discipline_map.json)", ""]
    L += [f"* `{k}` -> `{v}`" for k, v in sorted(um.items()) if not k.startswith("_")]
    L += ["", "## Biostatistics", "",
          "* biostatistics programs use rankings/biostatistics.csv (U.S. News 2026 ranks biostatistics "
          "separately from statistics)" if (ROOT / "rankings" / "biostatistics.csv").exists() else
          "* biostatistics programs use rankings/statistics.csv", "",
          "## Whitelist (independent institutes)", "",
          "rule: confirm=1 if a PhD program was verified on a fetched page and >=1 core relevant faculty matched", ""]
    L += [f"* {r['school']}: confirm={r['confirm']} ({r['n_relevant_faculty']} core relevant faculty)"
          for r in rows("whitelist.csv")]
    L += ["", "## Unresolved items", "",
          "rules: program types with no table -> keep if >=2 relevant faculty; unreadable schools -> keep "
          "(placeholder row) if >=10 core OpenAlex authors; name-only resemblance -> drop", ""]
    L += [f"* {r['school']} / {r['program'][:70]}: keep={r.get('keep') or '-'} "
          f"{('user_rank=' + r['user_rank']) if r.get('user_rank') else ''} [{r.get('decision_status')}]"
          for r in rows("unresolved.csv")]
    (ROOT / "decisions_log.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
