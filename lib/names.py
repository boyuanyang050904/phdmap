"""Match OpenAlex author names against the text of fetched faculty pages."""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

PARTICLES = {"van", "von", "de", "der", "den", "da", "di", "la", "le", "del", "dos", "du", "st"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("‐", "-").replace("–", "-")
    s = re.sub(r"[^a-z\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    txt = soup.get_text(" ", strip=True)
    # also include link texts/alts/titles and mailto/profile slugs (names often live in hrefs)
    extras = []
    for a in soup.find_all(["a", "img"]):
        for attr in ("title", "alt", "href", "aria-label"):
            v = a.get(attr)
            if v:
                extras.append(v.replace("-", " ").replace("_", " ").replace("/", " ").replace(".", " "))
    return norm(txt + " " + " ".join(extras))


DEGREES = {"phd", "md", "dr", "prof", "professor", "mph", "scd", "msc", "ms", "mba", "dphil", "bs", "ba",
           "jr", "sr", "ii", "iii", "iv", "facmi", "frcp", "pharmd", "dvm", "mbbs", "mmsc", "msce", "dsc"}


def _tokens(n):
    toks = [t for t in norm(n).split() if t and t not in DEGREES]
    return toks


def name_variants(names: list[str]) -> set[tuple[str, str]]:
    """(first, last) pairs from display names like 'Jeffrey J. Gray', 'Hongtu Zhu B',
    'César de la Fuente-Núñez'. Degree/title tokens are dropped; first and last
    names must have >= 2 letters (no initial-only variants)."""
    out = set()
    for n in names:
        toks = _tokens(n)
        while len(toks) > 2 and len(toks[-1]) == 1:   # trailing initial: "Hongtu Zhu B"
            toks = toks[:-1]
        if len(toks) < 2:
            continue
        first = toks[0]
        i = len(toks) - 1
        while i - 1 > 0 and toks[i - 1] in PARTICLES:
            i -= 1
        last = " ".join(toks[i:])
        cands = {(first, last)}
        if "-" in last:
            cands |= {(first, last.split("-")[0]), (first, last.replace("-", " "))}
        if "-" in first:
            cands |= {(first.replace("-", ""), last), (first.replace("-", " "), last)}
        for f, l in cands:
            if len(f.replace("-", "")) >= 2 and len(l.replace(" ", "").replace("-", "")) >= 2:
                out.add((f, l))
    return out


def middle_initials(names: list[str]) -> set[str]:
    out = set()
    for n in names:
        toks = _tokens(n)
        for t in toks[1:-1]:
            if t not in PARTICLES:
                out.add(t[0])
    return out


def find_name(text: str, variants: set[tuple[str, str]], middles: set[str] | None = None) -> str | None:
    """Return the matched snippet if the page contains 'first [middle] last' or 'last first'.
    A middle token is accepted only if it is a 1-2 letter initial or starts with one of the
    author's known middle initials (prevents stitching neighbouring names together)."""
    mids = middles or set()
    mid_word = r"[a-z]{1,2}"
    if mids:
        mid_word = r"(?:[a-z]{1,2}|[" + "".join(sorted(mids)) + r"][a-z\-]+)"
    for first, last in variants:
        fl = re.escape(first)
        ll = re.escape(last)
        pat = rf"\b{fl}(?: {mid_word}){{0,2}} {ll}\b|\b{ll} {fl}\b"
        m = re.search(pat, text)
        if m:
            return text[max(0, m.start() - 30): m.end() + 30]
    return None


def author_name_list(display_name: str, alternatives: list[str] | None, limit: int = 15) -> list[str]:
    """Display name + OpenAlex alternatives that are plausibly the same person:
    same surname and same first initial (alternatives are noisy, e.g. 'Didong Li' -> 'Yun Li').
    Reversed-order alternatives ('Li Didong') are accepted too."""
    base = name_variants([display_name])
    if not base:
        return [display_name]
    keep = [display_name]
    for alt in (alternatives or [])[: 4 * limit]:
        av = name_variants([alt])
        ok = False
        for f, l in av:
            for bf, bl in base:
                if (l == bl and f[0] == bf[0]) or (f == bl and l[0] == bf[0]):
                    ok = True
        if ok and alt not in keep:
            keep.append(alt)
        if len(keep) > limit:
            break
    return keep
