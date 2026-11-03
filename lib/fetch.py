"""Polite, cached HTTP fetching.

* Every response is cached on disk (cache/http/<sha256>.json.gz) together with
  the URL, final URL, HTTP status and the UTC fetch timestamp, so every
  extracted fact can cite source_url + fetched_at.
* robots.txt (RFC 9309) is honoured for our own UA token ("phdmap"), for
  "Claude-User" (Anthropic's token for fetches made on a user's behalf, which is
  what this tool does; its older name "Claude-Web" is honoured too) and for "*"; a URL is fetched only if all of them allow it.
  ClaudeBot / anthropic-ai are Anthropic's *training* crawlers, not this tool.
  robots.txt 4xx => no restrictions; 5xx / unreachable => complete disallow
  (RFC 9309 sec. 2.3.1.3-4).  Crawl-delay is honoured.
  (Policy switched from the stricter variant at the user's explicit request, 2026-11-03.)
* A minimum per-host delay is enforced (default 2 s).
* Blocked / failed URLs are logged to cache/fetch_log.jsonl.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

import requests

from . import tlsfix

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "http"
LOG_PATH = ROOT / "cache" / "fetch_log.jsonl"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 phdmap/0.1 (personal PhD-application research tool)")
ROBOT_TOKENS = ["phdmap", "Claude-User", "Claude-Web", "*"]  # Claude-Web = older name of Claude-User
SECRET_PARAMS = {"api_key"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_url(url: str, params: dict | None = None) -> str:
    """URL with params merged and sorted; secret params removed (cache key / citation)."""
    parts = urlsplit(url)
    q = parse_qsl(parts.query, keep_blank_values=True)
    if params:
        q += [(k, str(v)) for k, v in params.items() if v is not None]
    q = sorted((k, v) for k, v in q if k not in SECRET_PARAMS)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))


@dataclass
class Resp:
    url: str            # canonical requested URL (citable, no secrets)
    final_url: str
    status: int
    text: str
    fetched_at: str
    from_cache: bool
    content_type: str = ""

    def json(self):
        return json.loads(self.text)

    @property
    def ok(self):
        return 200 <= self.status < 300


class BlockedByRobots(Exception):
    pass


class HostUnreachable(BlockedByRobots):
    """robots.txt could not be retrieved (DNS / TLS / proxy error) -> site not fetched.
    Same fetching behaviour as BlockedByRobots; only the label differs."""
    pass


class Fetcher:
    def __init__(self, min_delay: float = 2.0, timeout: float = 40.0):
        self.min_delay = min_delay
        self.timeout = timeout
        self.s = requests.Session()
        self.s.verify = tlsfix.build_combined()
        self._tls_fixed: set[str] = set()
        self.s.headers.update({"User-Agent": UA,
                               "Accept-Language": "en-US,en;q=0.9"})
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- cache
    @staticmethod
    def _key(curl: str, method: str = "GET", body: str = "") -> Path:
        h = hashlib.sha256(f"{method} {curl} {body}".encode()).hexdigest()
        return CACHE_DIR / h[:2] / f"{h}.json.gz"

    @staticmethod
    def _load(p: Path) -> dict | None:
        if p.exists():
            try:
                with gzip.open(p, "rt", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    @staticmethod
    def _store(p: Path, rec: dict):
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".tmp{os.getpid()}{random.randint(0, 1 << 30)}")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(rec, f)
        os.replace(tmp, p)

    @staticmethod
    def log(**kw):
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        kw["at"] = utcnow()
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(kw) + "\n")

    # --------------------------------------------------------------- robots
    def _robots_for(self, url: str):
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base in self._robots:
            return self._robots[base]
        rurl = base + "/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rec = self._raw_get(rurl, check_robots=False, max_age_days=7)
        if rec.status == 0 or rec.status >= 500:
            # robots.txt unreachable (network/TLS/5xx): do not fetch the site at all
            rp.disallow_all = True
            rp.unreachable = True
            self.log(event="robots_unreachable", url=rurl, status=rec.status)
        elif rec.status >= 400:
            # RFC 9309: 4xx "unavailable" => crawler may access any resource
            rp.allow_all = True
        else:
            rp.parse(rec.text.splitlines())
        self._robots[base] = rp
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return all(rp.can_fetch(t, url) for t in ROBOT_TOKENS)

    def _delay_for(self, url: str) -> float:
        d = self.min_delay
        try:
            rp = self._robots_for(url)
            cd = rp.crawl_delay("phdmap") or rp.crawl_delay("*")
            if cd:
                d = max(d, float(cd))
        except Exception:
            pass
        return d

    def _wait(self, host: str, delay: float):
        with self._lock:
            last = self._last.get(host, 0)
            now = time.time()
            wait = last + delay - now
            self._last[host] = max(now, last + delay)
        if wait > 0:
            time.sleep(wait)

    # ------------------------------------------------------------------ get
    def _raw_get(self, url, params=None, headers=None, check_robots=True,
                 max_age_days=None, delay=None, retries=3) -> Resp:
        curl = canonical_url(url, params)
        p = self._key(curl)
        rec = self._load(p)
        if rec is not None:
            fresh = True
            if max_age_days is not None:
                age = (datetime.now(timezone.utc) -
                       datetime.strptime(rec["fetched_at"], "%Y-%m-%dT%H:%M:%SZ")
                       .replace(tzinfo=timezone.utc)).days
                fresh = age <= max_age_days
            if fresh:
                return Resp(rec["url"], rec["final_url"], rec["status"], rec["text"],
                            rec["fetched_at"], True, rec.get("content_type", ""))
        if check_robots and not self.allowed(curl):
            if getattr(self._robots_for(curl), "unreachable", False):
                raise HostUnreachable(curl)
            self.log(event="robots_blocked", url=curl)
            raise BlockedByRobots(curl)
        host = urlsplit(curl).netloc
        d = delay if delay is not None else (self._delay_for(curl) if check_robots else self.min_delay)
        last_exc = None
        for attempt in range(retries + 1):
            self._wait(host, d)
            try:
                r = self.s.get(url, params=params, headers=headers, timeout=self.timeout,
                               allow_redirects=True, verify=self.s.verify)
            except requests.exceptions.SSLError as e:
                last_exc = e
                h = urlsplit(url).hostname
                if "local issuer" in str(e) and h not in self._tls_fixed:
                    self._tls_fixed.add(h)
                    if tlsfix.fix_host(h):
                        # new session so urllib3 reloads the CA file
                        hdrs = dict(self.s.headers)
                        self.s.close()
                        self.s = requests.Session()
                        self.s.headers.update(hdrs)
                        self.s.verify = str(tlsfix.COMBINED)
                        continue
                break
            except requests.RequestException as e:
                last_exc = e
                time.sleep(2 ** (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                ra = r.headers.get("Retry-After")
                wait = float(ra) if ra and ra.isdigit() and float(ra) < 120 else 2 ** (attempt + 2)
                time.sleep(wait)
                continue
            ctype = r.headers.get("Content-Type", "")
            out = Resp(curl, r.url, r.status_code, r.text, utcnow(), False, ctype)
            if r.status_code < 500 and r.status_code != 429:
                self._store(p, {"url": curl, "final_url": r.url, "status": r.status_code,
                                "text": r.text, "fetched_at": out.fetched_at,
                                "content_type": ctype})
            if not out.ok:
                self.log(event="http_error", url=curl, status=r.status_code)
            return out
        self.log(event="network_error", url=curl, error=str(last_exc))
        return Resp(curl, curl, 0, "", utcnow(), False)

    def get(self, url, params=None, headers=None, max_age_days=None, delay=None) -> Resp:
        return self._raw_get(url, params=params, headers=headers,
                             max_age_days=max_age_days, delay=delay)

    # ------------------------------------------------------ rendered (JS)
    def get_rendered(self, url, wait_ms=2500, max_age_days=None) -> Resp:
        """Fetch with headless Chromium (for JS-rendered pages). Same cache/robots rules."""
        curl = canonical_url(url)
        frag = urlsplit(url).fragment
        # JS apps often filter by #fragment: keep it in the cache key for rendered pages
        p = self._key(curl + (("#" + frag) if frag else ""), method="RENDER")
        rec = self._load(p)
        if rec is not None and max_age_days is None:
            return Resp(rec["url"], rec["final_url"], rec["status"], rec["text"],
                        rec["fetched_at"], True)
        if not self.allowed(curl):
            self.log(event="robots_blocked", url=curl)
            raise BlockedByRobots(curl)
        self._wait(urlsplit(curl).netloc, self._delay_for(curl))
        import subprocess
        env = dict(os.environ, PHDMAP_UA=UA)
        status, html, final = 0, "", url
        try:
            pr = subprocess.run(["node", str(ROOT / "lib" / "render.js"), url, str(wait_ms)],
                                capture_output=True, text=True, timeout=120, env=env)
            d = json.loads(pr.stdout or "{}")
            status, html, final = d.get("status", 0), d.get("html", ""), d.get("final_url", url)
        except Exception as e:
            self.log(event="render_error", url=curl, error=str(e))
        out = Resp(curl, final, status, html, utcnow(), False)
        if status and status < 500:
            self._store(p, {"url": curl, "final_url": final, "status": status,
                            "text": html, "fetched_at": out.fetched_at})
        return out


_default: Fetcher | None = None


def fetcher() -> Fetcher:
    global _default
    if _default is None:
        _default = Fetcher()
    return _default
