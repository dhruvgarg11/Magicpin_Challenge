# Vera AI Merchant Assistant

An AI-powered WhatsApp merchant assistant inspired by Vera. The system generates concise, contextual and actionable merchant messages using category, merchant, trigger and optional customer context.

## Approach

The solution follows a context-driven architecture:

`CategoryContext + MerchantContext + TriggerContext + CustomerContext → Message`

### Trigger-aware routing
The bot routes each trigger to a dedicated handler, including performance changes, recalls, refills, festivals, seasonal opportunities, competitor signals, research/CDE updates, regulations, milestones, dormant conversations and match-day opportunities.

### Personalization
Messages use available merchant and customer information such as business category, performance metrics, customer history, preferences, offers and trigger-specific facts.

### Safety and specificity
The implementation avoids inventing unavailable information. Placeholder triggers receive safe fallback messages rather than fabricated facts.

Messages are concise and use a single primary CTA.

### Deterministic output
`compose()` returns:

- `body`
- `cta`
- `send_as`
- `suppression_key`
- `rationale`

## Testing

- 30/30 provided test pairs generated successfully
- JSONL validation: PASS
- Placeholder scenarios handled safely
- Trigger-specific routing implemented

## Run

From the project root:

```bash
python3 -m py_compile bot.py
```

The final submission is:

`dataset/submission.jsonl`
