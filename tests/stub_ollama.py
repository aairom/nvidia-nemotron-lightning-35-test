"""Minimal in-process fake Ollama server for tests (no real model needed)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/version":
            self._send(200, {"version": "9.9.9"})
        elif self.path == "/api/tags":
            self._send(200, {"models": [{"name": "stub:1"}]})
        elif self.path == "/api/ps":
            self._send(200, {"models": [{"name": "stub:1", "size": 123}] if self.server.loaded else []})
        else:
            self._send(404, {"error": "nope"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        self.server.requests.append((self.path, req))
        if req.get("model") != "stub:1":
            return self._send(404, {"error": f"model '{req.get('model')}' not found"})
        if self.path == "/api/generate":
            self.server.loaded = req.get("keep_alive") != 0
            return self._send(200, {"done": True})
        if self.path == "/api/chat":
            if req["messages"][-1]["content"] == "boom":
                return self._send(500, {"error": "kaboom"})
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.end_headers()
            lines = []
            if req.get("think"):
                lines.append({"message": {"thinking": "hmm "}, "done": False})
            lines += [{"message": {"content": "Hel"}, "done": False},
                      {"message": {"content": "lo"}, "done": False}]
            if req["messages"][-1]["content"] == "midstream":
                lines.append({"error": "died"})
            else:
                lines.append({"message": {"content": ""}, "done": True, "prompt_eval_count": 5,
                              "eval_count": 20, "eval_duration": 2_000_000_000,
                              "prompt_eval_duration": 500_000_000, "load_duration": 1_000_000_000,
                              "total_duration": 4_000_000_000})
            for ln in lines:
                self.wfile.write((json.dumps(ln) + "\n").encode())
                self.wfile.flush()
            return None
        return self._send(404, {"error": "nope"})


def start_stub() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    srv.requests, srv.loaded = [], False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"
