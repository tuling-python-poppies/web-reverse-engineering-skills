# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
from __future__ import annotations

def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
pass
REESE_MARKERS = ('reese84', 'initializeProtection', 'reeseSkipAutoLoad', 'onProtectionInitialized')

class _ScriptSrcParser(HTMLParser):

    def __init__(self) -> None:
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != 'script':
            return
        attr = {k.lower(): v or '' for k, v in attrs}
        src = attr.get('src')
        if src:
            self.srcs.append(src)

def discover_script_sources(html: str) -> list[str]:
    parser = _ScriptSrcParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    srcs = list(parser.srcs)
    for m in re.finditer('scriptElement\\.src\\s*=\\s*[\'"]([^\'"]+)[\'"]', html, flags=re.I):
        srcs.append(m.group(1))
    for m in re.finditer('\\.src\\s*=\\s*[\'"](/[^\'"]+)[\'"]', html, flags=re.I):
        srcs.append(m.group(1))
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
        return ''
    return f'{p.scheme}://{p.netloc}'

def build_allowlist(entry_url: str, html: str) -> set[str]:
    allowed = {origin_of(entry_url)}
    for src in discover_script_sources(html):
        full = urljoin(entry_url, src)
        o = origin_of(full)
        if o.startswith('https://'):
            allowed.add(o)
    return {a for a in allowed if a}

def looks_like_reese(script_text: str) -> bool:
    low = script_text[:200000].lower() if script_text else ''
    return any((m.lower() in low for m in REESE_MARKERS))

def discover_challenge(session: requests.Session, entry_response: requests.Response, headers: dict) -> tuple[str, str]:
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
            resp = (_reject_case_live_egress('session.get'), None)[1]
        except Exception as e:
            last_err = e
            continue
        if resp.status_code != 200 or not resp.text:
            continue
        if looks_like_reese(resp.text) or 'function' in resp.text[:200]:
            if looks_like_reese(resp.text) or len(resp.text) > 50000:
                return (script_url, resp.text)
    for source in discover_script_sources(html):
        script_url = urljoin(entry_url, source)
        if origin_of(script_url) != origin_of(entry_url):
            continue
        resp = (_reject_case_live_egress('session.get'), None)[1]
        if resp.status_code == 200 and len(resp.text) > 20000:
            return (script_url, resp.text)
    raise RuntimeError(f'Reese84 challenge not found (last_err={last_err})')
