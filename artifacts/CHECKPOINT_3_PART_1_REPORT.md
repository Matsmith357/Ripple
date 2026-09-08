# Ripple — Checkpoint 3, Part 1 Report

**Status:** Experience implementation complete; waiting for Part 2  
**Scenario:** Alex Morgan moves from Indianapolis, Indiana, to Columbus, Ohio  
**Open gate:** Checkpoint 2 exact-code live verification remains blocked by external HTTP 412 usage exhaustion

## What changed

Ripple now opens with the competition message **“Something changed. What else does that change?”** The single Alex Morgan move is presented as a clear triggering event with a prominent **Discover Ripples** action. The pre-run state explicitly shows that no graph exists until Strands reasons from the event and person context.

The investigation state now presents the agent's method as a focused sequence: read the change, discover domains, retrieve public evidence, test applicability, follow second-order effects, and stop safely. These labels communicate the real workflow while the request is active; they do not pre-populate result nodes.

The result experience is reorganized around a wide, horizontally scrollable consequence graph. The move is the root. First-order consequences share a connected branch. Evidence-backed downstream consequences render beneath their actual parent. Nodes have distinct, restrained treatments for `ACTION_PREPARED`, `DOES_NOT_APPLY`, `HUMAN_DECISION`, `UNKNOWN`, and `RESOLVED`.

The selected-node inspector clearly separates **Source evidence** from **Ripple reasoning**. It displays the prepared action, deadline, destination, required items, prerequisites, applicability to Alex, official source links, deterministic source quality, source limitations, uncertainty, and recursion provenance. `UNKNOWN` receives an explicit trust explanation: Ripple stopped rather than guessed.

## Scope preservation

The Python Strands engine, model path, prompts, evidence catalog, validators, server bridge, recursion, provenance, applicability guards, uncertainty behavior, and stopping safeguards were not changed. No new person, event, integration, account system, submission capability, payment flow, mobile app, chatbot, or Checkpoint 3 packaging was added.

The Checkpoint 2 verification gate remains open. No static graph or archived graph was introduced into the product. The interface still accepts only the graph returned by the live tRPC/Strands request.

## Tests and verification

| Gate | Result |
| --- | --- |
| Checkpoint 1 and 2 Python engine/trust regressions | **24 passed** |
| Vitest server and UI view-model tests | **9 passed across 3 files** |
| TypeScript check | **PASS** |
| Production build | **PASS** |
| Desktop visual verification | **PASS** at 1280 × 900 |
| Mobile visual verification | **PASS** at 390 × 844 |
| Browser console | **PASS**, no output |
| Successful live result-state browser verification | **Not repeated**; the external CP2 model-capacity gate remains open |

The new view tests verify graph summaries, runtime-generation labeling, exact deadline-source binding, exclusion of synthetic input from verified-evidence counts, parent-child rendering, visible status distinctions, official source links, evidence-versus-reasoning separation, and intentional UNKNOWN language.

## Files changed

| File | Purpose |
| --- | --- |
| `client/src/pages/Home.tsx` | Competition narrative, event card, live investigation state, graph-centered result layout, trust statement, and trace disclosure. |
| `client/src/components/ripple/ConsequenceGraph.tsx` | Runtime-driven branching graph and status treatments. |
| `client/src/components/ripple/NodeInspector.tsx` | Action, applicability, evidence, reasoning, uncertainty, deadline, and recursion inspection. |
| `client/src/lib/ripple-view.ts` | Typed graph view model and pure runtime summary/provenance helpers. |
| `server/ripple-view.test.ts` | View-model and server-rendered presentation regressions. |

## Part 1 stopping point

Checkpoint 3 Part 1 is implemented and tested. **Checkpoint 3 is not declared complete.** Submission packaging has not begun. Ripple is ready for the user's Part 2 instructions, with the Checkpoint 2 live-verification requirement still explicitly open.
