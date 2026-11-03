"""Fill title / lab URL for the TOP faculty from their official profile pages, then set
the new-assistant-professor flag.  Facts only from fetched pages (quote kept).

usage: python3 stage1/s12b_enrich.py PROGRAM_ID [...]
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup  # noqa: E402
from lib.fetch import fetcher, BlockedByRobots  # noqa: E402
from stage1.s12_faculty import CUTOFF_YEAR  # noqa: E402

D1 = ROOT / "data" / "stage1"
TITLE_RE = re.compile(r"((?:Distinguished |Associate |Assistant |Full |Adjunct |Research |Clinical |Visiting )*"
                      r"Professor(?: of [A-Z][\w&,\- ]{2,80})?|(?:Senior )?Lecturer|Investigator|"
                      r"(?:Associate |Assistant )?Member)", re.I)
LAB_RE = re.compile(r"\blab\b|laboratory|research group|lab website|group website|personal website", re.I)


def from_profile(url):
    try:
        r = fetcher().get(url)
    except BlockedByRobots:
        return None, None, None
    if not r.ok:
        return None, None, None
    soup = BeautifulSoup(r.text, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    title = None
    for line in soup.get_text("\n").splitlines():
        line = " ".join(line.split())
        if 3 < len(line) < 160:
            m = TITLE_RE.search(line)
            if m and "professor" in m.group(0).lower() or (m and len(line) < 60):
                title = {"value": line, "source_url": url, "fetched_at": r.fetched_at, "quote": line}
                break
    lab = None
    for a in soup.find_all("a", href=True):
        t = a.get_text(" ", strip=True)
        if LAB_RE.search(t) and not re.search(r"labs? (and|&) centers|core lab", t, re.I):
            href = urljoin(r.final_url, a["href"])
            if href.startswith("http"):
                lab = {"value": href, "source_url": url, "fetched_at": r.fetched_at, "quote": t[:120]}
                break
    return title, lab, r.fetched_at


def first_last_author_year_at_school(aid, school_id):
    """Earliest last/corresponding-author OpenAlex work whose byline (for this author)
    lists the school.  Restricting to the school avoids merged same-name profiles."""
    from stage1.s12_faculty import oa, role, on_school_byline
    for w, _, _ in oa.paginate("/works", per_page=200, filter=f"author.id:{aid.rsplit('/', 1)[-1]}",
                               select="id,publication_year,authorships", sort="publication_year:asc"):
        if role(w, aid)[0] == "last/corresponding" and on_school_byline(w, aid, school_id):
            return w.get("publication_year")
    return None


def affiliation_from_recent(aid, school_id):
    """Spec: compare the byline of the most recent papers with the program faculty page.
    Uses the 2 most recent last/corresponding-author works in the 3-year window."""
    from stage1.s12_faculty import oa, role, on_school_byline, WINDOW_FROM, TOPICS, work_text
    ws = []
    for w, url, at in oa.paginate("/works", per_page=200,
                                  filter=f"author.id:{aid.rsplit('/', 1)[-1]},from_publication_date:{WINDOW_FROM}",
                                  select="id,title,publication_date,authorships,abstract_inverted_index",
                                  sort="publication_date:desc"):
        # only works in the person's relevant research line (guards against merged namesakes)
        if role(w, aid)[0] == "last/corresponding" and any(rx.search(work_text(w)) for _, rx in TOPICS.values()):
            _, _, au = role(w, aid)
            ws.append({"id": w["id"], "title": w.get("title"), "date": w.get("publication_date"),
                       "institutions": [i["display_name"] for i in (au or {}).get("institutions", [])],
                       "lists_school": on_school_byline(w, aid, school_id), "source_url": url, "fetched_at": at})
        if len(ws) >= 2:
            break
    if not ws:
        return {"status": "unknown", "recent_works": [], "note": "no last/corresponding-author work in window"}
    ok = any(w["lists_school"] for w in ws)
    return {"status": "consistent" if ok else "possibly_moved", "recent_works": ws,
            "rule": "possibly_moved if none of the 2 most recent topic-relevant last/corresponding-author "
                    "works lists the school"}


def main(pids):
    for pid in pids:
        p = D1 / "faculty" / f"{pid}.json"
        d = json.load(open(p))
        prog = json.load(open(D1 / "programs" / f"{pid}.json"))
        flist = {f["name"]: f for f in prog["faculty_list"]["faculty"]}
        for x in d["top"]:
            if x.get("openalex_id"):
                x["affiliation_recent"] = affiliation_from_recent(x["openalex_id"], d["school_institution_id"])
            src = flist.get(x["name"], {})
            # title/lab from the faculty list (official page) if present
            if src.get("title"):
                x["title_field"] = {"value": src["title"], "source_url": src.get("source_url"),
                                    "quote": src["title"]}
            if src.get("lab_url"):
                x["lab_field"] = {"value": src["lab_url"], "source_url": src.get("source_url")}
            if (not x.get("title_field") or not x.get("lab_field")) and src.get("profile_url"):
                t, lab, _ = from_profile(src["profile_url"])
                x.setdefault("title_field", t)
                if not x.get("lab_field"):
                    x["lab_field"] = lab
            tv = ((x.get("title_field") or {}).get("value") or "").lower()
            if not tv:
                x["new_assistant_professor"] = {"value": None, "note": "official title not found"}
            else:
                is_ap = "assistant professor" in tv and not re.search(r"adjunct|research|clinical|visiting", tv)
                fy = x.get("first_last_author_year")
                if is_ap:
                    fy = first_last_author_year_at_school(x["openalex_id"], d["school_institution_id"])
                    x["first_last_author_year"] = fy
                x["new_assistant_professor"] = {
                    "value": bool(is_ap and fy is not None and fy >= CUTOFF_YEAR),
                    "title": (x.get("title_field") or {}).get("value"),
                    "title_source_url": (x.get("title_field") or {}).get("source_url"),
                    "first_last_author_year": fy, "cutoff_year": CUTOFF_YEAR,
                    "rule": "official title is (tenure-track) Assistant Professor AND first OpenAlex "
                            f"last/corresponding-author work listing this school >= {CUTOFF_YEAR}"}
        json.dump(d, open(p, "w"), indent=1)
        print(pid, [(x["name"], (x.get("title_field") or {}).get("value"), x["new_assistant_professor"]["value"],
                     (x.get("affiliation_recent") or {}).get("status")) for x in d["top"]])


if __name__ == "__main__":
    main(sys.argv[1:])
