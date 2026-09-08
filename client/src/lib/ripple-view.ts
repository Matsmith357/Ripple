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
