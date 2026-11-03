"""Validate stage-1 program files: every non-null FIELD's quote must occur in the cached
text of its source_url (whitespace/case-insensitive). Faculty names must occur on the
faculty-list page(s). Prints errors; exit 1 if any.

usage: python3 stage1/validate.py FILE [FILE...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup  # noqa: E402
from lib.fetch import fetcher, BlockedByRobots  # noqa: E402
from lib.names import norm  # noqa: E402

_cache = {}


def page_plain(url, render=False):
    key = (url, render)
    if key not in _cache:
        f = fetcher()
        try:
            r = f.get_rendered(url) if render else f.get(url)
            html = r.text if r.ok else ""
        except BlockedByRobots:
            html = ""
        if html.lstrip().startswith("%PDF") or url.lower().endswith(".pdf"):
            txt = html
        else:
            soup = BeautifulSoup(html, "lxml")
            for t in soup(["script", "style", "noscript"]):
                t.decompose()
            txt = soup.get_text(" ", strip=True)
        _cache[key] = re.sub(r"\s+", " ", txt).lower()
    return _cache[key]


def squash(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def check_field(path, fld, errs, render_urls=()):
    if not isinstance(fld, dict) or "value" not in fld:
        errs.append(f"{path}: not a FIELD object")
        return
    if fld["value"] is None:
        if not fld.get("note"):
            errs.append(f"{path}: null value without note")
        return
    for k in ("source_url", "fetched_at", "quote"):
        if not fld.get(k):
            errs.append(f"{path}: missing {k}")
            return
    txt = page_plain(fld["source_url"], fld["source_url"] in render_urls)
    if not txt:
        txt = page_plain(fld["source_url"], True)
    q = squash(fld["quote"])
    if q not in txt:
        # tolerate curly quotes / dashes differences
        q2 = q.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
        t2 = txt.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
        if q2 not in t2:
            errs.append(f"{path}: quote not found on {fld['source_url']}: {fld['quote'][:80]!r}")


def validate(p):
    d = json.load(open(p))
    errs = []
    simple = ["program_url", "deadline", "priority_deadline", "application_fee", "fee_waiver", "gre_policy",
              "letters_required", "application_system_url", "admissions_mode", "contact_faculty_advice",
              "stipend", "guaranteed_years", "pr_domestic", "t32_citizen_pr_only"]
    for k in simple:
        check_field(k, d.get(k), errs)
    for k, v in (d.get("toefl") or {}).items():
        check_field("toefl." + k, v, errs)
    fl = d.get("faculty_list") or {}
    pages = " ".join(norm(page_plain(u, fl.get("render", False))) for u in fl.get("source_urls", []))
    missing = [f["name"] for f in fl.get("faculty", []) if norm(f["name"]) and norm(f["name"]) not in pages]
    if missing:
        errs.append(f"faculty names not found on faculty pages ({len(missing)}): {missing[:8]}")
    print(f"{p}: {len(errs)} problems; faculty listed: {len(fl.get('faculty', []))}")
    for e in errs:
        print("   ", e)
    return not errs


if __name__ == "__main__":
    ok = all([validate(p) for p in sys.argv[1:]])
    sys.exit(0 if ok else 1)
