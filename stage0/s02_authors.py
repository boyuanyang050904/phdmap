"""0.1b  Aggregate US corresponding / last authors per direction.

Input : data/stage0/works_{A,B}.jsonl
Output: data/stage0/authors_{A,B}.json  (dict keyed by OpenAlex author id)

Role rule: an authorship counts if author_position == 'last' (or the work has a
single author) OR is_corresponding is true, AND that authorship lists >=1 US
institution.  Each work gets a heuristic `methods` flag from its title/abstract
(develops a method / model / tool, or uses ML / statistical modelling), so
purely applied papers can be down-weighted.  Works with >50 authors
(consortium papers) get weight 0.5.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "stage0"

METHOD_RE = re.compile(
    r"\b(we|here we|this study|this work|this paper)\s+(develop|propose|introduce|present|describe|"
    r"design|build|create|report)\w*\b[^.]{0,120}?\b(method|framework|model|tool|approach|algorithm|"
    r"package|pipeline|software|estimator|test|strategy|platform|network|architecture|benchmark)",
    re.I)
COMP_RE = re.compile(
    r"\b(deep learning|machine learning|neural network|language model|diffusion model|generative|"
    r"bayesian|statistical (method|framework|model)|computational (method|framework|model|approach|tool)|"
    r"algorithm|transformer|graph neural|variational|probabilistic model|benchmark)", re.I)


def abstract(w):
    inv = w.get("abstract_inverted_index") or {}
    pos = []
    for word, idx in inv.items():
        for i in idx:
            pos.append((i, word))
    return " ".join(wd for _, wd in sorted(pos))


def methods_flag(text):
    return bool(METHOD_RE.search(text)) or len(COMP_RE.findall(text)) >= 2


def main():
    for d in "AB":
        authors = {}
        for line in open(D / f"works_{d}.jsonl"):
            w = json.loads(line)
            text = (w.get("title") or "") + ". " + abstract(w)
            mflag = methods_flag(text)
            auths = w["authorships"]
            n = len(auths)
            weight = 0.5 if n > 50 else 1.0
            subs = sorted({m.split("#")[0] for m in w["matched"]})
            for a in auths:
                last = a.get("author_position") == "last" or n == 1
                corr = bool(a.get("is_corresponding"))
                if not (last or corr):
                    continue
                us_inst = [i for i in a.get("institutions", []) if i.get("country_code") == "US"]
                if not us_inst or not a.get("author", {}).get("id"):
                    continue
                aid = a["author"]["id"]
                rec = authors.setdefault(aid, {
                    "id": aid, "name": a["author"]["display_name"],
                    "orcid": a["author"].get("orcid"), "raw_names": Counter(),
                    "works": [], "institutions": defaultdict(lambda: {"n": 0, "years": []}),
                    "raw_affiliations": Counter(),
                })
                rec["raw_names"][a.get("raw_author_name") or ""] += 1
                for ra in a.get("raw_affiliation_strings", [])[:3]:
                    rec["raw_affiliations"][ra] += 1
                for i in us_inst:
                    e = rec["institutions"][i["id"]]
                    e.update({"name": i["display_name"], "type": i.get("type"),
                              "lineage": i.get("lineage", []), "ror": i.get("ror")})
                    e["n"] += 1
                    e["years"].append(w["publication_year"])
                rec["works"].append({
                    "id": w["id"], "doi": w.get("doi"), "title": w.get("title"),
                    "year": w["publication_year"], "date": w.get("publication_date"),
                    "type": w["type"], "cites": w.get("cited_by_count", 0),
                    "subtopics": subs, "methods": mflag, "weight": weight,
                    "role": "last" if last else "corresponding", "n_authors": n,
                    "source_url": w["source_urls"][0], "fetched_at": w["fetched_at"],
                    "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                })
        out = {}
        for aid, r in authors.items():
            ws = r["works"]
            r["n_works"] = len(ws)
            r["n_methods"] = sum(x["methods"] for x in ws)
            r["score"] = round(sum(x["weight"] * (1.0 if x["methods"] else 0.4) for x in ws), 2)
            r["subtopic_counts"] = dict(Counter(s for x in ws for s in x["subtopics"]))
            r["last_year"] = max(x["year"] for x in ws)
            r["raw_names"] = dict(r["raw_names"])
            r["raw_affiliations"] = [k for k, _ in r["raw_affiliations"].most_common(5)]
            r["institutions"] = dict(r["institutions"])
            out[aid] = r
        json.dump(out, open(D / f"authors_{d}.json", "w"))
        sc = Counter()
        for r in out.values():
            sc["n>=1"] += 1
            sc["score>=1"] += r["score"] >= 1
            sc["score>=2"] += r["score"] >= 2
            sc["methods>=1"] += r["n_methods"] >= 1
            sc["methods>=2"] += r["n_methods"] >= 2
        print(d, dict(sc))


if __name__ == "__main__":
    main()
