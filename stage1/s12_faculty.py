"""Stage 1: score every faculty member of a program by relevance of their last-3-year
OpenAlex works to the six interests, keep the top 5-8, attach evidence.

usage: python3 stage1/s12_faculty.py PROGRAM_ID [PROGRAM_ID ...]
reads  data/stage1/programs/<id>.json (faculty_list from the official page) and
       data/stage1/selection.json (program_id -> school OpenAlex institution id)
writes data/stage1/faculty/<id>.json

Relevance per work = topic weight (regex on title+abstract, per subtopic)
                     x methods factor (1.0 if methods/computational else 0.4)
                     x role factor (last/corresponding 1.0, first 0.6, middle 0.25)
Faculty direction: A / B / A+B from per-direction score shares (>=30%).
'Possibly moved' (可能已换单位): none of the institutions on the author's most recent
last/corresponding-author work (within the 3-year window) is the school (lineage-aware),
and the OpenAlex last_known_institutions don't include it either.
New assistant professor: official title contains "Assistant Professor" (not adjunct/
research/clinical) AND first last-author OpenAlex work >= CUTOFF_YEAR (5-year window).
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import openalex as oa  # noqa: E402
from lib.names import norm, name_variants  # noqa: E402
from stage0.s02_authors import abstract, methods_flag  # noqa: E402

D1 = ROOT / "data" / "stage1"
TODAY = date.today()
WINDOW_FROM = (TODAY - timedelta(days=3 * 365)).isoformat()
CUTOFF_YEAR = TODAY.year - 5      # "近 5 年内开组"
TOP_MAX, TOP_MIN, MIN_SCORE = 8, 5, 0.8

PROT = r"(protein|peptide|enzyme|binder|antibod|nanobod|miniprotein|amino[- ]acid)"
TOPICS = {
    "A1": ("A", re.compile(r"perturb-?seq|crop-?seq|crisp-?seq|single[- ]cell crispr|crispr screen|"
                           r"pooled (genetic |crispr )?screen|perturbation (response|effect|prediction|model)|"
                           r"genetic perturbation", re.I)),
    "A2": ("A", re.compile(r"causal (network|discovery|graph|structure)|gene regulatory network|"
                           r"regulatory network inference|structural causal|directed acyclic graph|"
                           r"network (inference|reconstruction)|causal (gene|protein|trait)", re.I)),
    "A3": ("A", re.compile(r"\bgwas\b|genome-wide association|summary statistic|mendelian randomi[sz]ation|"
                           r"polygenic|fine-?mapping|heritability|genetic correlation|\btwas\b|"
                           r"transcriptome-wide association|colocali[sz]ation|statistical genetic", re.I)),
    "B4": ("B", re.compile(r"(antibod|nanobod|\bvhh\b)[^.]{0,120}(design|engineer|affinity|optimi|maturation|"
                           r"language model|structure|developab|generat)|affinity maturation|"
                           r"antibody[- ]antigen", re.I)),
    "B5": ("B", re.compile(PROT + r"[^.]{0,80}(design|generat|diffusion|language model|inverse folding|"
                           r"engineering|sequence space)|protein language model|inverse folding|"
                           r"de novo (designed )?(protein|binder|enzyme)|designed (protein|binder)s?|"
                           r"(design|generat)\w*[^.]{0,40}" + PROT, re.I)),
    "B6": ("B", re.compile(r"protein structure prediction|structure prediction|alphafold|rosettafold|esmfold|"
                           r"protein[- ]protein (interaction|docking|interface|complex)|protein complex|"
                           r"(peptide|protein)[- ](protein |peptide )?docking|binding interface|"
                           r"interface prediction|multimer", re.I)),
}
APPLIED_FACTOR = 0.15
INST_SELECT = "id,display_name,works_count,last_known_institutions,affiliations,orcid,summary_stats"


def work_text(w):
    return (w.get("title") or "") + ". " + abstract(w)


def is_methods(t):
    return methods_flag(t)


def on_school_byline(w, aid, school_id):
    _, _, au = role(w, aid)
    return any(i.get("id") == school_id or school_id in (i.get("lineage") or [])
               for i in (au or {}).get("institutions", []))


def role(w, aid):
    n = len(w.get("authorships", []))
    for a in w.get("authorships", []):
        if (a.get("author") or {}).get("id") == aid:
            if a.get("author_position") == "last" or a.get("is_corresponding") or n == 1:
                return "last/corresponding", 1.0, a
            if a.get("author_position") == "first":
                return "first", 0.6, a
            return "middle", 0.25, a
    return None, 0.0, None


def resolve_author(name, inst_id, homes_by_name):
    """OpenAlex author for a faculty name at an institution. Prefers stage-0 authors."""
    key = norm(name)
    for a in homes_by_name.get(key, []):
        return a["id"], "stage0"
    toks = [t for t in re.sub(r"\(.*?\)", " ", name).replace(",", " ").split()
            if not re.fullmatch(r"(ph\.?d\.?|m\.?d\.?|jr\.?|sr\.?|iii?|iv)", t, re.I)]
    q = " ".join(toks)
    data, url, at = oa.get("/authors", search=q, filter=f"affiliations.institution.lineage:{inst_id.rsplit('/', 1)[-1]}",
                           select=INST_SELECT, per_page=10)
    cands = data.get("results", [])
    if not cands:
        return None, url
    fv = name_variants([name])
    good = [c for c in cands if name_variants([c["display_name"]]) & fv] or cands[:1]
    good.sort(key=lambda c: -(c.get("works_count") or 0))
    return good[0]["id"], url


def inst_ok(inst, school_id, school_lineage_ids):
    return inst.get("id") == school_id or school_id in (inst.get("lineage") or []) or inst.get("id") in school_lineage_ids


def main(pids):
    sel = json.load(open(D1 / "selection.json"))
    H = json.load(open(ROOT / "data" / "stage0" / "homes.json"))
    homes_by_name = {}
    for a in H["authors"].values():
        homes_by_name.setdefault(norm(a["name"]), []).append(a)
    (D1 / "faculty").mkdir(parents=True, exist_ok=True)
    for pid in pids:
        prog = json.load(open(D1 / "programs" / f"{pid}.json"))
        school_id = sel[pid]["institution_id"]
        sid = school_id.rsplit("/", 1)[-1]
        out = []
        for fac in prog["faculty_list"]["faculty"]:
            # restrict homes match to authors associated with this school
            hb = {k: [a for a in v if any(h["id"] == school_id for h in a["homes"])]
                  for k, v in homes_by_name.items() if k == norm(fac["name"])}
            aid, how = resolve_author(fac["name"], school_id, hb)
            if not aid:
                out.append({"name": fac["name"], "openalex_id": None, "score": 0, "note": "no OpenAlex author found",
                            "lookup_url": how})
                continue
            short = aid.rsplit("/", 1)[-1]
            ents, ent_url, ent_at = oa.get(f"/authors/{short}", select=INST_SELECT)
            works = []
            for w, wurl, wat in oa.paginate("/works", per_page=200,
                                            filter=f"author.id:{short},from_publication_date:{WINDOW_FROM}",
                                            select="id,doi,title,publication_year,publication_date,type,"
                                                   "abstract_inverted_index,authorships,primary_location"):
                w["_source_url"], w["_fetched_at"] = wurl, wat
                works.append(w)
            # count only works on which this author's byline lists the school (guards against
            # OpenAlex merging two people with the same name); fall back to all works if none
            here = [w for w in works if on_school_byline(w, aid, school_id)]
            used = here if here else works
            scored, sA, sB = [], 0.0, 0.0
            for w in used:
                if re.match(r"\s*(abstract|poster|session)\s*\w*\d+\s*:", w.get("title") or "", re.I) or \
                        w.get("type") in ("paratext", "erratum", "retraction", "letter", "editorial"):
                    continue          # conference-abstract / non-research records
                t = work_text(w)
                hits = [k for k, (_, rx) in TOPICS.items() if rx.search(t)]
                if not hits:
                    continue
                rname, rw, _ = role(w, aid)
                mf = 1.0 if is_methods(t) else APPLIED_FACTOR
                s = rw * mf * (1 + 0.25 * (len(hits) - 1))
                da = any(TOPICS[h][0] == "A" for h in hits)
                db = any(TOPICS[h][0] == "B" for h in hits)
                sA += s if da else 0
                sB += s if db else 0
                scored.append({"id": w["id"], "doi": w.get("doi"), "title": w.get("title"),
                               "year": w.get("publication_year"), "type": w.get("type"),
                               "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                               "landing_url": w.get("doi") or ((w.get("primary_location") or {}).get("landing_page_url")) or w["id"],
                               "subtopics": hits, "methods": mf == 1.0, "role": rname, "score": round(s, 2),
                               "abstract": abstract(w)[:700],
                               "source_url": w["_source_url"], "fetched_at": w["_fetched_at"]})
            # person score = sum of the 10 best works (volume of applied papers is not rewarded)
            best = sorted(scored, key=lambda x: -x["score"])[:10]
            ids = {b["id"] for b in best}
            sA = sum(b["score"] for b in best if any(TOPICS[h][0] == "A" for h in b["subtopics"]))
            sB = sum(b["score"] for b in best if any(TOPICS[h][0] == "B" for h in b["subtopics"]))
            total = sum(b["score"] for b in best)
            dirs = [d for d, v in (("A", sA), ("B", sB)) if total and v / total >= 0.3]
            # affiliation check on most recent last/corresponding work
            lc = sorted([w for w in works if role(w, aid)[0] == "last/corresponding"],
                        key=lambda w: w.get("publication_date") or "", reverse=True)
            recent_insts = []
            if lc:
                _, _, au = role(lc[0], aid)
                recent_insts = [{"id": i["id"], "name": i["display_name"], "lineage": i.get("lineage", [])}
                                for i in (au or {}).get("institutions", [])]
            lki = ents.get("last_known_institutions") or []
            at_school = any(inst_ok(i, school_id, ()) for i in recent_insts) or \
                any(inst_ok(i, school_id, ()) for i in lki)
            out.append({
                "name": fac["name"], "title": fac.get("title"), "profile_url": fac.get("profile_url"),
                "lab_url": fac.get("lab_url"), "faculty_source_url": fac.get("source_url"),
                "openalex_id": aid, "openalex_match": how, "openalex_name": ents.get("display_name"),
                "openalex_url": ent_url, "openalex_fetched_at": ent_at,
                "works_in_window": len(works), "works_at_school": len(here),
                "score_basis": "works with school on byline" if here else "all works (none list the school)",
                "score": round(total, 2),
                "score_A": round(sA, 2), "score_B": round(sB, 2), "direction": "+".join(dirs) or None,
                "top_works": sorted(scored, key=lambda x: (-x["score"], -(x["year"] or 0)))[:6],
                "affiliation_check": {
                    "recent_last_author_work": lc[0]["id"] if lc else None,
                    "recent_work_institutions": [i["name"] for i in recent_insts],
                    "last_known_institutions": [i["display_name"] for i in lki],
                    "matches_school": at_school if (recent_insts or lki) else None},
            })
        out.sort(key=lambda x: -x["score"])
        top = [x for x in out if x["score"] >= MIN_SCORE][:TOP_MAX]
        if len(top) < TOP_MIN:
            top = [x for x in out if x["score"] > 0][:TOP_MIN]
        # first last-author year for assistant professors (or unknown titles) among the top
        for x in top:
            t = (x.get("title") or "").lower()
            if x["openalex_id"] and ("assistant professor" in t or not t):
                first = None
                for w, _, _ in oa.paginate("/works", per_page=200,
                                           filter=f"author.id:{x['openalex_id'].rsplit('/', 1)[-1]}",
                                           select="id,publication_year,authorships", sort="publication_year:asc"):
                    if role(w, x["openalex_id"])[0] == "last/corresponding":
                        first = w.get("publication_year")
                        break
                x["first_last_author_year"] = first
        json.dump({"program_id": pid, "school_institution_id": school_id, "window_from": WINDOW_FROM,
                   "n_faculty": len(out), "top": top, "all_scores": [
                       {k: x.get(k) for k in ("name", "openalex_id", "score", "score_A", "score_B", "note")}
                       for x in out]},
                  open(D1 / "faculty" / f"{pid}.json", "w"), indent=1)
        print(pid, "faculty", len(out), "top", [(x["name"], x["score"]) for x in top])


if __name__ == "__main__":
    main(sys.argv[1:])
