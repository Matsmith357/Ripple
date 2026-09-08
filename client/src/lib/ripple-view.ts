export type Evidence = {
  source_id: string;
  source_type: string;
  source_url: string | null;
  publisher: string;
  title: string;
  excerpt: string;
  retrieved_at: string;
  query: string;
  retrieval_context: string;
  supports: string[];
  limitations: string;
  deadline: { text: string; kind: string; days?: number } | null;
  destination: string | null;
  required_items: string[];
  synthetic: boolean;
};

export type PreparedAction = {
  what: string;
  why: string;
  when: string;
  deadline_source_id: string | null;
  where: string;
  need: string[];
  depends_on: string | null;
  decision_options: string[];
  status: string;
};

export type Applicability = {
  rule: string;
  why_applies: string;
  trigger_facts: string[];
  resolved_facts: Record<string, unknown>;
  unresolved_facts: string[];
};

export type ConsequenceNode = {
  id: string;
  title: string;
  domain: string;
  parent_id: string | null;
  depth: number;
  status: string;
  reason: string;
  evidence: Evidence[];
  discovered_by: string;
  spawned_consequences: string[];
  why_investigated: string;
  model_reasoning: string;
  caused_by_evidence_id: string | null;
  applicability: Applicability;
  action: PreparedAction;
  uncertainty: string[];
};

export type RippleRun = {
  checkpoint: number;
  run_id: string;
  generated_at: string;
  generated_at_runtime?: boolean;
  engine: string;
  model: string;
  evidence_mode: string;
  graph: {
    root_id: string;
    nodes: ConsequenceNode[];
    edges: Array<{ source: string; target: string }>;
  };
  activity: Array<{
    sequence: number;
    at: string;
    actor: string;
    kind: string;
    message: string;
    node_id: string | null;
  }>;
  safeguards: Record<string, string | number | null>;
};

export type GraphSummary = {
  discovered: number;
  actions: number;
  unknown: number;
  decisions: number;
  recursive: number;
  officialSources: number;
  maxDepth: number;
};

export type WalkthroughStep = {
  id: string;
  label: string;
  title: string;
  note: string;
  nodeId: string;
  status: string;
  targetSeconds: number;
};

export function childrenOf(nodes: ConsequenceNode[], parentId: string): ConsequenceNode[] {
  return nodes.filter(node => node.parent_id === parentId);
}

export function summarizeGraph(run: RippleRun): GraphSummary {
  const nonRoot = run.graph.nodes.filter(node => node.id !== run.graph.root_id);
  const sourceIds = new Set(
    nonRoot.flatMap(node =>
      node.evidence
        .filter(item => item.source_type === "PRIMARY_OFFICIAL" || item.source_type === "AUTHORITATIVE_SECONDARY")
        .map(item => item.source_id),
    ),
  );

  return {
    discovered: nonRoot.length,
    actions: nonRoot.filter(node => node.status === "ACTION_PREPARED").length,
    unknown: nonRoot.filter(node => node.status === "UNKNOWN").length,
    decisions: nonRoot.filter(node => node.status === "HUMAN_DECISION").length,
    recursive: nonRoot.filter(node => node.depth > 1 && Boolean(node.caused_by_evidence_id)).length,
    officialSources: sourceIds.size,
    maxDepth: Math.max(0, ...run.graph.nodes.map(node => node.depth)),
  };
}

export function deadlineEvidence(node: ConsequenceNode): Evidence | null {
  if (!node.action.deadline_source_id) return null;
  return node.evidence.find(item => item.source_id === node.action.deadline_source_id) ?? null;
}

export function isVerifiedPublicEvidence(item: Evidence): boolean {
  return !item.synthetic && (item.source_type === "PRIMARY_OFFICIAL" || item.source_type === "AUTHORITATIVE_SECONDARY");
}

export function isRuntimeGraph(run: RippleRun): boolean {
  return run.generated_at_runtime === true && run.graph.nodes.length > 1 && run.activity.some(event => event.kind === "spawned");
}

export function buildJudgeWalkthrough(run: RippleRun): WalkthroughStep[] {
  const nodes = run.graph.nodes;
  const root = nodes.find(node => node.id === run.graph.root_id);
  if (!root) return [];

  const action = nodes.find(node =>
    node.status === "ACTION_PREPARED"
    && node.parent_id !== null
    && node.evidence.some(isVerifiedPublicEvidence)
    && Boolean(node.action.deadline_source_id),
  ) ?? nodes.find(node => node.status === "ACTION_PREPARED" && node.parent_id !== null);
  const recursive = nodes.find(node => node.depth > 1 && Boolean(node.caused_by_evidence_id));
  const unknown = nodes.find(node => node.status === "UNKNOWN");
  const notApplicable = nodes.find(node => node.status === "DOES_NOT_APPLY");

  return [
    {
      id: "event",
      label: "01 · Event",
      title: "Start with Alex’s move",
      note: "One change and person context enter the system—no consequence checklist.",
      nodeId: root.id,
      status: root.status,
      targetSeconds: 25,
    },
    {
      id: "graph",
      label: "02 · Discovery",
      title: "Reveal the generated graph",
      note: `${nodes.length - 1} consequences across runtime-selected domains, with the tool trace available below.`,
      nodeId: root.id,
      status: root.status,
      targetSeconds: 35,
    },
    action && {
      id: "action",
      label: "03 · Action",
      title: action.title,
      note: "Show WHAT, WHY, WHEN, Alex-specific applicability, and the exact supporting source.",
      nodeId: action.id,
      status: action.status,
      targetSeconds: 45,
    },
    recursive && {
      id: "recursion",
      label: "04 · Recursion",
      title: recursive.title,
      note: `Depth ${recursive.depth}; created from parent evidence ${recursive.caused_by_evidence_id}.`,
      nodeId: recursive.id,
      status: recursive.status,
      targetSeconds: 35,
    },
    unknown && {
      id: "unknown",
      label: "05 · Trust",
      title: unknown.title,
      note: "Explain why missing or weak support becomes UNKNOWN instead of an invented obligation.",
      nodeId: unknown.id,
      status: unknown.status,
      targetSeconds: 35,
    },
    notApplicable && {
      id: "not-applicable",
      label: "06 · Context",
      title: notApplicable.title,
      note: "Show the rule and the Alex-specific fact that makes this consequence inapplicable.",
      nodeId: notApplicable.id,
      status: notApplicable.status,
      targetSeconds: 30,
    },
    {
      id: "complete",
      label: "07 · Complete",
      title: "Return to the full consequence map",
      note: "End on the runtime graph, its recursive branch, statuses, source count, and safe stop condition.",
      nodeId: root.id,
      status: root.status,
      targetSeconds: 20,
    },
  ].filter((step): step is WalkthroughStep => Boolean(step));
}
