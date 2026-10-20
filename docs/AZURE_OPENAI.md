# Azure OpenAI

The existing gateway supports both generic OpenAI-compatible endpoints and Azure's
deployment-scoped Chat Completions API. The same permissions, tool limits, context builder,
and wall-clock deadline apply to both.

## Backend Configuration

```dotenv
MODEL_MODE=live
PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-10-21
MODEL_MAX_OUTPUT_TOKENS=600
MODEL_TIMEOUT_SECONDS=15
# Only set this for models supporting the requested reasoning effort:
MODEL_REASONING_EFFORT=none
```

Use the Azure **deployment name**, not just a model family name. The endpoint must be the
resource root. The gateway builds `/openai/deployments/{deployment}/chat/completions` and
adds `api-version`. Azure receives an `api-key` header and `max_completion_tokens`.
Unlike generic providers, Azure receives no `tool_choice` field when no tools are offered.

For local reuse of existing credentials, set `AZURE_OPENAI_CONFIG_FILE` to a server-local
dotenv file containing the four `AZURE_OPENAI_*` settings above. Only those four settings
are imported; explicit environment settings take precedence. The key is not copied into
source or into the local project configuration. Missing/invalid settings fail closed.
For deployment, provide the four values through the deployment's secret/environment system.

The ignored root `.env` in this checkout is configured for the existing Azure deployment and
a separate local PostgreSQL database named `mystery_pet`. It uses the locally running PostgreSQL
instance rather than Docker. No pre-existing application database was modified.

From `backend`, load the root configuration before starting:

```bash
set -a
source ../.env
set +a
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

From `frontend`, run `npm run dev`. The local access code is the `ACCESS_CODE` value in `.env`.
The local authentication settings are development-only; use fresh secrets for deployment.

## Live Verification

Deployment `edge-imci-gpt-5-4` returned model identity `gpt-5.4-2026-03-05`.
Actual Azure requests were made using synthetic records in an isolated temporary database:

- Created a project through the native `save_project` tool and persisted its receipt.
- Created an idea linked to that project through `save_idea`.
- Logged out/in and recalled both saved records from constructed context.
- Corrected the protagonist's instrument from violin to cello; the next response used cello.
- Explicit unhelpful feedback triggered deterministic clarification without a model call.
- A second account had no project evidence and the real model acknowledged missing information.

The final core workflow used six model calls, 6,960 reported input tokens and 779 reported output
tokens; the second-account check was an additional call. These are observed values for one run,
not a guaranteed cost or token budget. Price estimates remain unknown until input/output
per-million prices are configured. No general improvement over the comparison baseline is claimed.

Regression verification: 186 gateway/Azure/config/assistance tests passed, along with Ruff and
mypy. These tests are offline; they do not consume Azure credits. The synthetic live checks
were separately executed, not added as automatically billed CI tests.
