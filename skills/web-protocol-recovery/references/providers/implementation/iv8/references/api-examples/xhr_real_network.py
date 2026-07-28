"""
iv8 offline XHR bridge example.

Historical versions of this file routed XHR through Python requests. That is no
longer acceptable in an implementation Provider example: use injected resources
or a project-local python-collector delivery bridge with an approved work order.
"""

import json

import iv8


def setup_offline_xhr(ctx: iv8.JSContext) -> None:
    ctx.eval(
        """
        window.__iv8__.page.load({
            html: '<html><body></body></html>',
            baseURL: 'https://example.invalid'
        });
        """
    )
    ctx.add_resource(
        url="https://example.invalid/api/data",
        body=json.dumps({"key": "offline-value"}),
        status=200,
        headers={"content-type": "application/json"},
    )


def main() -> None:
    with iv8.JSContext() as ctx:
        setup_offline_xhr(ctx)
        ctx.eval(
            """
            var xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://example.invalid/api/data', false);
            xhr.send(null);
            """
        )
        result = {
            "status": ctx.eval("xhr.status"),
            "body": json.loads(str(ctx.eval("xhr.responseText"))),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
