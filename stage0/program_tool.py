"""Helper CLI for program discovery (stage 0.2).

  python3 stage0/program_tool.py fetch URL [--render]
      fetch via the project fetcher (cache + robots.txt + rate limit); print
      status, title, size and the page's links that look like program /
      faculty / admissions links.
  python3 stage0/program_tool.py match "INSTITUTION NAME" URL [URL ...] [--render]
      show which relevant OpenAlex authors (directions A/B) associated with
      that institution appear by name on the page(s).
  python3 stage0/program_tool.py authors "INSTITUTION NAME"
      list relevant authors associated with the institution.
  python3 stage0/program_tool.py text URL [--render] [--grep REGEX]
      print the visible text (optionally only lines matching REGEX).
  python3 stage0/program_tool.py homepage "INSTITUTION NAME"
      OpenAlex homepage_url of the institution (a starting point without web search).
  python3 stage0/program_tool.py find START_URL REGEX [--depth N] [--max M]
      breadth-first walk over links on the same site (registered domain), following
      navigation-like links (graduate/program/phd/academics/departments/faculty/people...),
      printing every link whose text or URL matches REGEX.  Default depth 2, max 30 pages.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup  # noqa: E402
from lib.fetch import fetcher, BlockedByRobots, HostUnreachable, BotProtected  # noqa: E402
from lib.names import page_text, name_variants, find_name, middle_initials, author_name_list  # noqa: E402

D = ROOT / "data" / "stage0"
KW = re.compile(r"facult|people|member|program|phd|ph\.d|doctoral|graduate|admission|apply|track|"
                r"curricul|training|research|labs?\b|directory|mentor", re.I)


def get(url, render=False):
    f = fetcher()
    try:
        r = f.get_rendered(url) if render else f.get(url)
    except HostUnreachable:
        print(f"UNREACHABLE (host does not resolve / TLS or proxy error; robots.txt not retrievable, so not fetched): {url}")
        sys.exit(3)
    except BotProtected:
        print(f"BOT-PROTECTED (site refuses automated clients with 401/403; not rendered either): {url}")
        sys.exit(4)
    except BlockedByRobots:
        print(f"BLOCKED by robots.txt: {url}")
        sys.exit(2)
    return r


_I = None


def related_edu(inst_id):
    """OpenAlex associated_institutions (related/parent) of type education."""
    global _I
    if _I is None:
        _I = json.load(open(D / "institutions.json"))
    i = _I.get(inst_id) or {}
    return [x["display_name"] for x in (i.get("associated_institutions") or [])
            if x.get("type") == "education" and x.get("relationship") in ("related", "parent")]


def inst_authors(name):
    """Relevant authors associated with an institution: OpenAlex home, unit,
    last_known_institutions, or (for authors at non-degree institutes such as
    Broad / MGH) an OpenAlex 'related' education institution of that institute."""
    H = json.load(open(D / "homes.json"))
    name_l = name.lower()
    out = []
    for a in H["authors"].values():
        assoc = [h["name"] for h in a["homes"]] + a.get("last_known_institutions", [])
        for h in a["homes"]:
            assoc += h.get("units", [])
        for ne in a.get("non_edu", []):
            assoc += related_edu(ne["id"])
        if any(name_l == x.lower() for x in assoc):
            out.append(a)
    return out


def main():
    cmd = sys.argv[1]
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    render = "--render" in sys.argv
    if cmd == "fetch":
        url = args[0]
        r = get(url, render)
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else ""
        print(f"status={r.status} final={r.final_url} fetched_at={r.fetched_at} cached={r.from_cache}")
        print(f"title={title!r} html_len={len(r.text)} text_len={len(soup.get_text(' ', strip=True))}")
        seen = set()
        for a in soup.find_all("a", href=True):
            t = a.get_text(" ", strip=True)
            h = a["href"]
            if (KW.search(t) or KW.search(h)) and (t, h) not in seen and len(t) < 90:
                seen.add((t, h))
                print(f"  [{t}] {h}")
    elif cmd == "text":
        url = args[0]
        r = get(url, render)
        soup = BeautifulSoup(r.text, "lxml")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        lines = [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]
        if "--grep" in sys.argv:
            rx = re.compile(sys.argv[sys.argv.index("--grep") + 1], re.I)
            lines = [l for l in lines if rx.search(l)]
        print(f"status={r.status} fetched_at={r.fetched_at}")
        print("\n".join(lines)[:12000])
    elif cmd == "homepage":
        I = json.load(open(D / "institutions.json"))
        for v in I.values():
            if v["display_name"].lower() == args[0].lower():
                print(v.get("homepage_url"), v["id"])
    elif cmd == "find":
        from urllib.parse import urljoin, urlsplit
        start, rx = args[0], re.compile(args[1], re.I)
        depth = int(sys.argv[sys.argv.index("--depth") + 1]) if "--depth" in sys.argv else 2
        mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 30

        def reg(h):
            parts = (h or "").lower().split(".")
            return ".".join(parts[-2:])
        base = reg(urlsplit(start).hostname)
        nav = re.compile(r"graduate|program|phd|ph-d|doctoral|academic|department|school|faculty|people|"
                         r"research|admission|degrees|study|training|divisions|centers|bbs|biosciences", re.I)
        seen, queue, printed, n = set(), [(start, 0)], set(), 0
        f = fetcher()
        while queue and n < mx:
            url, dep = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                r = f.get(url)
            except BlockedByRobots:
                print(f"BLOCKED {url}")
                continue
            n += 1
            if not r.ok or "html" not in (r.content_type or "html"):
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                h = urljoin(r.final_url, a["href"]).split("#")[0]
                t = a.get_text(" ", strip=True)[:90]
                if not h.startswith("http") or reg(urlsplit(h).hostname) != base:
                    continue
                if (rx.search(t) or rx.search(h)) and h not in printed:
                    printed.add(h)
                    print(f"  [{t}] {h}   (from {url})")
                if dep + 1 <= depth and h not in seen and (nav.search(t) or nav.search(h)):
                    queue.append((h, dep + 1))
        print(f"-- visited {n} pages")
    elif cmd == "authors":
        for a in inst_authors(args[0]):
            dirs = {d: v["tier"] for d, v in a["dirs"].items()}
            print(f"  {a['name']:30} {dirs} last_known={a.get('last_known_institutions')[:3]}")
    elif cmd == "match":
        inst = args[0]
        auths = inst_authors(inst)
        print(f"{len(auths)} relevant authors associated with {inst!r}")
        for url in args[1:]:
            r = get(url, render)
            txt = page_text(r.text)
            hits = []
            for a in auths:
                names = author_name_list(a["name"], a.get("display_name_alternatives", []))
                m = find_name(txt, name_variants(names), middle_initials(names))
                if m:
                    hits.append(f"{a['name']} {sorted(a['dirs'])}")
            print(f"== {url} status={r.status} text_len={len(txt)} matched={len(hits)}")
            for h in hits:
                print("   ", h)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
