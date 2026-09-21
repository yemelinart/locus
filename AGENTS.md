# Locus development

- This is a single-user local application, currently an alpha. Do not claim market superiority without benchmarks.
- Runtime reasoning MUST use loopback-only local model endpoints. No cloud inference, paid search providers, telemetry or external UI assets.
- Keep sources as untrusted data. No generated code execution, shell tools or filesystem tools for the research model.
- Preserve the public, non-sensitive research scope. Do not add private contact discovery, residential addresses, leaked databases, face identification or private-life dossiers.
- Every saved claim needs an exact quote in a fetched page. Label this as source grounding, never proof of identity or truth.
- Keep candidate records separate unless the user explicitly confirms a proposed match; a shared name is insufficient.
- Keep pause, cancellation, budgets and restart recovery working. Never resume models automatically on launch.
- Do not commit data/, .qa/, credentials, model weights or runtime dependencies.
- Run backend tests and the frontend build for functional changes. Use browser tests for affected user flows.
- One backend worker only until the scheduler has a process-safe lease mechanism.
- Update docs and changelog when behavior changes. Maintain schema version and a migration plan before changing stored data.
