# Live-state selector for the T'way Akamai case.
# Declares WHICH live state names are needed at reproduction time.
# Values are pulled from one approved browser session and kept in memory only;
# nothing in this file stores or returns real values.

LIVE_STATE = {
    "mode": "browser-export-json",
    "retention": "memory-only",
    "requiredCookies": [],
    "optionalCookies": [
        "bm_s",
        "bm_so",
        "bm_ss",
        "bm_sv",
        "bm_mi",
        "bm_lso",
        "ak_bmsc",
        "NetFunnel_ID",
        "SESSION",
        "WMONID",
        "SETTINGS_REGION",
        "SETTINGS_LANGUAGE",
        "SETTINGS_CURRENCY",
    ],
    "cookieNamePatterns": [
        "^bm_",
        "^ak_",
    ],
    "storageKeys": [
        "ak_bm_tab_id",
    ],
    "notes": [
        "Sensor cookies rotate on every sensor POST; seed cookies are optional "
        "because a fresh chain regenerates them through the iv8 bridge.",
        "NetFunnel_ID is an URL-encoded ticket string from ts.wseq 5101 enter; "
        "pull it only if reproducing mid-chain.",
        "SESSION is httpOnly and only needed for account-bound flows; public "
        "availability does not require it.",
    ],
}


def select(browser_state):
    """Pick the declared fields out of an approved browser export.

    browser_state: {"cookies": [{"name":..., "value":...}],
                    "sessionStorage": {...}, "localStorage": {...}}
    Returns memory-only dict with the same names; never persists.
    """
    out = {"cookies": {}, "sessionStorage": {}, "localStorage": {}}
    wanted = set(LIVE_STATE["optionalCookies"]) | set(LIVE_STATE["requiredCookies"])
    for cookie in browser_state.get("cookies", []) or []:
        name = cookie.get("name")
        if name in wanted:
            out["cookies"][name] = cookie.get("value", "")
    for key in LIVE_STATE["storageKeys"]:
        for store in ("sessionStorage", "localStorage"):
            source = browser_state.get(store) or {}
            if key in source:
                out[store][key] = source[key]
    return out


if __name__ == "__main__":
    import json

    print(json.dumps(LIVE_STATE, indent=2))
