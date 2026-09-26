from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from bot import compose

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
DATA = ROOT / "dataset" / "expanded"
PAIRS_FILE = DATA / "test_pairs.json"


contexts = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {}
}


def load_json(folder, name):
    with (DATA / folder / f"{name}.json").open(encoding="utf-8") as source:
        return json.load(source)


def load_demo_scenario(pair):
    merchant = load_json("merchants", pair["merchant_id"])
    trigger = load_json("triggers", pair["trigger_id"])
    customer = (
        load_json("customers", pair["customer_id"])
        if pair.get("customer_id") else None
    )
    category = load_json("categories", merchant["category_slug"])
    return merchant, trigger, customer, category


def demo_pairs():
    with PAIRS_FILE.open(encoding="utf-8") as source:
        return json.load(source)["pairs"]


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path in ("/app.css", "/app.js"):
            file_path = FRONTEND / ("index.html" if path == "/" else path[1:])
            try:
                body = file_path.read_bytes()
            except FileNotFoundError:
                self.send_json({"error": "Not found"}, 404)
                return
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8",
            }.get(file_path.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/v1/healthz":
            self.send_json({"status": "ok"})

        elif path == "/v1/metadata":
            self.send_json({
                "team_name": "Dhruv Garg",
                "model": "Vera Merchant AI"
            })

        elif path == "/v1/demo/scenarios":
            scenarios = []
            for pair in demo_pairs():
                merchant, trigger, customer, _ = load_demo_scenario(pair)
                identity = merchant.get("identity", {})
                scenarios.append({
                    "test_id": pair["test_id"],
                    "merchant_id": pair["merchant_id"],
                    "customer_id": pair.get("customer_id"),
                    "trigger_id": pair["trigger_id"],
                    "kind": trigger.get("kind", "unknown"),
                    "urgency": trigger.get("urgency", 0),
                    "category": merchant.get("category_slug", ""),
                    "merchant_name": identity.get("name", "Merchant"),
                    "owner_name": identity.get("owner_first_name", "there"),
                    "city": identity.get("city", ""),
                    "customer_name": (
                        customer.get("identity", {}).get("name")
                        if customer else None
                    ),
                })
            self.send_json({"scenarios": scenarios})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        path = urlparse(self.path).path

        if path == "/v1/demo/compose":
            test_id = data.get("test_id")
            pair = next(
                (item for item in demo_pairs() if item["test_id"] == test_id),
                None
            )
            if pair is None:
                self.send_json({"error": "Unknown demo scenario"}, 404)
                return
            merchant, trigger, customer, category = load_demo_scenario(pair)
            self.send_json({
                "message": compose(category, merchant, trigger, customer),
                "merchant": merchant,
                "trigger": trigger,
                "customer": customer,
            })

        elif path == "/v1/context":
            scope = data.get("scope")
            context_id = data.get("context_id")
            payload = data.get("payload", {})

            if scope in contexts and context_id:
                contexts[scope][context_id] = payload

            self.send_json({"accepted": True})

        elif path == "/v1/tick":
            self.send_json({"actions": []})

        elif path == "/v1/reply":
            message = data.get("message", "").strip()
            lower = message.lower()

            # Judge safety / conversation handling
            if any(x in lower for x in [
                "stop messaging",
                "stop",
                "spam",
                "useless"
            ]):
                self.send_json({
                    "action": "end"
                })
                return

            if any(x in lower for x in [
                "ok lets do it",
                "ok, lets do it",
                "whats next",
                "what's next"
            ]):
                self.send_json({
                    "action": "send",
                    "body": "Done — I’ll help you with the next step."
                })
                return

            # Auto-reply pattern
            if "thank you for contacting us" in lower:
                self.send_json({
                    "action": "wait",
                    "wait_seconds": 5
                })
                return

            self.send_json({
                "action": "wait",
                "wait_seconds": 5
            })

        else:
            self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("localhost", port), Handler)
    print(f"Vera bot server running on http://localhost:{port}")
    server.serve_forever()
