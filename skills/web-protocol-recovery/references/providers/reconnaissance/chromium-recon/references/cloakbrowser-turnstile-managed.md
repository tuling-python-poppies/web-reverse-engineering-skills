# CloakBrowser Turnstile Managed / 五秒盾

Use this reference only when the user explicitly asks for CloakBrowser browser-automation delivery for Cloudflare Turnstile managed challenge, 五秒盾, or a page whose visible widget says "Verify you are human" / "请验证您是真人". Keep `route: chromium-recon`; CloakBrowser is a Chromium tier, not a route.

Do **not** use this reference for generic captcha protocol recovery, browser-free collectors, pure protocol replay, or case-library proof. This pattern depends on a local browser runtime. It can be a user-requested compact browser automation deliverable, but it is not final browser-free protocol acceptance.

## Header

When the user explicitly asks for code using CloakBrowser against Turnstile managed / 五秒盾:

```text
shape: compact-replay
route: chromium-recon
nextAsk: <none | missing sample/context | executionPolicy>
nextRead: references/providers/reconnaissance/chromium-recon/PROVIDER.md
```

Use `nextAsk: missing sample/context` only if Browser Runtime Dependency Gate is about to ask for a local browser root. Use `nextAsk: executionPolicy` only when a required `pip`/`npm` install is missing. If the browser root or installed package is already known, `nextAsk: none`.

## Browser Runtime Dependency Gate

Ask this only when the next action is to launch the browser runtime:

```text
This step needs a local CloakBrowser runtime. Do you already have one installed?
1. Yes: provide the browser root directory, not the executable path, e.g. D:\develop_software\CloakBrowser
2. No: use the `cloakbrowser` package default resolution.
```

If the user provides a root directory, resolve the executable inside that root. Do not ask for an executable path. Common candidates:

```text
Windows: <root>\chrome.exe, <root>\CloakBrowser.exe
Linux:   <root>/chrome, <root>/chromium, <root>/cloakbrowser
macOS:   <root>/CloakBrowser.app/Contents/MacOS/CloakBrowser, <root>/Chromium.app/Contents/MacOS/Chromium
```

When a root is provided, set `CLOAKBROWSER_BINARY_PATH` to the resolved executable and set `CLOAKBROWSER_AUTO_UPDATE=false` so the wrapper does not download or replace the user-selected runtime. When no root is provided, do not set `CLOAKBROWSER_BINARY_PATH`; let the `cloakbrowser` package resolve or install its default binary. If the Python package itself is not installed, stop with `nextAsk: executionPolicy` before running `pip install cloakbrowser`.

## Implementation Template

Create a normal `web-protocol-recovery-simple` project. The stable file can be a root `main.py` when the user explicitly requested browser automation. Keep runtime state and screenshots under `js_reverse_cache/**`.

```python
import argparse
import os
from pathlib import Path
import sys
import time
from typing import Optional


TARGET_URL = "https://peet.ws/turnstile-test/managed.html"
CACHE_DIR = Path(__file__).resolve().parent / "js_reverse_cache"
PROFILE_DIR = CACHE_DIR / "private" / "cloak_profile"
SCREENSHOT_DIR = CACHE_DIR / "recon" / "cloak"


def resolve_browser_binary(browser_root: Optional[str]) -> Optional[Path]:
    if not browser_root:
        return None

    root = Path(browser_root).expanduser().resolve()
    if root.is_file():
        raise ValueError("Provide the browser root directory, not the executable path")
    if not root.is_dir():
        raise FileNotFoundError(f"Browser root does not exist: {root}")

    candidates = [
        root / "chrome.exe",
        root / "CloakBrowser.exe",
        root / "chrome",
        root / "chromium",
        root / "cloakbrowser",
        root / "CloakBrowser.app" / "Contents" / "MacOS" / "CloakBrowser",
        root / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    names = ", ".join(str(p.relative_to(root)) for p in candidates)
    raise FileNotFoundError(f"No supported browser binary found under {root}; tried: {names}")


def bypass_turnstile(
    url: str,
    browser_root: Optional[str],
    headless: bool,
    timeout_ms: int,
    fingerprint_seed: Optional[int],
) -> dict:
    browser_binary = resolve_browser_binary(browser_root)
    if browser_binary:
        os.environ["CLOAKBROWSER_BINARY_PATH"] = str(browser_binary)
        os.environ.setdefault("CLOAKBROWSER_AUTO_UPDATE", "false")

    try:
        from cloakbrowser import launch_persistent_context
    except ImportError:
        return {
            "success": False,
            "token": None,
            "elapsed_s": 0,
            "error": "cloakbrowser is not installed. Confirm executionPolicy, then run: pip install cloakbrowser",
        }

    start = time.time()
    context = None
    page = None
    try:
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

        args = []
        if fingerprint_seed is not None:
            args.append(f"--fingerprint={fingerprint_seed}")

        context = launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            humanize=True,
            args=args,
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        frame = page.frame_locator("iframe[src*='challenges.cloudflare.com']")
        checkbox = frame.get_by_role("checkbox")

        try:
            checkbox.wait_for(state="visible", timeout=10000)
            checkbox.click()
        except Exception:
            widget = page.locator(".cf-turnstile").first
            widget.wait_for(state="visible", timeout=timeout_ms)
            page.wait_for_timeout(1000)
            box = widget.bounding_box()
            if not box:
                raise RuntimeError("Turnstile widget is visible but has no bounding box")
            page.mouse.click(box["x"] + 22, box["y"] + 32)

        page.wait_for_function(
            """() => {
                const input = document.querySelector('[name="cf-turnstile-response"]');
                return input && input.value && input.value.length > 10;
            }""",
            timeout=timeout_ms,
        )
        token = page.evaluate("document.querySelector('[name=\"cf-turnstile-response\"]').value")
        return {
            "success": True,
            "token": token,
            "elapsed_s": round(time.time() - start, 2),
            "browser_binary": str(browser_binary) if browser_binary else "cloakbrowser package default",
            "error": None,
        }

    except Exception as exc:
        try:
            if page is not None:
                page.screenshot(path=str(SCREENSHOT_DIR / "failure.png"), full_page=True)
        except Exception:
            pass
        return {
            "success": False,
            "token": None,
            "elapsed_s": round(time.time() - start, 2),
            "browser_binary": str(browser_binary) if browser_binary else "cloakbrowser package default",
            "error": str(exc),
        }

    finally:
        if context:
            context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CloakBrowser Turnstile managed challenge runner")
    parser.add_argument("--url", default=TARGET_URL)
    parser.add_argument("--browser-root", default=os.environ.get("CLOAKBROWSER_ROOT"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--fingerprint-seed", type=int, default=42371)
    args = parser.parse_args()

    result = bypass_turnstile(
        url=args.url,
        browser_root=args.browser_root,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        fingerprint_seed=args.fingerprint_seed,
    )

    print(f"browser: {result.get('browser_binary')}")
    if not result["success"]:
        print(f"[FAIL] elapsed={result['elapsed_s']}s")
        print(f"error: {result['error']}")
        sys.exit(1)

    token = result["token"]
    print(f"[OK] elapsed={result['elapsed_s']}s")
    print(f"token length: {len(token)}")
    print(f"token head: {token[:60]}...")
    print(token)


if __name__ == "__main__":
    main()
```

## Commands

With an existing browser root:

```bash
python main.py --browser-root "D:\develop_software\CloakBrowser"
```

Without a browser root, after dependency-install approval if needed:

```bash
pip install cloakbrowser
python main.py
```

Headful mode is the default. Use `--headless` only when the user explicitly asks for it or the target is proven to pass headless. For Turnstile managed challenge, prefer headful plus `humanize=True`.

## Acceptance

Success means all checks hold:

1. The script launches CloakBrowser, not ordinary Playwright Chromium.
2. If a browser root was supplied, the resolved binary path is under that root.
3. A token is written to `[name="cf-turnstile-response"]` and its length is greater than 10.
4. The token is printed for immediate use but not written to disk.
5. Runtime state stays under `js_reverse_cache/private/cloak_profile`; screenshots stay under `js_reverse_cache/recon/cloak/`.
6. The final answer states this is browser automation delivery, not a browser-free protocol collector.

Observed local acceptance from the validating task: existing root `D:\develop_software\CloakBrowser`, package `cloakbrowser==0.5.6`, headful persistent context, token length 816, elapsed 14.2 seconds. Treat this as provenance for the template, not current-target acceptance for future tasks.

## Failure Recovery

| Symptom | First fix | Still fails |
|---|---|---|
| `cloakbrowser` import fails | Stop with `nextAsk: executionPolicy` for `pip install cloakbrowser` | Do not install silently |
| Browser root is an exe path | Ask for the root directory | Do not store executable path as route |
| Role checkbox not visible but screenshot shows widget | Use `.cf-turnstile` container coordinate fallback | Save `failure.png` and report selector blocker |
| Token remains empty | Check screenshot, iframe presence, headful mode, network, and browser version | Report live browser-runtime blocker |
| Chrome/Cloak launch exits immediately or profile is busy | Follow the browser startup failure diagnosis in `SKILL.md` | Do not kill user browsers automatically |

## Case-Library Boundary

Do not write this pattern to `references/cases/**` as a `verified` case by itself. The case writeback rules exclude browser-backed final delivery. It becomes case-eligible only if a later task extracts a browser-free protocol artifact with fixed vectors or semantic replay proof.
