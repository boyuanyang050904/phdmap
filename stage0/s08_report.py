"""Stage-0 summary -> stage0_report.md (what was found, what needs the user's decision)."""
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "stage0"


def rows(p):
    return list(csv.DictReader(open(ROOT / p))) if (ROOT / p).exists() else []


def main():
    H = json.load(open(D / "homes.json"))
    PM = json.load(open(D / "program_matches.json"))
    cands, wl, un, ex = rows("candidates.csv"), rows("whitelist.csv"), rows("unresolved.csv"), rows("excluded.csv")
    nA = sum(1 for a in H["authors"].values() if "A" in a["dirs"] and a["dirs"]["A"]["tier"] == "core")
    nB = sum(1 for a in H["authors"].values() if "B" in a["dirs"] and a["dirs"]["B"]["tier"] == "core")
    works = {d: sum(1 for _ in open(D / f"works_{d}.jsonl")) for d in "AB"}
    L = ["# Stage 0 report", ""]
    L += ["## Counts", "",
          f"* OpenAlex works (2022+, ≥1 US author): A {works['A']}, B {works['B']}",
          f"* core relevant US last/corresponding authors: A {nA}, B {nB}",
          f"* institutions with program discovery: {len(PM)}; programs recorded: "
          f"{sum(len(i['programs']) for i in PM)}",
          f"* candidates.csv {len(cands)} | whitelist.csv {len(wl)} | unresolved.csv {len(un)} | excluded.csv {len(ex)}",
          ""]
    dirs = Counter(r["direction"] for r in cands)
    L += ["candidates by direction: " + ", ".join(f"{k} {v}" for k, v in sorted(dirs.items())), ""]
    L += ["## Top 25 candidates", "", "| # | school | program | dir | rank | relevant faculty |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(cands[:25], 1):
        L.append(f"| {i} | {r['school']} | {r['program'][:60]} | {r['direction']} | "
                 f"{r['ranking_subject']} #{r['subject_rank']} | {r['n_relevant_faculty']} (+{r['n_possible_faculty']}) |")
    L += ["", "## Excluded programs with the most relevant faculty (check these)", "",
          "| school | program | reason | faculty |", "|---|---|---|---|"]
    exs = sorted([r for r in ex if r.get("n_relevant_faculty")],
                 key=lambda r: -int(r["n_relevant_faculty"] or 0))[:20]
    for r in exs:
        L.append(f"| {r['school']} | {r['program'][:50]} | {r['reason'][:90]} | {r['n_relevant_faculty']} |")
    # fetch problems
    blocked, unreach = Counter(), Counter()
    log = ROOT / "cache" / "fetch_log.jsonl"
    if log.exists():
        for line in open(log):
            e = json.loads(line)
            h = urlsplit(e.get("url", "")).netloc
            if e["event"] == "robots_blocked":
                blocked[h] += 1
            elif e["event"] in ("robots_unreachable", "network_error"):
                unreach[h] += 1
    L += ["", "## Sites not fetched", "",
          f"robots.txt disallowed ({len(blocked)} hosts): " + ", ".join(sorted(blocked)), "",
          f"unreachable / TLS / proxy errors ({len(unreach)} hosts): " + ", ".join(sorted(unreach)), ""]
    probs = []
    for i in PM:
        for p in i.get("problems", []):
            probs.append(f"* **{i['institution']}**: {p}")
    L += ["## Problems reported during program discovery", ""] + probs
    (ROOT / "stage0_report.md").write_text("\n".join(L) + "\n")
    print("wrote stage0_report.md")


if __name__ == "__main__":
    main()
