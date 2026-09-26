import json
from functools import lru_cache
from pathlib import Path

from bot import compose

DATA = Path(__file__).parent / "dataset" / "expanded"


@lru_cache(maxsize=4)
def records(folder, id_field):
    result = {}
    for path in (DATA / folder).glob("*.json"):
        with path.open(encoding="utf-8") as source:
            item = json.load(source)
        if id_field in item:
            result[item[id_field]] = item
    return result


def record(folder, id_field, record_id):
    return records(folder, id_field).get(record_id)


def workspace(merchant_id=None):
    merchants = records("merchants", "merchant_id")
    triggers = records("triggers", "id")
    customers = records("customers", "customer_id")
    categories = records("categories", "slug")
    merchant_list = sorted(
        merchants.values(),
        key=lambda item: item.get("identity", {}).get("name", "").casefold(),
    )

    selected_id = merchant_id or (merchant_list[0]["merchant_id"] if merchant_list else None)
    merchant = merchants.get(selected_id)
    if merchant is None:
        return None

    merchant_triggers = [
        {**trigger, "customer": customers.get(trigger.get("customer_id"))}
        for trigger in triggers.values()
        if trigger.get("merchant_id") == selected_id
    ]
    merchant_triggers.sort(
        key=lambda item: (
            -int(item.get("urgency", 0)),
            item.get("expires_at") or "9999",
            item.get("id", ""),
        )
    )
    history = sorted(
        merchant.get("conversation_history", []),
        key=lambda item: item.get("ts", ""),
        reverse=True,
    )

    return {
        "merchants": [
            {
                "merchant_id": item["merchant_id"],
                "name": item.get("identity", {}).get("name", "Unnamed merchant"),
                "city": item.get("identity", {}).get("city"),
                "category_slug": item.get("category_slug"),
                "owner_name": item.get("identity", {}).get("owner_first_name"),
            }
            for item in merchant_list
        ],
        "merchant": merchant,
        "category": categories.get(merchant.get("category_slug")),
        "triggers": merchant_triggers,
        "activity": history,
        "recent_ai_messages": [
            entry for entry in history if entry.get("from") == "vera"
        ],
    }


def compose_for_merchant(merchant_id, trigger_id, customer_id=None):
    merchant = records("merchants", "merchant_id").get(merchant_id)
    trigger = records("triggers", "id").get(trigger_id)
    if merchant is None or trigger is None or trigger.get("merchant_id") != merchant_id:
        return None

    customer_id = customer_id or trigger.get("customer_id")
    customer = records("customers", "customer_id").get(customer_id) if customer_id else None
    if customer_id and (customer is None or customer.get("merchant_id") != merchant_id):
        return None

    category = records("categories", "slug").get(merchant.get("category_slug"))
    if category is None:
        return None

    return {
        "message": compose(category, merchant, trigger, customer),
        "merchant": merchant,
        "category": category,
        "trigger": trigger,
        "customer": customer,
    }