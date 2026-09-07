from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .engine import VerificationError, verify

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path).path
        rel = parsed.lstrip("/") or "index.html"
        return str((WEB / rel).resolve())

    def do_POST(self):
        if self.path != "/api/verify":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200_000:
                raise VerificationError("request too large")
            body = self.rfile.read(length)
            spec = json.loads(body.decode("utf-8"))
            allowed = {"text_contains", "text_not_contains", "text_regex"}
            for criterion in spec.get("criteria", []):
                for check in criterion.get("checks", []):
                    if check.get("type") not in allowed:
                        raise VerificationError(f"web mode blocks check type: {check.get('type')}")
            spec.pop("workspace", None)
            report = verify(spec, base_dir=ROOT, allow_exec=False)
            payload = json.dumps(report).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            payload = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(400)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    host, port = "127.0.0.1", 8787
    print(f"ProofWorker → http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
