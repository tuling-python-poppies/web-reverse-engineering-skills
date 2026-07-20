# Python Collector Provider

## Select When

- Real endpoint and moving protocol state are already proved.
- Desired result is compact-replay or collector under `web-protocol-recovery-simple/v1`.
- Final live HTTP must be browser-free Python.

## Do Not Select When

- Protocol is still unproved (recon/implementation first).
- User only wants evidence or a hook snippet.
- Scaffold would overwrite existing `main.py` or create wrapper trees (reject).

Use this provider after web-protocol-recovery has proved the real endpoint and moving protocol state. It owns the stable browser-free implementation assigned under `main.py` and `utils/`.

Python owns live HTTP, session/cookie handling, request budgets, retries, pagination, parsing, decode, persistence, and output. JavaScript, WASM, or iv8 helpers remain narrow local artifact generators. The final path never drives a browser.

Start from the `web-protocol-recovery-simple/v1` layout. Reject symlinks, Windows junctions/reparse paths, and hard-linked files before writing. Publish only explicitly requested missing files atomically and never overwrite an existing path. Keep `main.py` compact and move only distinct stable responsibilities into `utils/sign.py`, `utils/runtime.py`, `utils/decode.py`, `utils/client.py`, or similarly narrow files. Do not generate a package framework or mandatory directories.

Require fixed-input checks before live traffic. Bound redirects, retries, response bytes, pages, concurrency, and output overwrite. Preserve cookie domain/path scope, exact serialization, and response bytes before decode. A `200` or non-empty signature is not semantic success.
