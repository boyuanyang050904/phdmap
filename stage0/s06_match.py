"""0.2c  Authoritative faculty matching from cached faculty pages.

For each program found by program discovery (data/stage0/programs/*.json) the
listed faculty pages are re-read from the local cache (fetched if missing)
and every relevant OpenAlex author associated with the institution is
name-matched against the page text.  Agent-reported memberships via faculty
profiles (unmatched_core_authors[].program_found + evidence_url) are accepted
only if the author's name also appears on that evidence page.

Output: data/stage0/program_matches.json
"""
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.fetch import fetcher, BlockedByRobots  # noqa: E402
from lib.names import page_text, name_variants, find_name, middle_initials, author_name_list  # noqa: E402
from stage0.program_tool import inst_authors  # noqa: E402

D = ROOT / "data" / "stage0"


def load_page(url, render):
    f = fetcher()
    try:
        r = f.get_rendered(url) if render else f.get(url)
    except BlockedByRobots:
        return None
    return r


def author_names(a):
    return author_name_list(a["name"], a.get("display_name_alternatives", []))


def norm_prog(s):
    return re.sub(r"[^a-z]+", " ", (s or "").lower()).strip()


def person_key(name):
    """'Li‐San Wang' / 'Li-San Wang' / 'Hongzhe Li' -> 'li san|wang' (drops middle initials)."""
    from lib.names import norm
    toks = [t for t in norm(name).replace("-", " ").split() if len(t) > 1 or t in ("x",)]
    if len(toks) < 2:
        return norm(name)
    return toks[0] + "|" + toks[-1]


def merge_people(ms):
    """OpenAlex sometimes splits one person into several author IDs: merge by name."""
    by = {}
    for m in ms:
        k = person_key(m["name"])
        if k not in by:
            by[k] = {**m, "openalex_ids": [m["id"]]}
            continue
        e = by[k]
        e["openalex_ids"].append(m["id"])
        for d, v in m["dirs"].items():
            if d not in e["dirs"] or v["score"] > e["dirs"][d]["score"]:
                e["dirs"][d] = v
        e["is_core"] = e["is_core"] or m["is_core"]
        if m["best_score"] > e["best_score"]:
            e.update({k2: m[k2] for k2 in ("name", "orcid", "best_score")})
    out = list(by.values())
    out.sort(key=lambda m: (-m["is_core"], -m["best_score"]))
    return out


def main():
    out = []
    for path in sorted(glob.glob(str(D / "programs" / "*.json"))):
        d = json.load(open(path))
        inst = d["institution"]
        auths = inst_authors(inst)
        progs = []
        for p in d.get("programs", []):
            matched = {}
            pages = []
            page_texts = []
            for fu in p.get("faculty_list_urls") or []:
                url = fu["url"] if isinstance(fu, dict) else fu
                render = bool(fu.get("render")) if isinstance(fu, dict) else False
                r = load_page(url, render)
                if r is None or not r.ok:
                    pages.append({"url": url, "status": None if r is None else r.status,
                                  "readable": False})
                    continue
                txt = page_text(r.text)
                pages.append({"url": url, "status": r.status, "fetched_at": r.fetched_at,
                              "text_len": len(txt), "readable": len(txt) > 500})
                page_texts.append((url, txt, r.fetched_at))
                for a in auths:
                    if a["id"] in matched:
                        continue
                    m = find_name(txt, name_variants(author_names(a)), middle_initials(author_names(a)))
                    if m:
                        matched[a["id"]] = {"evidence_url": url, "fetched_at": r.fetched_at,
                                            "snippet": m, "via": "faculty_list"}
            # names the agent confirmed by reading the page but that strict matching missed
            # (nicknames, e.g. "Zaida (Zan) Luthey-Schulten"): accept only if the surname
            # appears with a token starting with the first initial within the 3 preceding tokens
            for nm in p.get("matched_authors") or []:
                base = re.sub(r"\s*\[.*$", "", nm).strip()
                a = next((x for x in auths if x["name"] == base and x["id"] not in matched), None)
                if not a:
                    continue
                vs = name_variants([a["name"]])
                for pg_url, pg_txt, pg_at in page_texts:
                    hit = None
                    for f0, l0 in vs:
                        for mm in re.finditer(rf"\b{re.escape(l0)}\b", pg_txt):
                            before = pg_txt[max(0, mm.start() - 60):mm.start()].split()[-3:]
                            if any(t.startswith(f0[0]) for t in before):
                                hit = pg_txt[max(0, mm.start() - 40): mm.end() + 20]
                                break
                        if hit:
                            break
                    if hit:
                        matched[a["id"]] = {"evidence_url": pg_url, "fetched_at": pg_at,
                                            "snippet": hit, "via": "agent_confirmed_surname"}
                        break
            progs.append({**p, "pages": pages, "_matched": matched})
        # memberships found via individual faculty profiles
        for u in d.get("unmatched_core_authors", []) or []:
            pf, ev = u.get("program_found"), u.get("evidence_url")
            if not pf or not ev:
                continue
            tgt = [p for p in progs if norm_prog(pf) in norm_prog(p["program_name"])
                   or norm_prog(p["program_name"]) in norm_prog(pf)]
            if not tgt:
                continue
            r = load_page(ev, False)
            if r is None or not r.ok:
                continue
            txt = page_text(r.text)
            for a in auths:
                if norm_prog(a["name"]) == norm_prog(u["name"]) or u["name"] in author_names(a):
                    if find_name(txt, name_variants(author_names(a)), middle_initials(author_names(a))):
                        for p in tgt:
                            p["_matched"].setdefault(a["id"], {"evidence_url": ev, "fetched_at": r.fetched_at,
                                                              "snippet": None, "via": "faculty_profile"})
        A = {a["id"]: a for a in auths}
        for p in progs:
            ms = []
            for aid, ev in p.pop("_matched").items():
                a = A[aid]
                ms.append({"id": aid, "name": a["name"], "orcid": a.get("orcid"),
                           "dirs": {k: {"tier": v["tier"], "score": v["score"], "n_works": v["n_works"],
                                        "n_methods": v["n_methods"], "subtopics": v["subtopic_counts"]}
                                    for k, v in a["dirs"].items()},
                           "best_score": max(v["score"] for v in a["dirs"].values()),
                           "is_core": any(v["tier"] == "core" for v in a["dirs"].values()),
                           **ev})
            p["matched"] = merge_people(ms)
        out.append({"institution": inst, "file": Path(path).name, "grants_phd": d.get("grants_phd"),
                    "institution_kind": d.get("institution_kind"),
                    "grants_phd_evidence": d.get("grants_phd_evidence"),
                    "problems": d.get("problems", []), "programs": progs,
                    "n_relevant_authors": len(auths)})
    json.dump(out, open(D / "program_matches.json", "w"), indent=1)
    for o in out:
        print(o["institution"], [(p["program_name"][:40], sum(m["is_core"] for m in p["matched"]),
                                  len(p["matched"])) for p in o["programs"]])


if __name__ == "__main__":
    main()
