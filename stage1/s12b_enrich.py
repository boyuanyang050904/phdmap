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


def main(pids):
    for pid in pids:
        p = D1 / "faculty" / f"{pid}.json"
        d = json.load(open(p))
        prog = json.load(open(D1 / "programs" / f"{pid}.json"))
        flist = {f["name"]: f for f in prog["faculty_list"]["faculty"]}
        for x in d["top"]:
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
                if is_ap and fy is None:
                    from stage1.s12_faculty import oa, role  # lazy
                    for w, _, _ in oa.paginate("/works", per_page=200,
                                               filter=f"author.id:{x['openalex_id'].rsplit('/', 1)[-1]}",
                                               select="id,publication_year,authorships", sort="publication_year:asc"):
                        if role(w, x["openalex_id"])[0] == "last/corresponding":
                            fy = w.get("publication_year")
                            break
                    x["first_last_author_year"] = fy
                x["new_assistant_professor"] = {
                    "value": bool(is_ap and fy is not None and fy >= CUTOFF_YEAR),
                    "title": (x.get("title_field") or {}).get("value"),
                    "title_source_url": (x.get("title_field") or {}).get("source_url"),
                    "first_last_author_year": fy, "cutoff_year": CUTOFF_YEAR,
                    "rule": "official title is (tenure-track) Assistant Professor AND first OpenAlex "
                            f"last/corresponding-author work >= {CUTOFF_YEAR}"}
        json.dump(d, open(p, "w"), indent=1)
        print(pid, [(x["name"], (x.get("title_field") or {}).get("value"), x["new_assistant_professor"]["value"])
                    for x in d["top"]])


if __name__ == "__main__":
    main(sys.argv[1:])
