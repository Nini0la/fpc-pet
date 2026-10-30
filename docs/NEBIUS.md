# Nebius Token Factory / NVIDIA Nemotron integration

## Status and boundary

Nebius is selectable through Mica's existing `OpenAICompatibleGateway`, native tools,
`AgentRuntime`, PostgreSQL records, scheduler and response traces. This is an inference-provider
integration. Model output still passes through the same domain validation and permission checks.
No model weights or GPU containers are needed on Modal.

Milestone 1 remains **implemented, tested but not fully confirmed**. Nebius/Nemotron is the
owner-directed immediate priority; Milestone 2 remains unstarted and Hermes remains a separate
runtime-integration follow-up. **The owner trial now uses Nebius/Nemotron**, switched on October 30
at approximately 08:57 UTC at revision `25f8959`. Azure is retained for manual rollback, not automatic
fallback. Owner-channel experience confirmation remains open. The requested three-interaction proof
passes: [exact model, traces, costs and receipts](NEBIUS_ACCEPTANCE.md).

## Model selection — verified documentation, not a live-model claim

The official API base is `https://api.tokenfactory.nebius.com/v1`.
The [November 2026 deprecation notice](https://docs.tokenfactory.nebius.com/model-deprecations-november-2026.md)
lists these replacements for models being retired on November 9:

| Retiring model | Recommended replacement |
| --- | --- |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | `nvidia/Nemotron-3_5-Lightning` |
| `nvidia/nemotron-3-super-120b-a12b` | `nvidia/Nemotron-3.5-Super-VL` |

The tested candidate is **`nvidia/Nemotron-3.5-Super-VL` with `NEBIUS_REASONING_EFFORT=low` and
`MODEL_MAX_OUTPUT_TOKENS=1200`**. It completed the six-scenario isolated application smoke and
punctuationless interruption check. Lightning passed the small native-tool preflight but failed
the longer proposal scenario in its initial evaluation; it is not qualified as the trial default.
Select an exact ID returned by the authenticated model list; there is no silently selected default
or fallback model. These checks establish a working profile, not long-run reliability or owner
acceptance. See the status file for failed attempts and fixes as well as the successful run.

## Private configuration

Add the key and selected model to the ignored root `.env`, preserving existing Azure settings:

```dotenv
NEBIUS_API_KEY=your-private-key
NEBIUS_MODEL=nvidia/Nemotron-3.5-Super-VL
NEBIUS_REASONING_EFFORT=low
MODEL_MAX_OUTPUT_TOKENS=1200
# Optional: defaults to the current official endpoint.
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
# Optional verified USD / million-token prices; omit when unknown.
# NEBIUS_INPUT_COST_PER_MILLION=...
# NEBIUS_OUTPUT_COST_PER_MILLION=...
```

`PROVIDER=nebius` and `MODEL_MODE=live` select it for a backend process. `NEBIUS_API_KEY` and
`NEBIUS_MODEL` are required. Selecting Nebius never falls back to Azure/generic credentials,
model names, reasoning settings or prices. Missing prices are reported as unknown, not zero.
The shared limits remain at most **1,200 output tokens** and **15 seconds per inference call**;
configure `MODEL_MAX_OUTPUT_TOKENS` and `MODEL_TIMEOUT_SECONDS` within those bounds. Do not
raise these limits merely to hide failed reasoning/tool compatibility: measure first.

Requests use bearer authentication, `max_tokens`, native function tools and `service_tier=default`
(no automatic over-limit tier), with `store=false`. They do not retry or silently change provider.
Nebius's nullable `tool_calls` is supported. Truncated/filtered responses and reasoning-only empty
responses are rejected before operational writes. Separate provider reasoning fields are not
copied into chat or the response trace.

Nebius request schemas inline local Pydantic `$defs` references so nested time fields have visible
object schemas. Backend validation still rejects stringified objects/`"None"`; it does not coerce
malformed model arguments into writes. Prompts explicitly require JSON types, saved activity starts,
and complete known proposal execution fields. Reminder confirmations use the validated receipt
rather than a model-predicted next-check time; this avoids stale schedule claims without adding
a second inference call for ordinary reminder confirmations.

## Verification sequence

Run from `backend/`. These commands load private configuration from the root `.env`; they do
not change the active provider or touch the owner database/channels:

```sh
uv run python -m app.nebius_check --models-only
uv run python -m app.nebius_check
```

The first command lists available Nemotron IDs with no inference. The second checks the selected
model against that list and makes at most two synthetic inference calls: a plain response and a
native tool request. The probe tool is never executed. Output contains provider/model/usage metadata,
not credentials or production conversation. Missing credentials yield an explicit blocked result.

Next, create a **new disposable local** `*_smoke_test` database and run the existing integrated
HTTP/PostgreSQL/worker scenarios (the main harness requires no existing users):

```sh
createdb mica_nebius_smoke_test
DATABASE_URL=postgresql+psycopg:///mica_nebius_smoke_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg:///mica_nebius_smoke_test PROVIDER=nebius uv run python -m tests.live_semantic_smoke
DATABASE_URL=postgresql+psycopg:///mica_nebius_smoke_test PROVIDER=nebius MICA_VARIANT_ONLY=1 uv run python -m tests.live_semantic_smoke
```

The harness covers disclosures/activity interruptions, next-local-time reminders, eight-minute
check-ins, proposal acceptance after an interruption/API restart, clarification timing, and real
worker execution with duplicate sweeps. Telegram/WhatsApp credentials are blank in the subprocess.
Reports record the selected provider, configured/returned model, call usage and tool results under
ignored `.local/rollouts/semantic-integration/`, with unique filenames so Azure evidence is preserved.
This proves isolated application behavior; actual owner-channel acceptance is a separate gate.

Automated `tests/test_nebius.py` uses a **fake HTTP model endpoint** with the real subprocess
transport, shared runtime, PostgreSQL and scheduler. Those tests verify the integration plumbing,
not Nemotron's semantic decisions or real Nebius availability.

## Deployment after live acceptance

From the repository root, using the exact tested/pinned source revision:

```sh
backend/.venv/bin/python deploy/prepare_trial.py refresh --provider nebius
```

This writes only the private runtime-secret input; it neither activates a new window nor changes
the existing expiry. It exports only the chosen provider's credentials/settings. Follow the existing
[Modal update procedure](MODAL_TRIAL.md#semantic-integration-update-procedure) to update the runtime
Secret and refresh containers. Do not rerun `activate` or extend the December 31 cutoff for a provider
change. Local API and cloud worker should use the same selected provider once switched.

Authenticated `inspect_runtime` returns provider and configured model as well as revision/schema.
Its optional connectivity probe reports the actual returned model. Existing response traces also
record the provider, requested model, returned model, usage and native-tool effects.

Rollback is a provider/configuration switch to the retained Azure settings with
`refresh --provider azure_openai` and a container refresh; no schema downgrade or data deletion is
needed. This helper prepares local Secret input only; executing it is not proof of a deployment.

## Sources checked October 30, 2026

- [Quickstart](https://docs.tokenfactory.nebius.com/quickstart.md)
- [Function calling](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling.md)
- [Chat completion API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion.md)
- [Public serverless endpoints](https://docs.tokenfactory.nebius.com/public-serverless.md)
- [November model deprecations](https://docs.tokenfactory.nebius.com/model-deprecations-november-2026.md)
