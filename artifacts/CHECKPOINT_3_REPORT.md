# Ripple — Checkpoint 3 Report

**Author:** Manus AI  
**Scenario:** Alex Morgan moves from Indianapolis, Indiana, to Columbus, Ohio  
**Scope:** Competition experience and submission readiness; no new life events or product features

## Executive conclusion

Checkpoint 3 is **implemented and ready for submission preparation review**. Ripple now presents a coherent 3–4 minute judge experience, a runtime-derived demonstration guide, a competition architecture diagram, a public-repository README, dependency and test instructions, an MIT license, Strands usage documentation, synthetic-scenario and pre-existing-work disclosures, known limitations, and judging-criteria alignment.

The core Strands engine, model path, official evidence layer, prompts, trust guards, recursion, statuses, validators, and stopping safeguards remain unchanged from the accepted Checkpoint 2 implementation. The final exact-code Checkpoint 2 live verification is still **BLOCKED** by an external HTTP 412 `usage exhausted` response. No graph was produced or accepted during the Checkpoint 3 retry. This gate remains explicit and is the principal submission gap.

## Demo walkthrough

The walkthrough in `docs/DEMO_WALKTHROUGH.md` targets approximately 3 minutes 55 seconds. It begins with Alex's move and the intentionally empty graph, shows the live Strands investigation, establishes that the consequence list was generated rather than supplied, and then moves through action preparation, official evidence, applicability, a traced deadline, recursive discovery, intentional `UNKNOWN`, contextual `DOES_NOT_APPLY`, and the completed graph.

The product includes a **Judge walkthrough** guide after a successful run. Its node targets are computed from the actual graph. It selects a supported action, a depth-two-or-greater evidence-backed child, an `UNKNOWN`, and a `DOES_NOT_APPLY` by status and provenance. If a required proof node is absent, the guide omits that beat rather than fabricating or renaming a node.

## Architecture

The editable Mermaid source and rendered PNG identify three explicit responsibility boundaries.

| Boundary | Responsibility |
| --- | --- |
| **Strands reasoning and tool orchestration** | Candidate discovery, tool selection, evidence-aware conclusion reasoning, and recursive investigation. |
| **Retrieved evidence** | Authoritative public-source records with URLs, publishers, titles, timestamps, excerpts, query context, structured facts, and limitations. |
| **Deterministic safeguards** | Source classification, node binding, Alex-specific applicability, deadline and action grounding, duplicate and already-investigated protection, causal child validation, depth, node budget, terminal statuses, and safe stopping. |

Accepted nodes become the runtime graph and then the action/evidence experience. The diagram visually separates **source evidence** from **Ripple reasoning**.

## Repository readiness

The repository now contains the complete application source, Python engine, official evidence catalog and builder, validators, tests, Dockerfile, package lock, Python requirements, competition documents, diagram source and render, checkpoint artifacts, and MIT license. The README provides setup, local execution, direct-engine execution, validation, test, build, evidence, Strands, status, limitation, synthetic-scenario, and pre-existing-work documentation.

Repository hygiene was updated to exclude Python bytecode and pytest caches. Credentials remain excluded through `.env` ignore rules. The project has not been published or submitted.

## Judging alignment

`docs/JUDGING_ALIGNMENT.md` maps visible evidence to the five requested criteria. Technical Implementation is demonstrated by live Strands tool orchestration and deterministic trust guards. Design is demonstrated by the event-to-investigation-to-graph flow and clear status/evidence hierarchy. Potential Impact is framed as discovering easy-to-miss consequences while preparing rather than executing actions. Creativity and Originality are demonstrated by consequence discovery, recursive graph structure, and uncertainty as a first-class outcome. Presentation is supported by one understandable scenario, a timed script, and a runtime-derived guide.

No “first ever,” complete-coverage, professional-advice, or guaranteed-correctness claim is made.

## Validation

| Gate | Result |
| --- | --- |
| Checkpoint 1 and 2 Python engine/trust regressions | **24 passed** |
| TypeScript check | **PASS** |
| Vitest | **11 passed across 3 files** |
| Production build | **PASS** |
| Architecture source/render | **PASS**, Mermaid + 3120 × 1924 PNG |
| Desktop browser validation | **PASS** at 1280 × 900 |
| Mobile browser validation | **PASS** at 390 × 844 |
| Browser console | **PASS**, no output |
| Successful live result-state browser validation | **BLOCKED** because the exact-code model request returned HTTP 412 before producing a graph |
| CP2 exact-code live Strands retry | **BLOCKED**, HTTP 412 `usage exhausted`; no graph accepted |

The production build completed with one non-blocking Vite chunk-size warning. No dependency, type, test, or build failure remains.

## Checkpoint 2 open gate

The exact current engine was invoked with the Alex move, maximum depth 3, and node budget 14. The model gateway returned HTTP 412 `usage exhausted` before any consequence graph was produced. The 14 runtime validators therefore could not run against a new graph. No mock, alternate provider, archived graph, weakened validator, or product bypass was used.

A prior live Checkpoint 2 graph remains archived for provenance, but it predates final hardening and is not represented as exact-code verification. The active UI never loads it.

## Remaining submission gaps

The required fresh exact-code live Strands graph must still be produced, pass all 14 runtime validators, be archived with its run ID, and be browser-inspected in the final competition experience. After that, the team should record the live 3–4 minute walkthrough and complete the competition platform's submission fields. Publication and submission were intentionally not performed.

## Files added or updated

| File | Purpose |
| --- | --- |
| `client/src/components/ripple/DemoGuide.tsx` | Runtime-derived judge navigation. |
| `client/src/lib/ripple-view.ts` | Walkthrough selection by live status and provenance. |
| `client/src/pages/Home.tsx` | Judge guide integration and final Checkpoint 3 labeling. |
| `server/ripple-view.test.ts` | Dynamic walkthrough regressions. |
| `docs/DEMO_WALKTHROUGH.md` | Timed live-demo script and recording acceptance criteria. |
| `docs/architecture.mmd` | Source-controlled architecture diagram. |
| `docs/architecture.png` | Rendered competition diagram. |
| `docs/JUDGING_ALIGNMENT.md` | Criteria-to-demonstration mapping. |
| `README.md` | Public competition repository documentation. |
| `LICENSE` | MIT license. |
| `.gitignore` | Python cache and pytest-state exclusions. |

## Final verdict

Checkpoint 3 passes if judged on the requested experience, documentation, architecture, repository, and local validation deliverables. The project is not yet fully submission-ready because the explicitly preserved Checkpoint 2 exact-code live verification remains blocked by external gateway capacity. This report therefore records **Checkpoint 3: PASS, with one external pre-submission verification gate still open**.

## References

[1]: https://strandsagents.com/ "Strands Agents SDK Documentation"
