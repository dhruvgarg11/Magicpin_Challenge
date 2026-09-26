def handle_reply(data, merchant=None):
    message = data.get("message", "")
    if not isinstance(message, str):
        message = ""

    lower = " ".join(message.lower().split())

    if any(term in lower for term in (
        "stop messaging",
        "don't contact",
        "do not contact",
        "unsubscribe",
        "remove me",
        "not interested",
        "spam",
        "useless",
    )) or lower == "stop":
        return {
            "action": "end",
            "rationale": "Respecting the request to stop or decline further messages.",
        }

    if any(term in lower for term in (
        "busy",
        "not now",
        "later",
        "remind me",
        "give me time",
        "think about it",
        "get back to you",
    )):
        return {
            "action": "wait",
            "wait_seconds": 1800,
            "rationale": "The merchant asked for time; backing off for 30 minutes.",
        }

    if any(term in lower for term in (
        "ok lets do it",
        "ok, lets do it",
        "okay lets do it",
        "okay, let's do it",
        "what's next",
        "whats next",
        "go ahead",
        "sounds good",
        "yes, send",
        "send it",
        "let's do it",
        "lets do it",
    )):
        return {
            "action": "send",
            "body": "Done — I’ll help you with the next step. What would you like to work on first?",
            "cta": "open_ended",
            "rationale": "Acknowledging the merchant's positive response and inviting the next step.",
        }

    if "thank you for contacting us" in lower:
        return {
            "action": "wait",
            "wait_seconds": 1800,
            "rationale": "The message appears to be an automated acknowledgement.",
        }

    if merchant:
        performance = merchant.get("performance", {})
        metrics = {
            "views": ("profile views", performance.get("views")),
            "impressions": ("profile views", performance.get("views")),
            "calls": ("calls", performance.get("calls")),
            "directions": ("direction requests", performance.get("directions")),
            "leads": ("leads", performance.get("leads")),
        }
        requested_metric = next(
            (value for key, value in metrics.items() if key in lower),
            None,
        )
        if requested_metric and isinstance(requested_metric[1], (int, float)):
            label, value = requested_metric
            period = performance.get("window_days")
            period_text = f" over the last {period} days" if period else ""
            return {
                "action": "send",
                "body": (
                    f"{merchant.get('identity', {}).get('name', 'Your business')} "
                    f"recorded {value:,} {label}{period_text}."
                ),
                "cta": "open_ended",
                "rationale": "Answering from the selected merchant's recorded performance context.",
            }

        if "offer" in lower or "promotion" in lower:
            active_offers = [
                offer.get("title")
                for offer in merchant.get("offers", [])
                if offer.get("title") and offer.get("status") == "active"
            ]
            if active_offers:
                return {
                    "action": "send",
                    "body": (
                        f"The active offer recorded for "
                        f"{merchant.get('identity', {}).get('name', 'your business')} "
                        f"is {', '.join(active_offers[:3])}."
                    ),
                    "cta": "open_ended",
                    "rationale": "Answering from offers recorded in the selected merchant context.",
                }
            return {
                "action": "send",
                "body": "I don’t have an active offer recorded for this merchant yet. Tell me what you’re considering and I can help shape it.",
                "cta": "open_ended",
                "rationale": "No active offer is present in the selected merchant context.",
            }

    merchant_name = merchant.get("identity", {}).get("name") if merchant else None
    greeting = f"I’m here to help {merchant_name}." if merchant_name else "I’m here to help."
    return {
        "action": "send",
        "body": f"{greeting} Tell me a little more about what you need, and I’ll suggest a practical next step.",
        "cta": "open_ended",
        "rationale": "Responding with a clarifying prompt because no specific intent was detected.",
    }