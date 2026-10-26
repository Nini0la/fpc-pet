## Mica product and milestone contract

Read `docs/MICA_TARGET.md` before planning significant changes.
The active implementation mission is `docs/milestones/01_AUTONOMY.md`.
Maintain reproducible findings, changes and acceptance-test results in `docs/IMPLEMENTATION_STATUS.md`.

Implement and verify the current milestone, not alternate architectures or future milestones.
Inspect the actual code and current branch before assuming the prior review is accurate.
Prefer existing FastAPI/PostgreSQL/worker patterns and Azure inference during Milestone 1.
Do not add Hermes, Letta or Nebius/Nemotron simply for completeness.
Do not claim success without integrated behavior and recorded evidence.
Never send external messages, expose multi-user access, or alter production data without explicit authorization.
