# Ripple — Judging Alignment

Ripple is an Everyday Agents prototype built around one proposition: **a consequential life change creates work the person may not know to ask about**. The Alex Morgan interstate-move demo shows how Strands can discover, investigate, and recursively expand that hidden work while deterministic controls preserve evidence quality and uncertainty.

## Criteria mapping

| Criterion | Demonstrated feature | What the judge can verify |
| --- | --- | --- |
| **Technical Implementation** | Strands performs candidate discovery, tool selection, evidence retrieval orchestration, conclusion reasoning, and recursive investigation. General tools operate over person context, domains, graph state, and evidence rather than an Ohio-specific checklist. | Start from the empty graph, run Ripple, inspect multiple runtime domains, open the tool trace, select a depth-two child, and inspect its causal source ID. |
| **Technical Implementation** | Deterministic guards enforce source classification, node-bound evidence, Alex-specific applicability, deadline traceability, action grounding, duplicate prevention, already-investigated prevention, causal children, depth, node budget, and safe stopping. | Open an action with its source-bound deadline; compare it with UNKNOWN and DOES_NOT_APPLY. Review the validation and red-team test suites. |
| **Design** | The experience follows one narrative: event, live investigation, runtime graph, selected consequence, and trust explanation. The graph is the visual center, while detail remains available without obscuring causality. | Use Discover Ripples, follow the result graph, and use the runtime-derived judge guide to move through action, recursion, uncertainty, and applicability. |
| **Design** | Statuses use distinct but restrained visual treatments. UNKNOWN explicitly communicates safe restraint. Source evidence and Ripple reasoning occupy separate panels. | Open nodes with different statuses and compare the inspector sections. |
| **Potential Impact** | The architecture can help a person identify administrative, civic, financial, and logistical consequences that are easy to miss after a life change. | Observe that one move produces several domains and at least one downstream requirement while irrelevant consequences are excluded. |
| **Potential Impact** | The system prepares evidence-backed actions but does not execute consequential external operations. This supports informed human action without silent filings or payments. | Inspect WHAT, WHY, WHEN, WHERE, NEED, and DEPENDS ON; confirm the footer and architecture boundary. |
| **Creativity & Originality** | Ripple addresses consequence discovery rather than known-task completion. Its graph model makes second-order effects first-class and treats uncertainty as a visible result. | Compare the empty pre-run state with the generated parent-child graph and the intentional UNKNOWN node. |
| **Presentation** | The Alex scenario gives the audience one understandable event, a visible transformation, and a clear ending within approximately four minutes. | Follow `docs/DEMO_WALKTHROUGH.md` and keep the exact runtime run ID visible. |

## Responsible claim boundary

Ripple does not claim to provide legal advice, guarantee complete coverage, or replace an agency, insurer, employer, or professional. The public evidence catalog is a curated Checkpoint 2 retrieval layer and is designed to be replaceable with live source connectors. A conclusion remains `UNKNOWN` when evidence or applicability is insufficient. Prepared actions are informational and are not executed.

## Evidence for implementation quality

The repository includes deterministic unit and red-team tests, TypeScript validation, production build checks, a runtime graph validator with 14 Checkpoint 2 assertions, a source-controlled architecture diagram, and browser-verified desktop and mobile layouts. The unresolved HTTP 412 capacity issue for final exact-code live Strands verification remains disclosed rather than being bypassed.

## References

[1]: https://strandsagents.com/ "Strands Agents SDK Documentation"
