# Ripple — Judge Demo Walkthrough

**Target duration:** 3–4 minutes  
**Scenario:** Alex Morgan moves from Indianapolis, Indiana, to Columbus, Ohio  
**Demo rule:** Run the live Strands workflow. Do not substitute an archived graph, static consequence list, or mocked result.

## Presenter setup

Open Ripple on a desktop viewport before recording. Keep the default move date or choose a date before the run. Verify that the initial graph area says **“The graph does not exist yet.”** This opening state is part of the proof: Ripple has the event and Alex's context, but no consequence tree.

If the model gateway returns a capacity error, stop the recording attempt. Do not splice an archived graph into a claimed live run. A successful recording should preserve the visible run ID at the top of the completed graph.

## Timed walkthrough

| Time | Screen action | Presenter narrative | Proof to leave visible |
| --- | --- | --- | --- |
| 0:00–0:25 | Frame the headline and Alex's event card. | “Something changed: Alex moved from Indiana to Ohio. Other agents help complete a list you already know. Ripple discovers the tasks and decisions that were never on that list.” | Alex Morgan, Indianapolis → Columbus, move date, and empty graph. |
| 0:25–0:45 | Point to the empty graph, then select **Discover Ripples**. | “Ripple receives one event and Alex's declared facts—not an Ohio checklist. The consequence graph does not exist yet.” | “No predetermined consequence tree” and the button click. |
| 0:45–1:20 | Let the live investigation state run. | “Strands is orchestrating general tools: it discovers candidate domains, retrieves authoritative evidence, tests whether each rule applies to Alex, follows evidence-backed downstream effects, and stops under deterministic safeguards.” | Live investigation phases. Do not cut in a way that implies predetermined nodes. |
| 1:20–1:45 | On completion, pause on the graph header and zoom or pan across first-order branches. Open the agent/tool trace briefly. | “The list was discovered at runtime. These domains and nodes came from the Strands run. The trace shows tool calls, and the run ID ties this screen to this exact graph.” | Multiple first-order domains, runtime-generated badge, run ID, and trace. |
| 1:45–2:25 | Use the **Judge walkthrough** guide's Action step. It selects a live `ACTION_PREPARED` node with verified evidence and, when available, a traced deadline. | “Ripple separates preparation from execution. Here is WHAT Alex should do, WHY the rule applies to this person, WHEN the source supports a deadline, WHERE to go, what is needed, and any prerequisite.” | Action card, Alex-specific applicability, deadline source ID, official link, and `PRIMARY_OFFICIAL` quality. |
| 2:25–2:50 | Advance to the Recursion step. | “This is not a flat checklist. The child sits under its actual parent at depth two or greater. Ripple created it because the parent evidence revealed another material consequence.” | Child branch, depth, and `caused_by_evidence_id` recursion provenance. |
| 2:50–3:15 | Advance to the Trust step for a live `UNKNOWN` node. | “When public evidence or Alex-specific facts are insufficient, Ripple refuses to invent an obligation. UNKNOWN is an intentional trust outcome, not a hidden error.” | UNKNOWN status, uncertainty, and “Ripple stopped rather than guessed.” |
| 3:15–3:35 | Advance to the Context step for a live `DOES_NOT_APPLY` node. | “Evidence alone is not enough. Ripple also checks applicability. This consequence does not apply because Alex's declared context negates the rule's trigger.” | The rule, `DOES_NOT_APPLY`, and Alex-specific trigger facts. |
| 3:35–3:55 | Advance to Complete and return to the graph root. | “Ripple ends with a consequence map: actions to prepare, consequences that do not apply, uncertainties that should remain unknown, and real second-order branches—all tied to evidence and stopped safely.” | Completed graph, status mix, source count, recursive badge, run ID, and stop reason. |

The runtime-derived guide omits a step if the successful graph does not contain the required status. For the competition recording, use a successful run that naturally demonstrates `ACTION_PREPARED`, a recursive child, `UNKNOWN`, and `DOES_NOT_APPLY`. Do not rename or hard-code nodes to force those beats.

## Judge questions to anticipate

| Question | Concise answer |
| --- | --- |
| “Is this an Ohio checklist?” | No. The product starts with only the move and Alex's context. Strands discovers candidate consequences and invokes general-purpose tools. Deterministic code validates evidence, applicability, causality, duplication, and stopping; it does not supply a final tree. |
| “Why should I trust the action?” | The node shows its retrieved source, publisher, URL, timestamp, excerpt, query context, deterministic source class, Alex-specific trigger facts, and deadline source. Source evidence is visibly separate from model reasoning. |
| “Could Ripple hallucinate a deadline?” | A deadline is shown only when its exact evidence ID is bound to that node and the excerpt supports it. Otherwise WHEN is `UNKNOWN`. |
| “What makes this agentic?” | Strands performs discovery, tool selection, investigation, conclusion reasoning, and recursive orchestration. Consequences can create new pending investigations until safeguards stop the run. |
| “Does Ripple take actions for Alex?” | No. Checkpoint 3 prepares actions only. It does not file, pay, update insurance, submit government forms, or make a human decision. |

## Recording acceptance checklist

A usable competition take shows one uninterrupted live run from **Discover Ripples** to a completed graph. It includes the run ID, at least one official evidence link, a traced deadline when supported, one recursive child with causal evidence, one intentional UNKNOWN, one contextual DOES_NOT_APPLY, and the final graph. The browser console should remain clear, and no archived graph should be presented as the current run.
