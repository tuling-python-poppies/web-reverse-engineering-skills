"""
iv8 offline Python bridge example.

This example is intentionally offline. It demonstrates how JavaScript can call a
Python-owned bridge that returns a narrow artifact from supplied local data. Do
not add requests/httpx/aiohttp here; final live egress belongs to
python-collector under a validated work order.
"""

import json

import iv8


LOCAL_RESPONSES = {
    "https://example.invalid/config": {
        "status": 200,
        "body": {"version": "2.0", "features": ["a", "b"]},
    },
    "https://example.invalid/sign-input": {
        "status": 200,
        "body": {"nonce": "fixed", "page": 1},
    },
}


def bridge_get(url: str) -> str:
    record = LOCAL_RESPONSES.get(str(url))
    if record is None:
        raise ValueError(f"offline fixture missing for {url}")
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    with iv8.JSContext() as ctx:
        ctx.expose(bridge_get, "bridgeGet")
        result = ctx.eval(
            """
            (function() {
                var raw = __iv8__.data.bridgeGet('https://example.invalid/config');
                var resp = JSON.parse(raw);
                return {ok: resp.status === 200, version: resp.body.version};
            })()
            """,
            to_py=True,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
