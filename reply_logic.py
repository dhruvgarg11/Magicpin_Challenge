def handle_reply(data):
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

    return {
        "action": "send",
        "body": "I’m here to help. Tell me a little more about what you need, and I’ll suggest a practical next step.",
        "cta": "open_ended",
        "rationale": "Responding with a clarifying prompt because no specific intent was detected.",
    }