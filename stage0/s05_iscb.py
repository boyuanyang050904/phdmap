"""0.3  ISCB degree-program list -> US PhD programs.

The list at https://www.iscb.org/nucleus/education-and-training-resources/degree-and-certificate-programs-in-bioinformatics
is an iframe served from https://transition.iscb.org/cms_addon/univ_programs/displaytable.php
whose robots.txt is "User-agent: * / Disallow: /", so it is NOT fetched automatically.

If the user saves that iframe page from a browser to data/manual/iscb_displaytable.html,
this script parses it (any HTML table) and keeps US PhD rows.
The robots-allowed endorsement page is parsed for endorsed programs.

Output: data/stage0/iscb_us_phd.json  {status, source_url, fetched_at|saved_at, rows:[...]}
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup  # noqa: E402
from lib.fetch import fetcher, BlockedByRobots  # noqa: E402

LIST_PAGE = ("https://www.iscb.org/nucleus/education-and-training-resources/"
             "degree-and-certificate-programs-in-bioinformatics")
IFRAME = "https://transition.iscb.org/cms_addon/univ_programs/displaytable.php"
ENDORSE = ("https://www.iscb.org/nucleus/education-and-training-resources/"
           "iscb-degree-granting-endorsement-program")
MANUAL = ROOT / "data" / "manual" / "iscb_displaytable.html"
OUT = ROOT / "data" / "stage0" / "iscb_us_phd.json"
US_RE = re.compile(r"\b(USA|U\.S\.A?\.?|United States)\b", re.I)
PHD_RE = re.compile(r"\b(Ph\.?\s?D|doctor|doctoral)\b", re.I)


def parse_tables(html):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        hdr = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        for tr in trs[1:]:
            cells = tr.find_all(["td", "th"])
            vals = [c.get_text(" ", strip=True) for c in cells]
            links = [a["href"] for a in tr.find_all("a", href=True)]
            rec = dict(zip(hdr, vals)) if len(hdr) == len(vals) else {"cells": vals}
            rec["_links"] = links
            line = " | ".join(vals)
            if US_RE.search(line) and PHD_RE.search(line):
                rows.append(rec)
    return rows


def main():
    f = fetcher()
    out = {"list_page": LIST_PAGE, "iframe_url": IFRAME}
    # robots status of the iframe host (evidence for the report)
    out["iframe_allowed_by_robots"] = f.allowed(IFRAME)
    r = f.get(ENDORSE)
    soup = BeautifulSoup(r.text, "lxml")
    txt = soup.get_text("\n", strip=True)
    seg = txt[txt.find("Endorsed Degree-Granting Programs"):]
    endorsed = [l for l in seg.splitlines()[1:40] if re.search(r"program|degree|M\.S\.|Ph\.?D|Master|Bachelor", l, re.I)]
    out["endorsement_page"] = {"source_url": ENDORSE, "fetched_at": r.fetched_at,
                               "endorsed_lines": endorsed,
                               "us_phd_endorsed": [l for l in endorsed if PHD_RE.search(l) and US_RE.search(l)]}
    if MANUAL.exists():
        rows = parse_tables(MANUAL.read_text(errors="replace"))
        saved = datetime.fromtimestamp(os.path.getmtime(MANUAL), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.update(status="parsed_user_saved_copy", source_url=IFRAME, saved_at=saved, rows=rows)
    elif out["iframe_allowed_by_robots"]:
        try:
            rr = f.get(IFRAME)
            out.update(status="fetched", source_url=IFRAME, fetched_at=rr.fetched_at,
                       rows=parse_tables(rr.text))
        except BlockedByRobots:
            out.update(status="blocked_by_robots", rows=[])
    else:
        out.update(status="blocked_by_robots", rows=[],
                   note="transition.iscb.org/robots.txt disallows all agents; save the iframe page "
                        "manually to data/manual/iscb_displaytable.html and rerun.")
    json.dump(out, open(OUT, "w"), indent=1)
    print(out["status"], len(out.get("rows", [])), "US PhD rows;", "endorsed US PhD:",
          out["endorsement_page"]["us_phd_endorsed"])


if __name__ == "__main__":
    main()
