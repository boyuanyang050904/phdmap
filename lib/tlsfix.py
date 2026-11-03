"""TLS trust helpers (verification is never disabled).

Problem seen in this container: the proxy's CA bundle (/root/.ccr/ca-bundle.crt)
carries an older Mozilla root set, and many US university servers (InCommon,
now issued under emSign) don't send their intermediate certificates.

Fix:
 1. combined bundle = proxy bundle + Mozilla's current root store (certifi
    2026.10.23 from PyPI, saved at cache/certs/mozilla_certifi_*.pem)
 2. on "unable to get local issuer certificate", fetch the leaf certificate,
    follow its AIA "CA Issuers" URL(s), and keep the downloaded intermediates
    ONLY if `openssl verify` chains them to a root already in the bundle.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parent.parent
CERTS = ROOT / "cache" / "certs"
PROXY_BUNDLE = "/root/.ccr/ca-bundle.crt"
COMBINED = CERTS / "combined.pem"
INTERMEDIATES = CERTS / "intermediates.pem"


def build_combined() -> str:
    CERTS.mkdir(parents=True, exist_ok=True)
    parts = [Path(PROXY_BUNDLE).read_text()] if os.path.exists(PROXY_BUNDLE) else []
    for p in sorted(glob.glob(str(CERTS / "mozilla_certifi_*.pem"))):
        parts.append(Path(p).read_text())
    if INTERMEDIATES.exists():
        parts.append(INTERMEDIATES.read_text())
    tmp = COMBINED.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text("\n".join(parts))
    os.replace(tmp, COMBINED)
    return str(COMBINED)


def _to_pems(blob: bytes) -> list[str]:
    """DER / PEM / PKCS7 -> list of PEM certs."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(blob)
        path = f.name
    try:
        for cmd in (["openssl", "pkcs7", "-inform", "DER", "-in", path, "-print_certs"],
                    ["openssl", "pkcs7", "-in", path, "-print_certs"],
                    ["openssl", "x509", "-inform", "DER", "-in", path],
                    ["openssl", "x509", "-in", path]):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and "BEGIN CERTIFICATE" in r.stdout:
                return re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", r.stdout, re.S)
    finally:
        os.unlink(path)
    return []


def _leaf_and_aia(host: str) -> tuple[str | None, list[str]]:
    proxy = os.environ.get("HTTPS_PROXY", "").replace("http://", "")
    cmd = ["openssl", "s_client", "-connect", f"{host}:443", "-servername", host, "-showcerts"]
    if proxy:
        cmd += ["-proxy", proxy]
    try:
        r = subprocess.run(cmd, input="", capture_output=True, text=True, timeout=30)
    except Exception:
        return None, []
    pems = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", r.stdout, re.S)
    if not pems:
        return None, []
    urls = []
    for pem in pems:
        t = subprocess.run(["openssl", "x509", "-noout", "-text"], input=pem, capture_output=True, text=True)
        urls += re.findall(r"CA Issuers - URI:(\S+)", t.stdout)
    return pems[0], urls


def _verify(leaf_or_cert: str, untrusted: list[str], cafile: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        c = Path(d) / "c.pem"
        c.write_text(leaf_or_cert)
        args = ["openssl", "verify", "-CAfile", cafile]
        if untrusted:
            u = Path(d) / "u.pem"
            u.write_text("\n".join(untrusted))
            args += ["-untrusted", str(u)]
        r = subprocess.run(args + [str(c)], capture_output=True, text=True)
        return r.returncode == 0


def fix_host(host: str) -> bool:
    """Try to fetch & validate missing intermediates for host. Returns True if fixed."""
    cafile = build_combined()
    leaf, urls = _leaf_and_aia(host)
    if not leaf:
        return False
    got: list[str] = []
    seen = set()
    queue = list(urls)
    while queue and len(seen) < 6:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        blob = None
        for cand in ([u.replace("http://", "https://", 1), u] if u.startswith("http://") else [u]):
            try:
                rr = requests.get(cand, timeout=20, verify=cafile)
                if rr.ok:
                    blob = rr.content
                    break
            except requests.RequestException:
                continue
        if not blob:
            continue
        for pem in _to_pems(blob):
            if pem not in got:
                got.append(pem)
                t = subprocess.run(["openssl", "x509", "-noout", "-text"], input=pem,
                                   capture_output=True, text=True)
                queue += re.findall(r"CA Issuers - URI:(\S+)", t.stdout)
    if got and _verify(leaf, got, cafile):
        # keep only certs that themselves chain to a trusted root
        keep = [p for p in got if _verify(p, got, cafile)]
        existing = INTERMEDIATES.read_text() if INTERMEDIATES.exists() else ""
        add = [p for p in keep if p not in existing]
        if add:
            with open(INTERMEDIATES, "a") as f:
                f.write("\n" + "\n".join(add) + "\n")
        build_combined()
        return True
    return False
