from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from curl_cffi import requests

REESE_MARKERS = ("reese84", "initializeProtection", "reeseSkipAutoLoad", "onProtectionInitialized")


class _ScriptSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        src = attr.get("src")
        if src:
            self.srcs.append(src)


def discover_script_sources(html: str) -> list[str]:
    parser = _ScriptSrcParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    srcs = list(parser.srcs)
    # dynamic assignment patterns seen on Imperva interstitial
    for m in re.finditer(
        r"""scriptElement\.src\s*=\s*['"]([^'"]+)['"]""",
        html,
        flags=re.I,
    ):
        srcs.append(m.group(1))
    for m in re.finditer(
        r"""\.src\s*=\s*['"](/[^'"]+)['"]""",
        html,
        flags=re.I,
    ):
        srcs.append(m.group(1))
    # de-dupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for s in srcs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def origin_of(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return ""
    return f"{p.scheme}://{p.netloc}"


def build_allowlist(entry_url: str, html: str) -> set[str]:
    allowed = {origin_of(entry_url)}
    for src in discover_script_sources(html):
        full = urljoin(entry_url, src)
        o = origin_of(full)
        if o.startswith("https://"):
            allowed.add(o)
    return {a for a in allowed if a}


def looks_like_reese(script_text: str) -> bool:
    low = script_text[:200000].lower() if script_text else ""
    return any(m.lower() in low for m in REESE_MARKERS)


def discover_challenge(
    session: requests.Session,
    entry_response: requests.Response,
    headers: dict,
) -> tuple[str, str]:
    """Return (challenge_url, challenge_js_text)."""
    entry_url = str(entry_response.url)
    html = entry_response.text
    allowed = build_allowlist(entry_url, html)
    last_err = None
    for source in discover_script_sources(html):
        script_url = urljoin(entry_url, source)
        if origin_of(script_url) not in allowed:
            continue
        try:
            resp = session.get(
                script_url,
                headers={**headers, "Referer": entry_url, "Accept": "*/*"},
                timeout=30,
            )
        except Exception as e:
            last_err = e
            continue
        if resp.status_code != 200 or not resp.text:
            continue
        if looks_like_reese(resp.text) or "function" in resp.text[:200]:
            # Prefer marker hits; still accept large same-origin scripts from interstitial
            if looks_like_reese(resp.text) or len(resp.text) > 50_000:
                return script_url, resp.text
    # Fallback: any large same-origin script from dynamic src
    for source in discover_script_sources(html):
        script_url = urljoin(entry_url, source)
        if origin_of(script_url) != origin_of(entry_url):
            continue
        resp = session.get(
            script_url,
            headers={**headers, "Referer": entry_url, "Accept": "*/*"},
            timeout=30,
        )
        if resp.status_code == 200 and len(resp.text) > 20_000:
            return script_url, resp.text
    raise RuntimeError(f"Reese84 challenge not found (last_err={last_err})")
