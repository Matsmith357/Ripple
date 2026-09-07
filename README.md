# Ripple — Checkpoint 2

> **Other agents complete your to-do list. Ripple discovers the to-do list you did not know existed.**

Ripple is a Strands Agents SDK prototype for recursively discovering consequences of a real-world change. This repository implements **Checkpoint 2 only** for one synthetic scenario: Alex Morgan moves from Indianapolis, Indiana, to Columbus, Ohio on a configurable date.

Checkpoint 2 preserves the Checkpoint 1 runtime-discovery engine and replaces its active mock evidence provider with curated snapshots of verified public sources. The runtime graph is still created by Strands reasoning and general-purpose tools. It is not loaded from an Ohio checklist.

## Architecture

```text
React UI
  → public tRPC mutation
  → request-scoped Node/Python bridge
  → Strands discovery agent
  → general spawn / duplicate guards
  → Strands recursive investigator
  → official evidence retrieval tool
  → deterministic trust and applicability guards
  → runtime consequence graph + source provenance
```

The Python worker begins with only the root move event and Alex's declared context. The discovery agent proposes direct consequence candidates. The investigator queries the official evidence catalog, records guarded conclusions, and may declare evidence-backed child candidates. The store validates source quality, node binding, Alex-specific trigger facts, deadlines, action claims, duplicate keys, causal child evidence, depth, and node budget before changing graph state.

## Status vocabulary

Every investigated node ends in exactly one Checkpoint 2 state:

| Status | Meaning |
| --- | --- |
| `RESOLVED` | No outstanding step remains. |
| `DOES_NOT_APPLY` | Trusted evidence defines a trigger and Alex's declared context negates it. |
| `ACTION_PREPARED` | Ripple prepared, but did not execute, an action supported by node-bound primary evidence. |
| `HUMAN_DECISION` | Trusted evidence establishes a genuine choice that Ripple should not make for Alex. |
| `UNKNOWN` | Evidence, source quality, applicability facts, or orchestration output is insufficient. |

Ripple never files, pays, changes insurance, submits a government action, or performs another consequential external action.

## Official evidence

`python/official_evidence.json` is the active catalog. `python/build_official_catalog.py` reproducibly builds it from `artifacts/cp2-official-source-research.json`. The catalog contains source URL, publisher, title, retrieved timestamp, exact excerpt, research context, structured facts, limitations, deadline metadata, destination, required items, source-derived context requirements, and a content hash.

Source quality is recomputed from URL host at load time:

- `PRIMARY_OFFICIAL`: allowlisted government or regulator host.
- `AUTHORITATIVE_SECONDARY`: allowlisted institutional secondary source.
- `UNVERIFIED`: any other host.
- `EVIDENCE_GAP`: no usable source.

A catalog-provided quality label cannot promote an untrusted host. Legal and administrative `ACTION_PREPARED` conclusions require at least one `PRIMARY_OFFICIAL` source attached to that exact node.

## Run locally

```bash
cd /home/ubuntu/ripple-checkpoint-1
sudo uv pip install --system -r python/requirements.txt
pnpm install
pnpm dev
```

The web server invokes the Python worker with a 179-second request timeout. The worker uses `OPENAI_API_BASE` / `OPENAI_API_KEY` in the sandbox and falls back to the managed Forge endpoint and credential in WebDev.

Run the engine directly:

```bash
python3 python/ripple_engine.py \
  --move-date 2026-10-01 \
  --max-depth 3 \
  --max-nodes 14
```

Rebuild and validate:

```bash
python3 python/build_official_catalog.py
pytest -q python/test_ripple_engine.py python/test_trust_layer.py
pnpm check
pnpm build
pnpm test -- --run
python3 python/validate_result.py path/to/runtime-result.json
```

## Validation artifacts

- `artifacts/checkpoint2-prior-live-runtime-graph.json` is a successful Strands-generated CP2 graph captured before the final source-applicability hardening.
- `artifacts/checkpoint2-prior-live-validation.json` shows that graph passing all 14 current runtime acceptance checks.
- `artifacts/CHECKPOINT_2_REPORT.md` distinguishes that prior live proof from the exact-code deterministic test results and the final live rerun blocker.
- `artifacts/checkpoint1-mock-evidence.json` is retained only as an archive. No active runtime code imports it.

## Current limitation

The final exact-code live rerun could not be completed in this build session because the configured model gateway returned HTTP 412 with `usage exhausted`. The engine now fails visibly in that condition instead of returning an empty graph. All deterministic Python tests, TypeScript checks, production build, and server tests pass. The earlier CP2 live Strands run passed all current graph validations, but it predates the last source-required applicability and payload-hardening changes. See the report for the complete disclosure.

Checkpoint 3 features were not started.
