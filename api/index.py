import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bot import compose

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset" / "expanded"
PAIRS_FILE = DATA / "test_pairs.json"
contexts = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {},
}


def load_json(folder, name):
    with (DATA / folder / f"{name}.json").open(encoding="utf-8") as source:
        return json.load(source)


def demo_pairs():
    with PAIRS_FILE.open(encoding="utf-8") as source:
        return json.load(source)["pairs"]


def load_demo_scenario(pair):
    merchant = load_json("merchants", pair["merchant_id"])
    trigger = load_json("triggers", pair["trigger_id"])
    customer = (
        load_json("customers", pair["customer_id"])
        if pair.get("customer_id") else None
    )
    category = load_json("categories", merchant["category_slug"])
    return merchant, trigger, customer, category


class handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        return "/v1/" + parse_qs(urlparse(self.path).query).get("path", [""])[0].lstrip("/")

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        path = self.route()
        if path == "/v1/healthz":
            self.send_json({"status": "ok"})
        elif path == "/v1/metadata":
            self.send_json({"team_name": "Dhruv Garg", "model": "Vera Merchant AI"})
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
                    "customer_name": customer.get("identity", {}).get("name") if customer else None,
                })
            self.send_json({"scenarios": scenarios})
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        data = self.read_json()
        if data is None:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        path = self.route()
        if path == "/v1/demo/compose":
            pair = next(
                (item for item in demo_pairs() if item["test_id"] == data.get("test_id")),
                None,
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
            if scope in contexts and context_id:
                contexts[scope][context_id] = data.get("payload", {})
            self.send_json({"accepted": True})
        elif path == "/v1/tick":
            self.send_json({"actions": []})
        elif path == "/v1/reply":
            lower = data.get("message", "").strip().lower()
            if any(term in lower for term in ("stop messaging", "stop", "spam", "useless")):
                self.send_json({"action": "end"})
            elif any(term in lower for term in ("ok lets do it", "ok, lets do it", "whats next", "what's next")):
                self.send_json({
                    "action": "send",
                    "body": "Done — I’ll help you with the next step.",
                })
            else:
                self.send_json({"action": "wait", "wait_seconds": 5})
        else:
            self.send_json({"error": "Not found"}, 404)
