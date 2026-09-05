from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

from strands import Agent, tool
from strands.models.openai import OpenAIModel

Status = Literal[
    "RESOLVED",
    "DOES_NOT_APPLY",
    "ACTION_NEEDED",
    "HUMAN_DECISION",
    "UNKNOWN",
]
TERMINAL_STATUSES: set[str] = {
    "RESOLVED",
    "DOES_NOT_APPLY",
    "ACTION_NEEDED",
    "HUMAN_DECISION",
    "UNKNOWN",
}

DEFAULT_SCENARIO: dict[str, Any] = {
    "person": {
        "name": "Alex Morgan",
        "citizenship": "United States",
        "drivers_license": {"held": True, "state": "Indiana"},
        "vehicle": {"owns_personally": True, "state": "Indiana"},
        "auto_insurance": True,
        "employer": True,
        "voter_registration": {"registered": True, "state": "Indiana"},
        "professional_license": False,
        "children": False,
        "business": False,
        "government_benefits": False,
        "work_location": None,
    },
    "event": {
        "type": "interstate_move",
        "from_city": "Indianapolis",
        "from_state": "Indiana",
        "to_city": "Columbus",
        "to_state": "Ohio",
        "move_date": "2026-10-01",
    },
}


@dataclass
class Evidence:
    source_id: str
    source_type: str
    publisher: str
    title: str
    excerpt: str
    retrieved_at: str
    query: str
    synthetic: bool = True


@dataclass
class Node:
    id: str
    title: str
    domain: str
    parent_id: str | None
    depth: int
    status: str
    reason: str
    evidence: list[dict[str, Any]]
    discovered_by: str
    spawned_consequences: list[str] = field(default_factory=list)
    why_investigated: str = ""
    model_reasoning: str = ""
    created_order: int = 0


class EvidenceProvider:
    """Replaceable evidence interface. Checkpoint 1 uses only controlled mock records."""

    def search(self, query: str, domain: str, limit: int = 4) -> list[Evidence]:
        raise NotImplementedError


class MockEvidenceProvider(EvidenceProvider):
    def __init__(self, path: Path, clock: callable | None = None) -> None:
        payload = json.loads(path.read_text())
        self.catalog_version = payload["catalog_version"]
        self.label = payload["label"]
        self.documents = payload["documents"]
        self.clock = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @staticmethod
    def _tokens(value: str) -> set[str]:
        low_information = {
            "after",
            "address",
            "another",
            "before",
            "change",
            "check",
            "from",
            "indiana",
            "material",
            "move",
            "moving",
            "ohio",
            "person",
            "requirement",
            "required",
            "resident",
            "rule",
            "service",
            "state",
            "update",
            "within",
        }
        aliases = {"dmv": "bmv", "licensing": "license", "licenses": "license"}
        return {
            aliases.get(token, token)
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if len(token) > 2 and token not in low_information
        }

    def search(self, query: str, domain: str, limit: int = 4) -> list[Evidence]:
        query_tokens = self._tokens(f"{query} {domain}")
        domain_tokens = self._tokens(domain)
        ranked: list[tuple[int, dict[str, Any]]] = []
        for document in self.documents:
            searchable = " ".join(
                [
                    document["title"],
                    document["content"],
                    " ".join(document["domains"]),
                    " ".join(document["keywords"]),
                ]
            )
            document_tokens = self._tokens(searchable)
            document_domain_tokens = self._tokens(
                f"{' '.join(document['domains'])} {document['title']}"
            )
            score = len(query_tokens & document_tokens)
            domain_relevant = any(
                left == right or left.startswith(right) or right.startswith(left)
                for left in domain_tokens
                for right in document_domain_tokens
                if min(len(left), len(right)) >= 3
            )
            if score >= 2 and domain_relevant:
                ranked.append((score, document))
        ranked.sort(key=lambda item: (-item[0], item[1]["source_id"]))
        return [
            Evidence(
                source_id=document["source_id"],
                source_type=document["source_type"],
                publisher=document["publisher"],
                title=document["title"],
                excerpt=document["content"],
                retrieved_at=self.clock(),
                query=query,
                synthetic=True,
            )
            for _, document in ranked[:limit]
        ]


class InvestigationStore:
    def __init__(
        self,
        scenario: dict[str, Any],
        evidence_provider: EvidenceProvider,
        max_depth: int = 3,
        max_nodes: int = 24,
    ) -> None:
        self.scenario = scenario
        self.evidence_provider = evidence_provider
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.run_id = f"run_{uuid.uuid4().hex[:10]}"
        self.activity: list[dict[str, Any]] = []
        self.nodes: dict[str, Node] = {}
        self.retrieved_evidence: dict[str, Evidence] = {}
        self.node_evidence_ids: dict[str, set[str]] = {}
        self.normalized_index: dict[str, str] = {}
        self.sequence = 0
        self.safeguards = {
            "duplicate_blocks": 0,
            "already_investigated_blocks": 0,
            "max_depth_blocks": 0,
            "max_nodes_blocks": 0,
            "missing_evidence_coercions": 0,
            "stop_reason": None,
        }
        root = Node(
            id="root_move",
            title=(
                f"Interstate Move: {scenario['event']['from_state']} → "
                f"{scenario['event']['to_state']}"
            ),
            domain="life event",
            parent_id=None,
            depth=0,
            status="RESOLVED",
            reason="The synthetic move event is the investigation trigger.",
            evidence=[
                {
                    "source_id": "SYNTHETIC-EVENT-001",
                    "source_type": "SYNTHETIC_SCENARIO",
                    "publisher": "Ripple demo input",
                    "title": "Configured interstate move",
                    "excerpt": json.dumps(scenario["event"], sort_keys=True),
                    "retrieved_at": self._now(),
                    "query": "initial event",
                    "synthetic": True,
                }
            ],
            discovered_by="configured event input",
            why_investigated="Root event supplied to Ripple.",
            model_reasoning="No inference: this node records the supplied event.",
            created_order=self._next_sequence(),
        )
        self.nodes[root.id] = root
        self.normalized_index[self._normalize(root.title, root.domain)] = root.id
        self.log("engine", "run_started", f"Created {root.title}", root.id)

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _next_sequence(self) -> int:
        self.sequence += 1
        return self.sequence

    @staticmethod
    def _normalize(title: str, domain: str) -> str:
        terms = re.findall(r"[a-z0-9]+", f"{domain} {title}".lower())
        ignored = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"}
        return " ".join(term for term in terms if term not in ignored)

    def log(self, actor: str, kind: str, message: str, node_id: str | None = None) -> None:
        self.activity.append(
            {
                "sequence": len(self.activity) + 1,
                "at": self._now(),
                "actor": actor,
                "kind": kind,
                "message": message,
                "node_id": node_id,
            }
        )

    def find_existing(self, title: str, domain: str) -> Node | None:
        node_id = self.normalized_index.get(self._normalize(title, domain))
        return self.nodes.get(node_id) if node_id else None

    def spawn(
        self,
        title: str,
        domain: str,
        parent_id: str,
        why: str,
        discovered_by: str,
        caused_by_evidence_id: str | None = None,
    ) -> dict[str, Any]:
        parent = self.nodes.get(parent_id)
        if not parent:
            return {"accepted": False, "reason": "parent_not_found"}
        normalized_domain = domain.strip().lower().replace("_", " ")
        event_domain = str(self.scenario["event"]["type"]).lower().replace("_", " ")
        if normalized_domain in {
            event_domain,
            "move",
            "move planning",
            "relocation",
            "life event",
            "general",
            "administration",
        }:
            self.log(
                "guard",
                "invalid_domain",
                f"Rejected event-shaped domain '{domain}'; a specific topical domain is required.",
                parent_id,
            )
            return {
                "accepted": False,
                "reason": "invalid_domain",
                "instruction": "Use a specific topical category such as the subject of the consequence, not the event type.",
            }
        existing = self.find_existing(title, domain)
        if existing:
            self.safeguards["duplicate_blocks"] += 1
            self.log(
                "guard",
                "duplicate_prevented",
                f"Reused existing node '{existing.title}'.",
                existing.id,
            )
            return {"accepted": False, "reason": "duplicate", "existing_node_id": existing.id}
        depth = parent.depth + 1
        if depth > self.max_depth:
            self.safeguards["max_depth_blocks"] += 1
            self.log(
                "guard",
                "max_depth_reached",
                f"Blocked '{title}' at depth {depth}; maximum is {self.max_depth}.",
                parent_id,
            )
            return {"accepted": False, "reason": "max_depth", "max_depth": self.max_depth}
        if parent_id != "root_move":
            allowed_ids = self.node_evidence_ids.get(parent_id, set())
            evidence = self.retrieved_evidence.get(caused_by_evidence_id or "")
            if not evidence or evidence.source_id not in allowed_ids:
                self.log(
                    "guard",
                    "child_evidence_missing",
                    f"Blocked child '{title}' because its causal source was not retrieved for the parent.",
                    parent_id,
                )
                return {"accepted": False, "reason": "child_evidence_missing"}
            child_terms = MockEvidenceProvider._tokens(f"{title} {domain}")
            evidence_terms = MockEvidenceProvider._tokens(f"{evidence.title} {evidence.excerpt}")
            if len(child_terms & evidence_terms) < 2:
                self.log(
                    "guard",
                    "child_evidence_mismatch",
                    f"Blocked child '{title}' because its claim was not supported by the causal source.",
                    parent_id,
                )
                return {"accepted": False, "reason": "child_evidence_mismatch"}
        if len(self.nodes) >= self.max_nodes:
            self.safeguards["max_nodes_blocks"] += 1
            self.log("guard", "max_nodes_reached", f"Blocked '{title}'.", parent_id)
            return {"accepted": False, "reason": "max_nodes", "max_nodes": self.max_nodes}
        node_id = f"c_{self._next_sequence():02d}_{uuid.uuid4().hex[:6]}"
        node = Node(
            id=node_id,
            title=title.strip(),
            domain=domain.strip().lower(),
            parent_id=parent_id,
            depth=depth,
            status="PENDING",
            reason="Pending investigation.",
            evidence=[],
            discovered_by=discovered_by,
            why_investigated=why,
            model_reasoning="",
            created_order=self.sequence,
        )
        self.nodes[node_id] = node
        self.normalized_index[self._normalize(title, domain)] = node_id
        parent.spawned_consequences.append(node_id)
        self.log("agent", "consequence_discovered", f"Discovered '{title}' in {domain}.", node_id)
        return {"accepted": True, "node_id": node_id, "depth": depth}

    def search_evidence(self, node_id: str, query: str, domain: str) -> dict[str, Any]:
        node = self.nodes.get(node_id)
        if not node:
            return {"ok": False, "reason": "node_not_found"}
        results = self.evidence_provider.search(query=query, domain=domain)
        if not results:
            gap = Evidence(
                source_id=f"EVIDENCE-GAP-{uuid.uuid4().hex[:8]}",
                source_type="EVIDENCE_GAP",
                publisher="Ripple evidence guard",
                title="No controlled evidence matched the query",
                excerpt=(
                    "The controlled Checkpoint 1 evidence catalog returned no matching source. "
                    "The consequence must remain UNKNOWN unless another retrieved source resolves it."
                ),
                retrieved_at=self._now(),
                query=query,
                synthetic=True,
            )
            results = [gap]
        for item in results:
            self.retrieved_evidence[item.source_id] = item
            self.node_evidence_ids.setdefault(node_id, set()).add(item.source_id)
        self.log(
            "tool",
            "evidence_retrieved",
            f"Retrieved {len(results)} controlled source(s) for '{node.title}'.",
            node_id,
        )
        return {
            "ok": True,
            "evidence_label": "CONTROLLED MOCK/SYNTHETIC EVIDENCE",
            "results": [asdict(item) for item in results],
        }

    def record(
        self,
        node_id: str,
        status: str,
        reason: str,
        evidence_ids: list[str],
        model_reasoning: str,
    ) -> dict[str, Any]:
        node = self.nodes.get(node_id)
        if not node:
            return {"ok": False, "reason": "node_not_found"}
        if node.status in TERMINAL_STATUSES:
            self.safeguards["already_investigated_blocks"] += 1
            self.log(
                "guard",
                "already_investigated",
                f"Blocked a second conclusion for '{node.title}'.",
                node_id,
            )
            return {"ok": False, "reason": "already_investigated", "status": node.status}
        if status not in TERMINAL_STATUSES:
            status = "UNKNOWN"
            reason = f"Invalid requested status was guarded. {reason}".strip()
        evidence = [
            asdict(self.retrieved_evidence[source_id])
            for source_id in evidence_ids
            if source_id in self.retrieved_evidence
            and source_id in self.node_evidence_ids.get(node_id, set())
        ]
        if not evidence:
            self.safeguards["missing_evidence_coercions"] += 1
            status = "UNKNOWN"
            evidence = [
                asdict(
                    Evidence(
                        source_id=f"EVIDENCE-GAP-{uuid.uuid4().hex[:8]}",
                        source_type="EVIDENCE_GAP",
                        publisher="Ripple evidence guard",
                        title="Conclusion lacked retrieved evidence",
                        excerpt=(
                            "No evidence returned by investigate_domain was attached. "
                            "Ripple coerced the conclusion to UNKNOWN."
                        ),
                        retrieved_at=self._now(),
                        query=node.title,
                        synthetic=True,
                    )
                )
            ]
            reason = f"Insufficient retrieved evidence. {reason}".strip()
        if any(item["source_type"] == "EVIDENCE_GAP" for item in evidence):
            status = "UNKNOWN"
        node.status = status
        node.reason = reason.strip() or "No reason supplied; treated as unresolved."
        node.evidence = evidence
        node.model_reasoning = model_reasoning.strip() or node.reason
        self.log("agent", "consequence_recorded", f"{node.title} → {node.status}", node_id)
        return {"ok": True, "node_id": node_id, "status": node.status}

    def pending_nodes(self) -> list[Node]:
        return sorted(
            (node for node in self.nodes.values() if node.status == "PENDING"),
            key=lambda node: node.created_order,
        )

    def force_unknown(self, node_id: str, reason: str) -> None:
        node = self.nodes[node_id]
        if node.status != "PENDING":
            return
        gap = Evidence(
            source_id=f"EVIDENCE-GAP-{uuid.uuid4().hex[:8]}",
            source_type="EVIDENCE_GAP",
            publisher="Ripple engine guard",
            title="Investigation ended without an evidence-backed conclusion",
            excerpt=reason,
            retrieved_at=self._now(),
            query=node.title,
            synthetic=True,
        )
        self.retrieved_evidence[gap.source_id] = gap
        self.record(node_id, "UNKNOWN", reason, [gap.source_id], reason)

    def result(self, model_id: str, strands_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        ordered = sorted(self.nodes.values(), key=lambda node: node.created_order)
        edges = [
            {"source": node.parent_id, "target": node.id}
            for node in ordered
            if node.parent_id is not None
        ]
        return {
            "checkpoint": 1,
            "run_id": self.run_id,
            "generated_at": self._now(),
            "generated_at_runtime": True,
            "engine": "Strands Agents SDK",
            "model": model_id,
            "evidence_mode": "CONTROLLED MOCK/SYNTHETIC",
            "scenario": self.scenario,
            "graph": {"root_id": "root_move", "nodes": [asdict(node) for node in ordered], "edges": edges},
            "activity": self.activity,
            "safeguards": self.safeguards,
            "strands_metrics": strands_metrics,
        }


class RippleEngine:
    def __init__(
        self,
        scenario: dict[str, Any] | None = None,
        max_depth: int = 3,
        max_nodes: int = 24,
        model_id: str = "gpt-5-mini",
        evidence_path: Path | None = None,
    ) -> None:
        self.scenario = json.loads(json.dumps(scenario or DEFAULT_SCENARIO))
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.model_id = model_id
        self.evidence_path = evidence_path or Path(__file__).with_name("mock_evidence.json")

    def _model(self) -> OpenAIModel:
        api_key = os.getenv("BUILT_IN_FORGE_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("BUILT_IN_FORGE_API_URL") or os.getenv("OPENAI_API_BASE")
        if not api_key or not base_url:
            raise RuntimeError("No managed LLM credentials are available to the Strands worker.")
        normalized_url = base_url.rstrip("/")
        if not normalized_url.endswith("/v1"):
            normalized_url = f"{normalized_url}/v1"
        return OpenAIModel(
            client_args={"api_key": api_key, "base_url": normalized_url},
            model_id=self.model_id,
            stream=False,
            params={
                "max_completion_tokens": 5000,
                "extra_body": {"reasoning": {"effort": "low"}},
            },
        )

    @staticmethod
    def _metric_summary(result: Any, phase: str, node_id: str | None = None) -> dict[str, Any]:
        try:
            summary = result.metrics.get_summary()
        except Exception:
            summary = {}
        return {"phase": phase, "node_id": node_id, "summary": summary}

    def run(self) -> dict[str, Any]:
        provider = MockEvidenceProvider(self.evidence_path)
        store = InvestigationStore(
            scenario=self.scenario,
            evidence_provider=provider,
            max_depth=self.max_depth,
            max_nodes=self.max_nodes,
        )
        metrics: list[dict[str, Any]] = []

        @tool
        def get_person_context() -> dict[str, Any]:
            """Retrieve the complete synthetic person context and move event. Call this before deciding applicability."""
            store.log("tool", "context_retrieved", "Retrieved Alex Morgan's synthetic context.", "root_move")
            return {
                "evidence_label": "SYNTHETIC PERSON AND EVENT CONTEXT",
                "source_id": "SYNTHETIC-PERSON-001",
                "person": store.scenario["person"],
                "event": store.scenario["event"],
            }

        @tool
        def investigate_domain(requests_json: str) -> dict[str, Any]:
            """Search controlled evidence for up to twelve nodes. Pass a JSON array of objects with node_id, domain, and query. This is the only external-rule evidence source."""
            requests = json.loads(requests_json)
            return {
                "results": [
                    {
                        "node_id": request.get("node_id"),
                        **store.search_evidence(
                            node_id=request.get("node_id", ""),
                            query=request.get("query", ""),
                            domain=request.get("domain", ""),
                        ),
                    }
                    for request in requests[:12]
                ]
            }

        @tool
        def find_existing_node(candidates_json: str) -> dict[str, Any]:
            """Check up to twelve candidates against the runtime graph. Pass a JSON array of objects with title and domain."""
            candidates = json.loads(candidates_json)
            results = []
            for candidate in candidates[:12]:
                title = candidate.get("title", "")
                domain = candidate.get("domain", "")
                existing = store.find_existing(title=title, domain=domain)
                store.log(
                    "tool",
                    "duplicate_check",
                    f"Checked graph for '{title}': {'found' if existing else 'not found'}.",
                    existing.id if existing else None,
                )
                results.append(
                    {
                        "title": title,
                        "domain": domain,
                        "found": bool(existing),
                        "node": asdict(existing) if existing else None,
                    }
                )
            return {"results": results}

        @tool
        def spawn_investigation(candidates_json: str) -> dict[str, Any]:
            """Create up to twelve runtime nodes. Pass a JSON array with title, domain, parent_id, why, and caused_by_evidence_id for every non-root child. Guardrails validate every item."""
            candidates = json.loads(candidates_json)
            return {
                "results": [
                    {
                        "title": candidate.get("title", ""),
                        **store.spawn(
                            title=candidate.get("title", ""),
                            domain=candidate.get("domain", ""),
                            parent_id=candidate.get("parent_id", ""),
                            why=candidate.get("why", ""),
                            discovered_by="Strands model reasoning via spawn_investigation",
                            caused_by_evidence_id=candidate.get("caused_by_evidence_id"),
                        ),
                    }
                    for candidate in candidates[:12]
                ]
            }

        @tool
        def record_consequence(conclusions_json: str) -> dict[str, Any]:
            """Record up to twelve conclusions. Pass a JSON array of objects with node_id, status, reason, evidence_ids, and model_reasoning. Missing or gap evidence becomes UNKNOWN."""
            conclusions = json.loads(conclusions_json)
            return {
                "results": [
                    store.record(
                        node_id=str(conclusion.get("node_id", "")),
                        status=str(conclusion.get("status", "UNKNOWN")),
                        reason=str(conclusion.get("reason", "")),
                        evidence_ids=[str(item) for item in conclusion.get("evidence_ids", [])],
                        model_reasoning=str(conclusion.get("model_reasoning", "")),
                    )
                    for conclusion in conclusions[:12]
                ]
            }

        @tool
        def get_pending_nodes() -> dict[str, Any]:
            """Return unresolved runtime nodes. An empty list is the no-new-consequences stopping signal."""
            pending = [asdict(node) for node in store.pending_nodes()]
            store.log(
                "tool",
                "pending_checked",
                f"Pending queue contains {len(pending)} node(s).",
                "root_move",
            )
            return {"pending": pending, "count": len(pending)}

        @tool
        def get_graph_snapshot() -> dict[str, Any]:
            """Inspect the current runtime graph, including statuses, evidence, causal parents, and spawned children."""
            nodes = [asdict(node) for node in sorted(store.nodes.values(), key=lambda item: item.created_order)]
            store.log("tool", "graph_reviewed", f"Reviewed {len(nodes)} runtime graph node(s).", "root_move")
            return {"nodes": nodes, "safeguards": store.safeguards}

        discovery_prompt = """
You are Ripple's first-order consequence discovery planner. There is no predefined consequence checklist.

Call get_person_context. Reason broadly from only that event and context. Create a compact set of 6–9 materially plausible direct consequence candidates across at least five distinct topical domains. Pass the full candidate JSON array to find_existing_node once, then pass only absent candidates as a JSON array to spawn_investigation once with parent_id root_move.

At least one candidate should test applicability of a context attribute that is explicitly false or absent, so later investigation can record DOES_NOT_APPLY when supported. At least one candidate should expose a material uncertainty rather than silently omitting it. These are reasoning categories, not named consequences.

Do not investigate or conclude nodes in this phase. Do not create prerequisites or follow-on steps; those must be discovered later from retrieved evidence beneath their causal consequence. Use a specific affected system as domain, never the move event or generic planning. Keep nodes atomic and do not invent a requirement.
"""
        discovery_agent = Agent(
            model=self._model(),
            tools=[
                get_person_context,
                find_existing_node,
                spawn_investigation,
            ],
            system_prompt=discovery_prompt,
            callback_handler=None,
            name="Ripple Discovery Planner",
        )
        try:
            discovery_result = discovery_agent(
                f"Discover direct consequences of {store.nodes['root_move'].title}; configured move date "
                f"{self.scenario['event']['move_date']}."
            )
            metrics.append(self._metric_summary(discovery_result, "discovery"))
            store.log(
                "agent",
                "discovery_complete",
                f"Discovery produced {len(store.pending_nodes())} candidate node(s).",
                "root_move",
            )

            investigation_prompt = f"""
You are Ripple's recursive consequence investigator. Work only on nodes already present in the runtime graph or children that retrieved evidence causes.

Call get_person_context, then repeat this loop until get_pending_nodes returns zero:
1. Get pending nodes.
2. Submit one investigate_domain call whose requests_json is a JSON array covering every pending node, with a focused open-text query for each. Only retrieved tool evidence may support a requirement.
3. Submit one record_consequence call whose conclusions_json is a JSON array with exactly one conclusion per pending node. Use ACTION_NEEDED only for the narrow step explicitly stated in a retrieved excerpt; remove any bundled deadline, cancellation, minimum, filing, test, document, or other detail that the excerpt does not state. Use DOES_NOT_APPLY when both a retrieved applicability rule and context negate the trigger; HUMAN_DECISION for a genuine preference or judgment; UNKNOWN for missing facts or evidence gaps; and RESOLVED only when no outstanding step remains.
4. Inspect retrieved evidence for distinct material prerequisites or follow-ons. If present, batch-check them using candidates_json in find_existing_node, then batch-create absent children using candidates_json in spawn_investigation beneath each causal node, never beneath root_move. Every child candidate must include caused_by_evidence_id naming the source retrieved for its parent that explicitly supports the child's claim. Investigate accepted children in the next loop.

Safeguards are enforced by tools: maximum depth {self.max_depth}, maximum nodes {self.max_nodes}, duplicate and already-investigated detection, evidence-required conclusions, and empty-queue stopping. Keep evidence separate from model_reasoning. Do not invent deadlines, rules, person facts, or children unsupported by retrieved evidence.
"""
            investigator = Agent(
                model=self._model(),
                tools=[
                    get_person_context,
                    get_pending_nodes,
                    get_graph_snapshot,
                    investigate_domain,
                    record_consequence,
                    find_existing_node,
                    spawn_investigation,
                ],
                system_prompt=investigation_prompt,
                callback_handler=None,
                name="Ripple Recursive Investigator",
            )
            investigation_result = investigator(
                "Investigate the runtime graph. Follow the evidence recursively and finish with an empty pending queue."
            )
            metrics.append(self._metric_summary(investigation_result, "recursive_investigation"))

            has_downstream = any(node.depth >= 2 for node in store.nodes.values())
            has_unknown = any(node.status == "UNKNOWN" for node in store.nodes.values())
            has_not_applicable = any(node.status == "DOES_NOT_APPLY" for node in store.nodes.values())
            if not has_downstream or not has_unknown or not has_not_applicable:
                coverage_requests = []
                coverage_allowance = 0
                if not has_downstream:
                    coverage_allowance += 1
                    coverage_requests.append(
                        "Create exactly one child: choose the clearest distinct prerequisite stated explicitly in an "
                        "existing node's retrieved evidence, place it beneath that causal node, investigate it, and record it."
                    )
                if not has_unknown:
                    coverage_allowance += 1
                    coverage_requests.append(
                        "Create at most one still-material consequence whose controlling fact or source is absent from the "
                        "controlled layer; investigate it and preserve the evidence gap as UNKNOWN."
                    )
                if not has_not_applicable:
                    coverage_allowance += 1
                    coverage_requests.append(
                        "Create at most one plausible context-negative candidate; if the retrieved applicability "
                        "rule and person context negate it, record DOES_NOT_APPLY."
                    )
                store.max_nodes = min(store.max_nodes, len(store.nodes) + coverage_allowance)
                coverage_result = investigator(
                    "Run a graph coverage review using get_graph_snapshot. "
                    + " ".join(coverage_requests)
                    + " Create no other nodes. Do not invent a requirement merely to satisfy coverage. Finish only when get_pending_nodes is empty."
                )
                metrics.append(self._metric_summary(coverage_result, "coverage_review"))
        except Exception as exc:
            store.log("engine", "agent_error", f"Orchestrator error: {type(exc).__name__}", "root_move")

        for node in store.pending_nodes():
            store.force_unknown(
                node.id,
                "The Strands orchestration ended before this runtime node received an evidence-backed conclusion.",
            )

        store.safeguards["stop_reason"] = "NO_NEW_CONSEQUENCES"
        store.log(
            "guard",
            "stopped",
            "No material unresolved consequence nodes remain; investigation terminated.",
            "root_move",
        )
        return store.result(model_id=self.model_id, strands_metrics=metrics)


def _validate_move_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ripple Checkpoint 1")
    parser.add_argument("--move-date", default=DEFAULT_SCENARIO["event"]["move_date"], type=_validate_move_date)
    parser.add_argument("--max-depth", default=3, type=int)
    parser.add_argument("--max-nodes", default=24, type=int)
    parser.add_argument("--model", default=os.getenv("RIPPLE_MODEL", "gpt-5-mini"))
    args = parser.parse_args()
    scenario = json.loads(json.dumps(DEFAULT_SCENARIO))
    scenario["event"]["move_date"] = args.move_date
    try:
        result = RippleEngine(
            scenario=scenario,
            max_depth=args.max_depth,
            max_nodes=args.max_nodes,
            model_id=args.model,
        ).run()
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    except Exception as exc:
        json.dump({"error": str(exc), "error_type": type(exc).__name__}, sys.stdout)
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
