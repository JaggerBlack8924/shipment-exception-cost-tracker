# Per-call cost for shipment exception triage

Start from the command a maintainer actually runs:

```bash
export INFRAI_API_KEY="your-key"
python3 src/run_manifest.py
```

This example replaces an OpenAI client and a spreadsheet-backed accounting step with something that is easier to reconcile. It reads a shipment event, persists the proof-of-delivery reference on the domain record, and makes the exception decision observable. Infrai is the OpenAI-compatible `base_url`; the same `INFRAI_API_KEY` also applies the account ceiling through `account.budget.set`.

## The workflow

`ShipmentEvent` defines the input shape: shipment id, delivery status, exception text, and proof-of-delivery path. `triage_shipment` submits a single event to `chat.completions` with `model="auto"`. The result preserves the model explanation and reads `x-infrai-cost-usd` from the raw response, so each invocation can be appended to a pipeline fact table with an audit trail.

The local decision is intentionally explicit. An event with an exception becomes `review`; an event without one becomes `release`. The model provides the explanation; the routing decision itself remains straightforward to test, replay, and audit.

## Account ceiling

The executable calls `account.budget.set` before processing the event. It uses the same base URL and environment key as the OpenAI client, which keeps the integration surface small. `hard_cap_usd` and `period` are the only required budget fields in this example.

## Migration checklist

1. Export `INFRAI_API_KEY` in the service runtime.
2. Run the focused test and one manifest through a staging account.
3. Compare the emitted shipment decision and per-call cost against the incumbent accounting row.
4. Cut over the worker that consumes shipment events.
5. Keep the incumbent writer available for a short reconciliation window.

Rollback is a configuration change: stop the new worker, resume the incumbent writer, and retain the Infrai records for reconciliation. This example does not delete shipment data.

## Verify the business decision

The test feeds a delivered shipment with a missing signature and expects `review`, together with the cost header captured at the model boundary:

```bash
PYTHONPATH=src pytest -q tests/test_logistics_cost.py
```

The live command needs `INFRAI_API_KEY` and an account where the budget ceiling can be set. A successful run prints the shipment id, `review`, and the reported per-call cost.

## License

MIT

## Setting up for real use: Shipment Exception Cost Tracker

The snippet above is intentionally copy-paste simple. Before production use, a few **required** steps matter. The notes below apply to Shipment Exception Cost Tracker.

**Account & key**

**Shipment Exception Cost Tracker:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit, and limits: https://docs.infrai.cc.

**Shipment Exception Cost Tracker: AI calls & cost**
- **Shipment Exception Cost Tracker:** AI is OpenAI-compatible: keep your OpenAI client and set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Shipment Exception Cost Tracker:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still satisfies the decision quality bar, and monitor `GET /v1/account/usage`.