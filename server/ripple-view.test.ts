import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ConsequenceGraph } from "../client/src/components/ripple/ConsequenceGraph";
import { NodeInspector } from "../client/src/components/ripple/NodeInspector";
import {
  deadlineEvidence,
  isRuntimeGraph,
  isVerifiedPublicEvidence,
  summarizeGraph,
  type ConsequenceNode,
  type Evidence,
  type RippleRun,
} from "../client/src/lib/ripple-view";

const officialEvidence: Evidence = {
  source_id: "OFFICIAL-1",
  source_type: "PRIMARY_OFFICIAL",
  source_url: "https://bmv.ohio.gov/new-to-ohio.aspx",
  publisher: "Ohio BMV",
  title: "New Ohio Residents",
  excerpt: "Transfer requirements apply.",
  retrieved_at: "2026-09-08T00:00:00Z",
  query: "license transfer",
  retrieval_context: "Official source research",
  supports: ["Transfer requirement"],
  limitations: "",
  deadline: { text: "Within 30 days", kind: "relative_days", days: 30 },
  destination: "Ohio BMV",
  required_items: [],
  synthetic: false,
};

function node(partial: Partial<ConsequenceNode>): ConsequenceNode {
  return {
    id: "node",
    title: "Consequence",
    domain: "test",
    parent_id: "root_move",
    depth: 1,
    status: "UNKNOWN",
    reason: "Reason",
    evidence: [],
    discovered_by: "Strands",
    spawned_consequences: [],
    why_investigated: "Why",
    model_reasoning: "Reasoning",
    caused_by_evidence_id: null,
    applicability: {
      rule: "Rule",
      why_applies: "Why",
      trigger_facts: [],
      resolved_facts: {},
      unresolved_facts: [],
    },
    action: {
      what: "UNKNOWN",
      why: "Why",
      when: "UNKNOWN",
      deadline_source_id: null,
      where: "UNKNOWN",
      need: [],
      depends_on: null,
      decision_options: [],
      status: "UNKNOWN",
    },
    uncertainty: [],
    ...partial,
  };
}

function runFixture(): RippleRun {
  const root = node({ id: "root_move", title: "Interstate Move", parent_id: null, depth: 0, status: "RESOLVED" });
  const action = node({
    id: "license",
    title: "Transfer license",
    status: "ACTION_PREPARED",
    evidence: [officialEvidence],
    spawned_consequences: ["documents"],
    action: {
      ...root.action,
      what: "Transfer license",
      status: "ACTION_PREPARED",
      deadline_source_id: officialEvidence.source_id,
    },
  });
  const child = node({
    id: "documents",
    title: "Gather identity documents",
    parent_id: "license",
    depth: 2,
    status: "ACTION_PREPARED",
    evidence: [officialEvidence],
    caused_by_evidence_id: officialEvidence.source_id,
  });
  const unknown = node({ id: "voter", title: "Voter eligibility", status: "UNKNOWN" });

  return {
    checkpoint: 2,
    run_id: "run_live_123",
    generated_at: "2026-09-08T00:00:00Z",
    generated_at_runtime: true,
    engine: "Strands Agents SDK",
    model: "gpt-5-mini",
    evidence_mode: "VERIFIED PUBLIC SOURCES",
    graph: {
      root_id: root.id,
      nodes: [root, action, child, unknown],
      edges: [
        { source: root.id, target: action.id },
        { source: action.id, target: child.id },
        { source: root.id, target: unknown.id },
      ],
    },
    activity: [{ sequence: 1, at: "now", actor: "tool", kind: "spawned", message: "spawned", node_id: action.id }],
    safeguards: { stop_reason: "NO_NEW_CONSEQUENCES" },
  };
}

describe("Ripple competition view model", () => {
  it("summarizes only runtime consequences and proves evidence-backed recursion", () => {
    const summary = summarizeGraph(runFixture());
    expect(summary).toEqual({
      discovered: 3,
      actions: 2,
      unknown: 1,
      decisions: 0,
      recursive: 1,
      officialSources: 1,
      maxDepth: 2,
    });
  });

  it("requires runtime metadata and spawn activity before labeling a graph runtime-generated", () => {
    const runtime = runFixture();
    expect(isRuntimeGraph(runtime)).toBe(true);
    expect(isRuntimeGraph({ ...runtime, generated_at_runtime: false })).toBe(false);
    expect(isRuntimeGraph({ ...runtime, activity: [] })).toBe(false);
  });

  it("finds the exact node-bound deadline source", () => {
    const action = runFixture().graph.nodes.find(item => item.id === "license")!;
    expect(deadlineEvidence(action)?.source_id).toBe("OFFICIAL-1");
    expect(deadlineEvidence({ ...action, action: { ...action.action, deadline_source_id: "OTHER" } })).toBeNull();
  });

  it("never presents synthetic scenario input as verified public evidence", () => {
    expect(isVerifiedPublicEvidence(officialEvidence)).toBe(true);
    expect(isVerifiedPublicEvidence({ ...officialEvidence, synthetic: true })).toBe(false);
    expect(isVerifiedPublicEvidence({ ...officialEvidence, source_type: "EVIDENCE_GAP" })).toBe(false);
  });

  it("renders actual parent-child structure and distinct consequence states", () => {
    const runtime = runFixture();
    const root = runtime.graph.nodes[0];
    const markup = renderToStaticMarkup(
      createElement(ConsequenceGraph, {
        root,
        nodes: runtime.graph.nodes,
        selectedId: "license",
        onSelect: () => undefined,
      }),
    );

    expect(markup).toContain("Moved from Indiana to Ohio");
    expect(markup).toContain("Transfer license");
    expect(markup).toContain("Gather identity documents");
    expect(markup).toContain("Action prepared");
    expect(markup).toContain("Unknown");
  });

  it("renders official evidence separately from Ripple reasoning and explains UNKNOWN", () => {
    const runtime = runFixture();
    const action = runtime.graph.nodes.find(item => item.id === "license")!;
    const unknown = runtime.graph.nodes.find(item => item.id === "voter")!;
    const actionMarkup = renderToStaticMarkup(createElement(NodeInspector, { node: action }));
    const unknownMarkup = renderToStaticMarkup(createElement(NodeInspector, { node: unknown }));

    expect(actionMarkup).toContain("Source evidence");
    expect(actionMarkup).toContain("Ripple reasoning");
    expect(actionMarkup).toContain("https://bmv.ohio.gov/new-to-ohio.aspx");
    expect(actionMarkup).toContain("Primary official");
    expect(actionMarkup).toContain("Deadline traced to Ohio BMV");
    expect(unknownMarkup).toContain("Ripple stopped rather than guessed");
  });
});
