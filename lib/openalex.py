"""OpenAlex client: api_key + mailto on every request, disk cache via lib.fetch."""
from __future__ import annotations

import os
import time
from pathlib import Path

from .fetch import Fetcher, canonical_url

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.openalex.org"


def _env():
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("OPENALEX_")})
    return env


ENV = _env()
MAILTO = ENV.get("OPENALEX_MAILTO", "boyuan.yang@emory.edu")
API_KEY = ENV.get("OPENALEX_API_KEY")

_f = Fetcher(min_delay=0.12)


class OpenAlexError(RuntimeError):
    pass


def get(path: str, **params):
    """GET an OpenAlex endpoint. Returns (json, citable_url, fetched_at)."""
    params = {k: v for k, v in params.items() if v is not None}
    params["mailto"] = MAILTO
    if API_KEY:
        params["api_key"] = API_KEY
    url = path if path.startswith("http") else BASE + path
    for attempt in range(6):
        r = _f.get(url, params=params)
        if r.ok:
            return r.json(), r.url, r.fetched_at
        if r.status in (429, 0) or r.status >= 500:
            time.sleep(min(60, 5 * 2 ** attempt))
            continue
        raise OpenAlexError(f"{r.status} {r.url}: {r.text[:500]}")
    raise OpenAlexError(f"giving up: {canonical_url(url, params)}")


def paginate(path: str, max_results: int | None = None, per_page: int = 200, **params):
    """Cursor-paginate an OpenAlex list endpoint; yields (item, page_url, fetched_at)."""
    cursor = "*"
    n = 0
    while cursor:
        data, url, at = get(path, per_page=per_page, cursor=cursor, **params)
        for it in data.get("results", []):
            yield it, url, at
            n += 1
            if max_results and n >= max_results:
                return
        cursor = data.get("meta", {}).get("next_cursor")
        if not data.get("results"):
            break


def count(path: str, **params) -> int:
    data, _, _ = get(path, per_page=1, **params)
    return data["meta"]["count"]
