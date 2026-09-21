"""Dependency-free HTTP delivery for the blind-SQLi training challenge."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from challenge import oracle


class Handler(BaseHTTPRequestHandler):
    def bounded_content_length(self) -> int:
        try:
            return max(0, min(int(self.headers.get("Content-Length", "0")), 1024))
        except ValueError:
            return 0

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
        elif self.path == "/":
            self.send_json(
                200,
                {
                    "service": "t3mp3st-ctf-sqli-blind",
                    "usage": "POST /query with a JSON sku value",
                    "oracle": "found plus row count only",
                },
            )
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path != "/query":
            self.send_json(404, {"error": "not found"})
            return
        body = self.rfile.read(self.bounded_content_length()).decode(errors="replace")
        try:
            sku = json.loads(body).get("sku")
            if not isinstance(sku, str) or not sku:
                raise ValueError
        except ValueError:
            self.send_json(400, {"error": "bad sku"})
            return
        found, count = oracle(sku)
        self.send_json(200 if found else 404, {"found": found, "count": count})

    def log_message(self, _format: str, *_args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
