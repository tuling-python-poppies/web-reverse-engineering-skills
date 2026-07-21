import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode

try:
    from curl_cffi import requests
except Exception:
    import requests


ROOT = Path(__file__).resolve().parent
MAIN_JS = ROOT / "main.js"


def get_encrypted_params(payload):
    try:
        import execjs

        source = MAIN_JS.read_text(encoding="utf-8")
        ctx = execjs.compile(source, cwd=str(ROOT))
        return ctx.call("getEncryptedParams", payload)
    except Exception:
        completed = subprocess.run(
            ["node", str(MAIN_JS), json.dumps(payload, ensure_ascii=False)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout or "{}")


def request_api():
    base_url = "https://target.example/api/path"
    headers = {"user-agent": "...", "referer": "..."}
    cookies = {}
    params = {}

    prepared_url = base_url + (("?" + urlencode(params)) if params else "")
    encrypted = get_encrypted_params({"url": prepared_url})
    params.update({key: value for key, value in encrypted.items() if value})

    response = requests.get(base_url, headers=headers, cookies=cookies, params=params)
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    request_api()
