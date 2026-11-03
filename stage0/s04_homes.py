"""0.2b  Resolve each relevant author to an academic home.

Evidence used (all from OpenAlex):
  * institutions on the author's own relevant works in their latest 2 years
  * the author entity's last_known_institutions (weight 2)
Each institution is rolled up along its OpenAlex lineage to the top-most
non-"system" education ancestor (e.g. Stanford Medicine -> Stanford University;
UCSF stays UCSF, not "University of California System").
Non-education institutions with no education ancestor (Broad, Fred Hutch,
HHMI, companies, hospitals...) are kept separately; if the author also has an
education home that one is used.

Output: data/stage0/homes.json
  authors: {aid: {..., homes:[{id,name,type,weight}], primary, non_edu:[...]}}
  institutions: {home_id: {name,type,geo, A:{core:[],peripheral:[]}, B:{...}}}
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "stage0"
SYSTEM_RE = re.compile(r"\bsystem\b|^State University of New York$|^City University of New York$|"
                       r"^University of California$|^Texas A&M University System", re.I)
# employers that are never a student's PhD home; the host university is used instead
PASS_THROUGH = {"Howard Hughes Medical Institute"}


STOP = set("""university universities of the at in and for medicine medical school college hospital
hospitals center centre health healthcare institute institutes system state research sciences science
campus foundation clinic clinical national laboratory laboratories graduate department""".split())


def tokens(name):
    return {t for t in re.findall(r"[a-z]+", name.lower().replace("&", " ")) if t not in STOP and len(t) > 2}


REJECTED = set()
BLOCK = {(b["child"], b["ancestor"]) for b in json.load(open(ROOT / "stage0" / "lineage_overrides.json"))["block"]}


def main():
    I = json.load(open(D / "institutions.json"))
    E = json.load(open(D / "author_entities.json"))

    def edu_root(iid):
        """Top-most US, non-'system' education ancestor in OpenAlex lineage (or self)."""
        inst = I.get(iid)
        if not inst:
            return None
        self_edu = inst.get("type") == "education" and not SYSTEM_RE.search(inst["display_name"])
        anc = []
        for a_id in (inst.get("lineage") or []):
            if a_id == iid:
                continue
            a = I.get(a_id)
            if not a or a.get("country_code") != "US" or a.get("type") != "education":
                continue
            if SYSTEM_RE.search(a["display_name"]):
                continue
            if (inst["display_name"], a["display_name"]) in BLOCK:
                REJECTED.add((inst["display_name"], a["display_name"], "manual block"))
                continue
            anc.append(a_id)
        if not anc:
            return iid if self_edu else None
        # roots = ancestors that have no other candidate ancestor above them
        roots = [a for a in anc if not ((set(I.get(a, {}).get("lineage") or []) - {a}) & set(anc))]
        if len(roots) == 1:
            return roots[0]
        # multi-university entities (CZ Biohub, QB3, IGI, CTBP ...): ambiguous -> no roll-up
        REJECTED.add((inst["display_name"], " + ".join(I[r]["display_name"] for r in roots), "ambiguous"))
        return iid if self_edu else None

    authors_out = {}
    agg = defaultdict(lambda: {"A": {"core": [], "peripheral": []}, "B": {"core": [], "peripheral": []}})
    for d in "AB":
        A = json.load(open(D / f"authors_{d}.json"))
        for aid, r in A.items():
            if r["n_methods"] < 1:
                continue
            tier = "core" if r["n_works"] >= 2 else "peripheral"
            w = defaultdict(float)
            for iid, e in r["institutions"].items():
                recent = sum(1 for y in e["years"] if y >= r["last_year"] - 1)
                w[iid] += recent
            ent = E.get(aid, {})
            for i in ent.get("last_known_institutions") or []:
                if i.get("country_code") == "US":
                    w[i["id"]] += 2
            homes = defaultdict(float)
            units = defaultdict(set)
            non_edu = defaultdict(float)
            for iid, wt in w.items():
                if wt <= 0:
                    continue
                root = edu_root(iid)
                if root:
                    homes[root] += wt
                    if iid != root:
                        units[root].add(I.get(iid, {}).get("display_name", iid))
                else:
                    nm = I.get(iid, {}).get("display_name", iid)
                    if nm not in PASS_THROUGH:
                        non_edu[iid] += wt
            if not homes and non_edu:
                # independent institute / hospital / company as its own home
                homes = dict(non_edu)
            hl = sorted(homes.items(), key=lambda kv: -kv[1])
            if not hl:
                continue
            top = hl[0][1]
            keep = [(h, wt) for h, wt in hl if wt >= max(1.0, 0.34 * top)]
            rec = authors_out.setdefault(aid, {
                "id": aid, "name": r["name"], "orcid": r["orcid"],
                "display_name_alternatives": ent.get("display_name_alternatives", []),
                "h_index": (ent.get("summary_stats") or {}).get("h_index"),
                "works_count": ent.get("works_count"),
                "last_known_institutions": [i["display_name"] for i in ent.get("last_known_institutions") or []],
                "entity_source_url": ent.get("_source_url"), "entity_fetched_at": ent.get("_fetched_at"),
                "dirs": {},
            })
            rec["dirs"][d] = {"tier": tier, "score": r["score"], "n_works": r["n_works"],
                              "n_methods": r["n_methods"], "subtopic_counts": r["subtopic_counts"],
                              "top_works": sorted(r["works"], key=lambda x: (-x["methods"], -x["cites"]))[:5]}
            rec["homes"] = [{"id": h, "name": I.get(h, {}).get("display_name", h),
                             "type": I.get(h, {}).get("type"), "weight": wt,
                             "units": sorted(units.get(h, []))} for h, wt in keep]
            rec["non_edu"] = [{"id": h, "name": I.get(h, {}).get("display_name", h),
                               "type": I.get(h, {}).get("type")} for h in non_edu]
            for h, _ in keep:
                agg[h][d][tier].append(aid)

    insts = {}
    for h, v in agg.items():
        inst = I.get(h, {})
        insts[h] = {"id": h, "name": inst.get("display_name", h), "type": inst.get("type"),
                    "geo": inst.get("geo"), "homepage_url": inst.get("homepage_url"),
                    "ror": inst.get("ror"),
                    "alternatives": inst.get("display_name_alternatives", []),
                    "acronyms": inst.get("display_name_acronyms", []),
                    "source_url": f"https://api.openalex.org/institutions/{h.rsplit('/',1)[-1]}",
                    **v}
    json.dump({"authors": authors_out, "institutions": insts}, open(D / "homes.json", "w"))
    rows = sorted(insts.values(), key=lambda x: -(len(x["A"]["core"]) + len(x["B"]["core"])))
    print("authors", len(authors_out), "homes", len(insts))
    print("REJECTED lineage roll-ups:", sorted(REJECTED))
    json.dump(sorted(REJECTED), open(D / "lineage_rejected.json", "w"), indent=0)
    from collections import Counter
    print(Counter(x["type"] for x in insts.values()))
    for x in rows[:70]:
        print(f'{len(x["A"]["core"]):3} {len(x["A"]["peripheral"]):3} | {len(x["B"]["core"]):3} {len(x["B"]["peripheral"]):3}  {x["type"][:10]:10} {x["name"]}')


if __name__ == "__main__":
    main()
