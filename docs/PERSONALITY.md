# Conversational Personality — companion-voice-v1

This is a prompt and presentation-text update on `feat/mystery-pet-context`. It does not change
the conversation runtime, database schema, tools, write permissions, retrieval or model provider.

## Configuration and Integration

- `backend/app/personality.py` owns the shared disposition, the three existing temperament
  accents, and the reflection/unhelpful-feedback acknowledgements. Refine the voice here and
  bump `PERSONALITY_VERSION` when publishing a subsequent revision.
- `backend/app/assistance.py` keeps operational instructions separate and composes them with
  the voice and the validated temperament from the existing context profile. The same prompt
  is used for both the initial model call and the post-tool response.
- `AssistanceRun.policy.personality_version` records which version was applied. No extra
  model call, memory store, maturity stage, or visual feature is added.
- `backend/app/agent.py` uses the warmer reflection acknowledgement only after the existing
  journal-capture skill has actually handled the reflection. Vocabulary review remains intact.

All three presets retain the same intelligent, innocent, warm companion. Calm is gentler,
curious gives more room to a focused question about an unexplained personal detail, and playful
allows slightly more mischief. Explicit user requests for seriousness, precision, brevity or
no questions take precedence over those accents.

The profile's `name` is explicitly identified as the **companion's name**, not the user's name.
User-supplied names remain context data; arbitrary profile strings are not interpolated into
system instructions. Unknown temperament values fall back to the calm accent.

## Behavioral Changes

The former short prompt pushed creative work and a practical next step across conversation
types. It also encouraged raw-ID citations and allowed the model to recite its name/temperament.

The revised guidance instead supports:

- Purposeful curiosity about this person's routines, interests and project meaning, without
  pretending ignorance of ordinary technical knowledge or assigning invented motives.
- Affection through attention and useful conduct, not constant praise or emotional dependence.
- Brief company, situated celebration, and occasional playful observations without forcing tasks.
- Competent answers first when precision matters, including plain SQL or short factual answers.
- Natural personal recall; source IDs remain available and are cited when the user asks.
- No mandatory closing question, repeated introduction, baby talk, theatrical narration,
  invented monitoring, physical caretaking, or protective restrictions on the user's activity.

Task success, uncertainty and tool receipts remain factual. The application still appends its
authoritative server receipts after actions; the model is asked not to duplicate those receipts.
The text-only input capability is explicit, so warmth should not lead to offers to inspect
photos or audio that this interface cannot receive.

## Context and Memory

Existing recent conversation and current structured records supply the familiarity. A personal
explanation can inform the next turn without being permanently saved. The existing permission
gate still controls durable writes; no automatic profile-learning mechanism was introduced.

Consequently, a routine outside the recent context may be unavailable later unless it was stored
through an existing supported mechanism. Retrieval remains bounded and lexical/association-based.
Personality instructions do not create missing memories, improve retrieval by themselves, or
establish that the companion has learned new capabilities.

## Evaluation

`backend/evaluation/personality.json` contains 14 synthetic scenarios and 18 conversational
turns, including all three temperaments, multi-turn learning, no-advice venting, a serious moment,
technical accuracy under fatigue, corrected/unknown memory, and a real project-save workflow.

From `backend/`:

```bash
uv run python -m app.evaluate_personality
# Explicit live calls, using the existing provider configuration:
set -a; source ../.env; set +a
uv run python -m app.evaluate_personality --live
# Recheck only selected situations:
uv run python -m app.evaluate_personality --live --case purposeful-curiosity --case practical-save
```

Offline mode lists the cases without calling a model or claiming generated behavior. Live mode
uses the actual AgentRuntime, context construction, tool execution and persistence against a
fresh in-memory SQLite database per scenario. It never opens the personal application database.
Each turn retains the existing two-model-call/two-tool limit; the full suite has an upper bound
of 36 model attempts. Provider usage and latency are included; absent pricing remains unknown.

Automated flags catch some repetitive introductions, misplaced pet-name address, excessive
questions, dependency language, feigned ignorance, intrusive control, stage directions, invented
visual access and unsupported upload suggestions. These are triage signals, not semantic quality
scores. Expected saves and lack of unrequested writes are checked against real persisted state.
Human review remains necessary, especially for warmth, inferred motives and subtle over-helping.

Verification on this branch: **472 backend tests passed**, including PostgreSQL concurrency and
migration coverage, with zero skipped tests. Ruff and mypy passed. Frontend code was not changed.

## Observed Live Results and Limits

Azure GPT-5.4 was exercised through full scenario sweeps and targeted reruns, using synthetic
data only. The first pass exposed misaddressing the user as Mica, overlong companion monologues,
and unsolicited task lists. Later checks also exposed an unsupported photo-upload suggestion
and a tendency to explain a personal ritual instead of asking about it. The instructions and
review cases were refined in response.

Reviewed later outputs included:

- A focused question about what turning a notebook upside down does for the user, followed by
  using the explanation without asking again. The same routine was also checked with the calm
  and playful presets, which used different wording rather than a fixed curiosity template.
- Correct two-sentence HTTP 409/500 explanations and a bare PostgreSQL aggregation query when
  requested, without withholding help because the user mentioned fatigue.
- Quiet company without a question or a productivity plan, and brief, specific celebration.
- Correct reuse of the bench-sweep explanation and the corrected blue palette.
- Honest missing-memory responses and no durable save when permission was absent.
- An actual tool-backed save of the Lantern fox project, followed by a brief confirmation.

This is a small qualitative review, not proof that every response will comply. Some generations
still offer an optional next step or use stock phrasing; further tuning should follow real user
feedback rather than optimizing solely for lexical checks. Fixed briefings, vocabulary teaching,
error messages and the explicitly labeled deterministic development stub remain largely as before.

## Carrying the Change to the Operational Branch

The running WhatsApp/operations services were not restarted from this older branch. They continue
using their existing runtime until this change is carried over. The code and live evaluation on
this branch are updated; the operational deployment has not silently changed personality.

When merging, retain the destination branch's operational/tool rules and response-tracing hooks,
then compose those rules with `personality.py` for both model calls. In particular, do not replace
the operational branch's responsibility instructions with this branch's narrower capability rules.
No migration or permission changes are needed for the personality module itself.
