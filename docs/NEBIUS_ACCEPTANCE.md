# Nemotron through Mica — three-interaction acceptance evidence

**Result: PASS**, October 30, 2026, approximately 08:22 UTC.

This is a real provider/application/worker run, not a connection-only probe or a mocked model.
Application revision: `25f8959` (runtime implementation `8e25def`), with the new acceptance
harness in `backend/tests/live_nebius_acceptance.py` and opt-in process network guard in
`backend/tests/provider_guard/sitecustomize.py`. No application runtime changes were needed.

## Exact provider and execution environment

- **Provider:** Nebius Token Factory, `https://api.tokenfactory.nebius.com/v1/chat/completions`.
- **Requested and returned NVIDIA model on every call:** `nvidia/Nemotron-3.5-Super-VL`.
- **Settings:** reasoning `low`, max output 1,200 tokens, per-call deadline 15 seconds,
  `service_tier=default`, `store=false`.
- **Application:** actual FastAPI Mica HTTP server on loopback port 8015, native model tool calls,
  existing validated domain operations, PostgreSQL persistence and response inspector.
- **Database:** fresh local `mica_nebius_proof_smoke_test`, schema `0014`, synthetic owner data.
- **Delivery:** real Mica **in-app chat message** created by a separate scheduler process against
  the wall clock. This run does not claim Telegram delivery or a production provider switch.
- **Isolation:** the API process received only Nebius model credentials. No Azure configuration or
  credentials were inherited. The worker received no model credentials and could reach only local
  services under the test guard. Production owner records and the running Azure trial were unchanged.

## Interaction results and measured latency

One context-setting message precedes the three requested interactions, for four model calls total.
Model latency is the existing gateway measurement; HTTP latency covers the whole app request.

| Turn | Result | Model latency | HTTP latency | Input tokens | Output tokens | Estimated USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Context setup | Acknowledged three classmates, three-minute demo, coding confidence/explanation nerves; no tool call | 2.199 s | 2.666 s | 12,120 | 231 | $0.0038439 |
| 1. Contextual conversation | Used the preceding audience/time constraints to suggest an opening and a 0:30–2:00 / 2:00–3:00 demo structure; no tool call | 3.031 s | 3.129 s | 12,300 | 518 | $0.0041562 |
| 2. Commitment creation | Native `create_commitment` call executed and persisted version 1 with source provenance | 2.604 s | 2.759 s | 12,552 | 248 | $0.0039888 |
| 3. Reminder scheduling | Native `schedule_reminder` call persisted a one-time reminder after 30 seconds | 2.732 s | 2.869 s | 12,882 | 285 | $0.0041211 |
| **Total** | **Four real Nemotron calls** | | | **49,854** | **1,282** | **$0.0161100** |

### Cost source and interpretation

Authenticated `GET https://api.tokenfactory.nebius.com/v1/models?verbose=true` returned:

- Prompt: `$0.0000003/token` = **$0.30 / million tokens**.
- Completion: `$0.0000009/token` = **$0.90 / million tokens**.
- Cached input: `$0.00000006/token` = **$0.06 / million tokens**.
- Per-request price: zero in the returned metadata.

The run configured Mica's cost estimator with those prompt/completion rates before inference.
Each trace contains measured token counts and a non-null `cost_usd`. The table is an **uncached
list-price estimate**, not an invoice/account debit; caching discounts and credits can reduce it.
The worker made no inference calls, so its incremental model-inference cost was **$0**.
Local worker/database compute is not included in the inference estimate.

## Tool execution receipts

### Commitment

User input:

> Please save a commitment titled 'Rehearse the Mica demo'. The next action is 'Write the opening
> sentence'. It is complete when I can deliver the three-minute demo without notes. Do not enable
> check-ins for this commitment.

Model-generated tool call `chatcmpl-tool-9f267a7d4f3e7da6` selected `create_commitment` with the
requested title, next action, completion criteria and `followup_enabled=false`.

Verified database receipt:

```json
{
  "id": "d783e1a4-61d1-40ff-ac7d-dce27f6eeefe",
  "version": 1,
  "state": "open",
  "title": "Rehearse the Mica demo",
  "next_action": "Write the opening sentence",
  "completion_criteria": "I can deliver the three-minute demo without notes",
  "followup_enabled": false,
  "provenance_links": 1
}
```

Assistance run: `39d2b808-fca8-4cae-b233-adf965f952d4`.
Assistant message: `f3367155-295a-4db4-a79b-aa6c2b80db0f`.

### Reminder and unattended delivery

User input:

> Remind me once in 30 seconds to rehearse the Mica demo.

Model-generated call `chatcmpl-tool-b2a8f026165b9fc2` selected `schedule_reminder`:

```json
{
  "topic": "rehearse the Mica demo",
  "mode": "once",
  "when": {"kind": "after", "seconds": 30, "anchor": "message", "timezone": "UTC"}
}
```

The harness stopped the API after scheduling, started the actual `app.scheduler --personal-only`
process, waited for the real due instant, and read the resulting message from PostgreSQL.

| Evidence | Value |
| --- | --- |
| Plan | `4cba99d2-16b6-4c97-b601-8b6d5cbcd5a6` |
| Scheduling assistance run | `f259709b-5f72-496d-97f5-d546ff1496f9` |
| Scheduled action | `79db4331-71bc-400d-8ec2-a0bfac060c9a` |
| Worker event | `92dc0a17-4622-4ed2-b314-46abf75daddd` |
| Delivered message | `0a9503e9-16a6-4346-b4d0-667c4225742c` |
| Due | `2026-10-30T08:22:47.753667+00:00` |
| Completed | `2026-10-30T08:22:51.630339+00:00` |
| Due-to-delivery lag | **3.877 seconds** |
| Action result | `succeeded`, `reminder_saved_in_app`, one attempt |
| Delivered text | `Reminder: rehearse the Mica demo.` |
| Plan after execution | `completed` |

After stopping the worker, a second real one-shot sweep returned
`{"prepared":0,"executed":0,"failures":0}`. The database still contained exactly one scheduled
action. Restarting the API exposed the successful action through the existing response-context
endpoint for the delivered message. No model call was used to inspect the evidence.

## Proof that Azure was not used

1. Every persisted provider trace says `provider=nebius`, and both requested and returned models
   match `nvidia/Nemotron-3.5-Super-VL`.
2. The test API's environment is built from an allowlist, not inherited root `.env` contents.
   Azure credentials/config-file settings and generic model credentials are absent.
3. An opt-in Python process audit guard applies to the API and its actual gateway subprocesses.
   It permits inference HTTP only to `api.tokenfactory.nebius.com`; other external DNS/inference
   destinations are blocked and logged. The report reconciles request count with persisted calls.
4. Audit results: **four Nebius inference requests, zero Azure requests, zero blocked attempts**.
5. Both worker invocations had no model credentials; the worker guard blocks external connections.
   **Zero worker inference requests** were observed, and the AssistanceRun count was unchanged
   across unattended delivery and the duplicate sweep.

This proves the requested NVIDIA-on-Nebius → Mica conversation/tool → durable unattended-action
path. Formal competition eligibility is distinct from this technical execution evidence.

## Reproduce and inspect

From `backend/`, after adding `NEBIUS_API_KEY` to the ignored root `.env`, use a new local database:

```sh
createdb mica_nebius_proof_smoke_test
DATABASE_URL=postgresql+psycopg:///mica_nebius_proof_smoke_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg:///mica_nebius_proof_smoke_test uv run python -m tests.live_nebius_acceptance
```

The harness refuses existing users/nonlocal/non-`*_smoke_test` databases. Use a different fresh
database name when repeating; preserve this run's evidence. It requests synthetic content only.

Private full request/response traces, tool arguments/results, costs and network audit:

```text
.local/rollouts/nebius-acceptance/20261030T082207Z/results.json
.local/rollouts/nebius-acceptance/20261030T082207Z/provider-network.jsonl
```

Validation: actual acceptance run **passed**; Ruff passed for application/tests/deploy; mypy passed
for 39 application modules; `git diff --check` passed. This slice adds test/evidence files, not
production runtime changes. The previously passing 585-test suite was not redundantly rerun.
