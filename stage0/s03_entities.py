"""0.1c / 0.2a  Fetch OpenAlex author + institution entities.

* authors with >=1 methods work (either direction): last_known_institutions,
  affiliations-by-year, summary_stats, works_count
* every institution seen on those authors: type, geo, lineage,
  associated_institutions (parent/child/related), name alternatives
Output: data/stage0/author_entities.json, data/stage0/institutions.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import openalex as oa  # noqa: E402

D = ROOT / "data" / "stage0"


def short(i):
    return i.rsplit("/", 1)[-1]


def batch_get(endpoint, ids, select):
    out = {}
    ids = sorted(set(ids))
    for k in range(0, len(ids), 50):
        chunk = ids[k:k + 50]
        data, url, at = oa.get(endpoint, filter="openalex:" + "|".join(short(i) for i in chunk),
                               per_page=50, select=select)
        for it in data["results"]:
            it["_source_url"] = url
            it["_fetched_at"] = at
            out[it["id"]] = it
    return out


def main():
    aids = set()
    for d in "AB":
        A = json.load(open(D / f"authors_{d}.json"))
        aids |= {a for a, r in A.items() if r["n_methods"] >= 1}
    print("authors to fetch", len(aids))
    ents = batch_get("/authors", aids,
                     "id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,"
                     "summary_stats,last_known_institutions,affiliations")
    json.dump(ents, open(D / "author_entities.json", "w"))
    print("authors fetched", len(ents))

    iids = set()
    for d in "AB":
        A = json.load(open(D / f"authors_{d}.json"))
        for a, r in A.items():
            if a in aids:
                iids |= set(r["institutions"])
    for e in ents.values():
        for i in e.get("last_known_institutions") or []:
            iids.add(i["id"])
        for af in e.get("affiliations") or []:
            if (af.get("institution") or {}).get("country_code") == "US" and max(af.get("years") or [0]) >= 2022:
                iids.add(af["institution"]["id"])
    print("institutions to fetch", len(iids))
    inst = batch_get("/institutions", iids,
                     "id,display_name,display_name_alternatives,display_name_acronyms,ror,"
                     "country_code,type,geo,lineage,associated_institutions,homepage_url")
    # parents/related referenced via associated_institutions
    extra = set()
    for i in inst.values():
        for ai in i.get("associated_institutions") or []:
            if ai["id"] not in inst:
                extra.add(ai["id"])
        for l in i.get("lineage") or []:
            if l not in inst:
                extra.add(l)
    inst.update(batch_get("/institutions", extra,
                          "id,display_name,display_name_alternatives,display_name_acronyms,ror,"
                          "country_code,type,geo,lineage,associated_institutions,homepage_url"))
    json.dump(inst, open(D / "institutions.json", "w"))
    print("institutions fetched", len(inst))


if __name__ == "__main__":
    main()
