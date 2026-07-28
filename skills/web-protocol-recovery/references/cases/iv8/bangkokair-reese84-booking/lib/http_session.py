# Offline-only case module. Final live egress belongs to python-collector under an approved project work-order.
from __future__ import annotations

def _reject_case_live_egress(action: str='live HTTP') -> None:
    raise RuntimeError(f'case entry refuses {action}: offline-only. Use projectRoot main.py + python-collector with a validated work-order.')
pass
BOOKING_ORIGIN = 'https://digital.bangkokair.com'
ENTRY_URL = f'{BOOKING_ORIGIN}/booking/availability/0'
API_HOST = 'https://api-des.bangkokair.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
BASE_HEADERS = {'User-Agent': UA, 'Accept-Language': 'en-GB,en;q=0.9', 'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"', 'Origin': BOOKING_ORIGIN, 'Referer': ENTRY_URL}

def make_session() -> requests.Session:
    return _reject_case_live_egress('requests.Session')

def browser_headers(extra: dict | None=None, reese: str | None=None) -> dict:
    h = dict(BASE_HEADERS)
    if reese:
        h['x-d-token'] = reese
    if extra:
        h.update(extra)
    return h

def install_reese_cookie(session: requests.Session, token: str, cookie_domain: str='bangkokair.com') -> None:
    domain = cookie_domain if cookie_domain.startswith('.') else f'.{cookie_domain}'
    session.cookies.set('reese84', token, domain=domain.lstrip('.'), path='/')
