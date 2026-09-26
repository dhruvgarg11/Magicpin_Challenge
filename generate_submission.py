import json
from pathlib import Path
from bot import compose

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset" / "expanded"

with open(DATASET / "test_pairs.json") as f:
    pairs = json.load(f)["pairs"]

def load_json(folder, filename):
    with open(DATASET / folder / filename) as f:
        return json.load(f)

with open(ROOT / "dataset" / "categories" / "dentists.json") as f:
    pass

# Map category slug from merchant data
categories = {}
for p in (DATASET / "categories").glob("*.json"):
    with open(p) as f:
        data = json.load(f)
    categories[data["slug"]] = data

rows = []

for pair in pairs:
    merchant = load_json("merchants", pair["merchant_id"] + ".json")
    trigger = load_json("triggers", pair["trigger_id"] + ".json")

    customer = None
    if pair.get("customer_id"):
        customer = load_json("customers", pair["customer_id"] + ".json")

    category = categories[merchant["category_slug"]]

    result = compose(category, merchant, trigger, customer)

    rows.append({
        "test_id": pair["test_id"],
        **result
    })

with open(DATASET / "submission.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"Generated {len(rows)} submission rows.")
