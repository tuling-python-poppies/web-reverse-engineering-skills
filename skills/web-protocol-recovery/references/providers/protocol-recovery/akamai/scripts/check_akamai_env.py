#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys


def module_status(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    modules = {
        "curl_cffi": module_status("curl_cffi"),
        "iv8": module_status("iv8"),
        "bs4": module_status("bs4"),
    }
    chrome_profile = None
    if modules["curl_cffi"]:
        from curl_cffi.requests.impersonate import DEFAULT_CHROME

        chrome_profile = DEFAULT_CHROME

    result = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "modules": modules,
        "curl_cffi_default_chrome": chrome_profile,
        "proxy_env": {
            name: os.getenv(name)
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
            if os.getenv(name)
        },
        "notes": [
            "curl_cffi is required for browser-like TLS/HTTP2 replay",
            "iv8 is required only for the local live-collector route",
            "proxy environment variables must be handled explicitly",
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if modules["curl_cffi"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
