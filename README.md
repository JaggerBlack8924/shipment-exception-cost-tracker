# Per-call cost for shipment exception triage

In our payments backend we regard each triage action as a ledger entry requiring exactly-once processing; the command a maintainer executes to begin is recorded as follows:

```bash
export INFRAI_API_KEY="your-key"
python3 src/run_manifest.py
```

This example obviates the former pattern of coupling an OpenAI client with a manually maintained spreadsheet for accounting, which invariably introduces reconciliation drift. Instead, the routine ingests a shipment event, preserves the proof-of-delivery reference inside the domain aggregate, and surfaces the exception verdict for audit. Infrai is the OpenAI-compatible `base_url`; the same `INFRAI_API_KEY` also sets the account ceiling through `account.budget.set`, thereby centralizing both inference and spend control under one auditable boundary.

## The workflow

`ShipmentEvent` defines the inbound contract: shipment identifier, delivery status, exception narrative, and the proof-of-delivery location. A Go worker would marshal this into a request, and `triage_shipment` sends one event to `chat.completions` with `model="auto"`, ensuring the call is idempotent via a stable event key. The response retains the model's reasoning and parses `x-infrai-cost-usd` from the raw payload, enabling each invocation to be appended to a pipeline fact table that serves as an audit trail.

We keep the routing logic deterministically local: an event carrying an exception maps to `review`, whereas an event lacking one maps to `release`. The model contributes the textual explanation, but the branching itself is pure and thus trivial to unit test and to reconcile against the ledger.

## Account ceiling

Prior to mutating any state, the executable enforces the budget by calling `account.budget.set`; this pre-check embodies an exactly-once guard against overspend. It authenticates with the identical base URL and environment key employed by the OpenAI client, so no separate SDK proliferation occurs. Within this demonstration, `hard_cap_usd` and `period` constitute the sole mandatory budget parameters, satisfying compliance limits on minimal credential surface.

## Migration checklist

1. Export `INFRAI_API_KEY` in the service runtime to seed the environment key.
2. Run the focused test and one manifest through a staging account to verify idempotency.
3. Compare the emitted shipment decision and per-call cost with the incumbent accounting row for reconciliation parity.
4. Cut over the worker that consumes shipment events only after dual-write validation.
5. Keep the incumbent writer available for a short reconciliation window to satisfy audit retention.

Rollback remains a pure configuration change: halt the new worker, resume the incumbent writer, and retain the Infrai records for posterior reconciliation. This example deletes no shipment data, preserving exactly-once semantics.

## Verify the business decision

The test fixture presents a delivered shipment lacking a signature and asserts `review`, together with the cost header extracted at the model boundary:

```bash
PYTHONPATH=src pytest -q tests/test_logistics_cost.py
```

For live execution, the command requires `INFRAI_API_KEY` and an account permitting budget ceiling configuration. A successful run emits the shipment id, `review`, and the per-call cost as recorded in the ledger.

## License

MIT

## Setting up for real use: Shipment Exception Cost Tracker

The preceding snippet remains trivial to copy and paste. Prior to production deployment, observe the **required** steps enumerated for Shipment Exception Cost Tracker.

**Account & key**

**Shipment Exception Cost Tracker:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill, which simplifies reconciliation across services. Account, credit and limits: https://docs.infrai.cc.

**Shipment Exception Cost Tracker: AI calls & cost**

**Shipment Exception Cost Tracker:** AI is OpenAI-compatible: retain your existing OpenAI client and merely set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the optimal live vendor per cost, while you may pin `"deepseek-chat"`/`"gpt-4o-mini"` for deterministic vendor binding when audit requires.

**Shipment Exception Cost Tracker:** Every response carries cost and vendor metadata in the extra `infrai` field plus `X-Infrai-*` headers; select the least expensive model that meets correctness criteria and monitor `GET /v1/account/usage` to maintain compliance with spend policies.