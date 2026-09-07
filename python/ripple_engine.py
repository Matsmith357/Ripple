from __future__ import annotations

import argparse
import hashlib
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
from urllib.parse import urlparse

from strands import Agent, tool
from strands.models.openai import OpenAIModel

Status = Literal[
    "RESOLVED",
    "DOES_NOT_APPLY",
    "ACTION_PREPARED",
    "HUMAN_DECISION",
    "UNKNOWN",
]
TERMINAL_STATUSES: set[str] = {
    "RESOLVED",
    "DOES_NOT_APPLY",
    "ACTION_PREPARED",
    "HUMAN_DECISION",
    "UNKNOWN",
}


def parse_json_array(payload: str) -> tuple[list[dict[str, Any]], bool]:
    """Parse a model-supplied array, repairing invalid apostrophe escapes or duplicated trailing output."""
    repaired = False
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as original_error:
        cleaned = payload.replace("\\'", "'")
        try:
            parsed, end = json.JSONDecoder().raw_decode(cleaned.lstrip())
            if cleaned.lstrip()[end:].strip() or cleaned != payload:
                repaired = True
        except json.JSONDecodeError:
            raise original_error
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError("Tool payload must be a JSON array of objects.")
    return parsed, repaired

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
    source_url: str | None
    publisher: str
    title: str
    excerpt: str
    retrieved_at: str
    query: str
    retrieval_context: str
    supports: list[str] = field(default_factory=list)
    limitations: str = ""
    deadline: dict[str, Any] | None = None
    destination: str | None = None
    required_items: list[str] = field(default_factory=list)
    required_context_paths: list[str] = field(default_factory=list)
    content_sha256: str | None = None
    synthetic: bool = False


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
    caused_by_evidence_id: str | None = None
    applicability: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    uncertainty: list[str] = field(default_factory=list)
    created_order: int = 0


class EvidenceProvider:
    """Replaceable retrieval interface. Checkpoint 2 uses verified official-source snapshots."""

    def search(self, query: str, domain: str, limit: int = 2) -> list[Evidence]:
        raise NotImplementedError


class OfficialEvidenceProvider(EvidenceProvider):
    PRIMARY_OFFICIAL_HOSTS = {
        "bmv.ohio.gov",
        "www.bmv.ohio.gov",
        "publicsafety.ohio.gov",
        "codes.ohio.gov",
        "www.ohiosos.gov",
        "olvr.ohiosos.gov",
        "www.franklincountyohio.gov",
        "tax.ohio.gov",
        "dam.assets.ohio.gov",
        "www.usps.com",
        "pe.usps.com",
        "insurance.ohio.gov",
        "ohio.gov",
        "elicense.ohio.gov",
        "education.ohio.gov",
    }
    AUTHORITATIVE_SECONDARY_HOSTS = {"content.naic.org"}

    def __init__(self, path: Path, clock: callable | None = None) -> None:
        payload = json.loads(path.read_text())
        self.catalog_version = payload["catalog_version"]
        self.label = payload["label"]
        self.classification_policy = payload.get("classification_policy", {})
        self.documents = payload["documents"]
        self.clock = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        for document in self.documents:
            digest = hashlib.sha256(document["content"].encode()).hexdigest()
            if digest != document.get("content_sha256"):
                raise ValueError(f"Evidence snapshot integrity check failed: {document['source_id']}")

    @classmethod
    def classify_source(cls, url: str | None) -> str:
        if not url:
            return "EVIDENCE_GAP"
        host = (urlparse(url).hostname or "").lower()
        if host in cls.PRIMARY_OFFICIAL_HOSTS:
            return "PRIMARY_OFFICIAL"
        if host in cls.AUTHORITATIVE_SECONDARY_HOSTS:
            return "AUTHORITATIVE_SECONDARY"
        return "UNVERIFIED"

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
        aliases = {
            "automobile": "auto",
            "dmv": "bmv",
            "insurer": "insurance",
            "licensing": "license",
            "licenses": "license",
        }
        return {
            aliases.get(token, token)
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if len(token) > 2 and token not in low_information
        }

    def search(self, query: str, domain: str, limit: int = 2) -> list[Evidence]:
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
            direct_tokens = self._tokens(f"{document['title']} {document['content']}")
            document_domain_tokens = self._tokens(
                f"{' '.join(document['domains'])} {document['title']}"
            )
            score = len(query_tokens & document_tokens) + (2 * len(query_tokens & direct_tokens))
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
                source_type=self.classify_source(document.get("source_url")),
                source_url=document.get("source_url"),
                publisher=document["publisher"],
                title=document["title"],
                excerpt=document["content"][:1400],
                retrieved_at=document["retrieved_at"],
                query=query,
                retrieval_context=document["retrieval_context"],
                supports=document.get("supports", []),
                limitations=document.get("limitations", ""),
                deadline=document.get("deadline"),
                destination=document.get("destination"),
                required_items=document.get("required_items", []),
                required_context_paths=document.get("required_context_paths", []),
                content_sha256=document.get("content_sha256"),
                synthetic=False,
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
        self.configured_max_nodes = max_nodes
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
            "weak_evidence_coercions": 0,
            "applicability_coercions": 0,
            "deadline_coercions": 0,
            "unsupported_action_coercions": 0,
            "human_decision_coercions": 0,
            "tool_payload_repairs": 0,
            "tool_payload_rejections": 0,
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
                    "source_url": None,
                    "publisher": "Ripple demo input",
                    "title": "Configured Alex Morgan move event",
                    "excerpt": f"{scenario['event']['from_city']}, {scenario['event']['from_state']} to {scenario['event']['to_city']}, {scenario['event']['to_state']} on {scenario['event']['move_date']}",
                    "retrieved_at": self._now(),
                    "query": "root event",
                    "retrieval_context": "User-configured synthetic scenario input, not a public source.",
                    "supports": ["The move event that begins the investigation."],
                    "limitations": "Synthetic person and event context; not legal or administrative evidence.",
                    "deadline": None,
                    "destination": None,
                    "required_items": [],
                    "content_sha256": None,
                    "synthetic": True,
                }
            ],
            discovered_by="configured event input",
            why_investigated="Root event supplied to Ripple.",
            model_reasoning="No inference: this node records the supplied event.",
            caused_by_evidence_id=None,
            applicability={
                "rule": "Configured event input",
                "why_applies": "Alex's configured move is the investigation trigger.",
                "trigger_facts": ["event.from_state", "event.to_state", "event.move_date"],
                "resolved_facts": {
                    "event.from_state": scenario["event"]["from_state"],
                    "event.to_state": scenario["event"]["to_state"],
                    "event.move_date": scenario["event"]["move_date"],
                },
            },
            action={
                "what": "Investigate the consequences of the configured interstate move.",
                "why": "This is the supplied root event.",
                "when": scenario["event"]["move_date"],
                "deadline_source_id": "SYNTHETIC-EVENT-001",
                "where": "Ripple investigation engine",
                "need": ["Configured move", "Synthetic person context"],
                "depends_on": None,
                "status": "RESOLVED",
            },
            uncertainty=[],
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

    def resolve_context_fact(self, path: str) -> tuple[bool, Any]:
        parts = path.split(".")
        if not parts or parts[0] not in {"person", "event"}:
            return False, None
        value: Any = self.scenario
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return False, None
            value = value[part]
        return True, value

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
            child_terms = OfficialEvidenceProvider._tokens(f"{title} {domain}")
            evidence_terms = OfficialEvidenceProvider._tokens(f"{evidence.title} {evidence.excerpt}")
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
            caused_by_evidence_id=caused_by_evidence_id,
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
                source_url=None,
                publisher="Ripple evidence guard",
                title="No trustworthy evidence matched the query",
                excerpt=(
                    "The verified Checkpoint 2 evidence catalog returned no matching source. "
                    "The consequence must remain UNKNOWN unless another retrieved source resolves it."
                ),
                retrieved_at=self._now(),
                query=query,
                retrieval_context="Deterministic evidence-provider gap generated for this query.",
                synthetic=False,
            )
            results = [gap]
        for item in results:
            self.retrieved_evidence[item.source_id] = item
            self.node_evidence_ids.setdefault(node_id, set()).add(item.source_id)
        self.log(
            "tool",
            "evidence_retrieved",
            f"Retrieved {len(results)} verified source(s) for '{node.title}'.",
            node_id,
        )
        return {
            "ok": True,
            "evidence_label": "VERIFIED PUBLIC EVIDENCE",
            "results": [
                {
                    "source_id": item.source_id,
                    "source_type": item.source_type,
                    "source_url": item.source_url,
                    "publisher": item.publisher,
                    "title": item.title,
                    "excerpt": item.excerpt,
                    "retrieved_at": item.retrieved_at,
                    "retrieval_context": item.retrieval_context,
                    "limitations": item.limitations[:500],
                    "deadline": item.deadline,
                    "destination": item.destination,
                    "required_items": item.required_items,
                    "required_context_paths": item.required_context_paths,
                }
                for item in results
            ],
        }

    def record(
        self,
        node_id: str,
        status: str,
        reason: str,
        evidence_ids: list[str],
        model_reasoning: str,
        action: dict[str, Any] | None = None,
        applicability: dict[str, Any] | None = None,
        uncertainty: list[str] | None = None,
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
        if status == "ACTION_NEEDED":
            status = "ACTION_PREPARED"
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
                        source_url=None,
                        publisher="Ripple evidence guard",
                        title="Conclusion lacked retrieved evidence",
                        excerpt=(
                            "No evidence returned by investigate_domain was attached. "
                            "Ripple coerced the conclusion to UNKNOWN."
                        ),
                        retrieved_at=self._now(),
                        query=node.title,
                        retrieval_context="Deterministic conclusion guard generated after missing node-bound evidence.",
                        synthetic=False,
                    )
                )
            ]
            reason = f"Insufficient retrieved evidence. {reason}".strip()
        if any(item["source_type"] == "EVIDENCE_GAP" for item in evidence):
            status = "UNKNOWN"

        primary_ids = {
            item["source_id"] for item in evidence if item["source_type"] == "PRIMARY_OFFICIAL"
        }
        trusted_ids = {
            item["source_id"]
            for item in evidence
            if item["source_type"] in {"PRIMARY_OFFICIAL", "AUTHORITATIVE_SECONDARY"}
        }
        applicability = applicability or {}
        evidence_required_paths = [
            path
            for item in evidence
            for path in item.get("required_context_paths", [])
        ]
        trigger_facts = list(
            dict.fromkeys(
                [str(path) for path in applicability.get("trigger_facts", [])]
                + [str(path) for path in evidence_required_paths]
            )
        )
        resolved_facts: dict[str, Any] = {}
        unresolved_facts: list[str] = []
        for path in trigger_facts:
            found, value = self.resolve_context_fact(path)
            if found:
                resolved_facts[path] = value
            else:
                unresolved_facts.append(path)
        applicability_record = {
            "rule": str(applicability.get("rule", "")).strip(),
            "why_applies": str(applicability.get("why_applies", reason)).strip(),
            "trigger_facts": trigger_facts,
            "resolved_facts": resolved_facts,
            "unresolved_facts": unresolved_facts,
        }

        action = action or {}
        action_what = str(action.get("what", "")).strip()
        requested_when = str(action.get("when", "UNKNOWN")).strip() or "UNKNOWN"
        deadline_source_id = str(action.get("deadline_source_id", "")).strip() or None
        supported_when = "UNKNOWN"
        if requested_when.upper() != "UNKNOWN":
            source = self.retrieved_evidence.get(deadline_source_id or "")
            if (
                source
                and source.source_id in self.node_evidence_ids.get(node_id, set())
                and source.source_type in {"PRIMARY_OFFICIAL", "AUTHORITATIVE_SECONDARY"}
                and source.deadline
            ):
                supported_when = str(source.deadline.get("text", "UNKNOWN"))
            else:
                self.safeguards["deadline_coercions"] += 1
        destination = next(
            (item["destination"] for item in evidence if item.get("destination")),
            "UNKNOWN",
        )
        evidence_needs = sorted(
            {
                requirement
                for item in evidence
                for requirement in item.get("required_items", [])
                if requirement
            }
        )
        depends_on = (
            self.nodes[node.parent_id].title
            if node.parent_id and node.parent_id != "root_move"
            else (str(action.get("depends_on", "")).strip() or None)
        )

        if status == "ACTION_PREPARED":
            action_terms = OfficialEvidenceProvider._tokens(action_what)
            rule_terms = OfficialEvidenceProvider._tokens(applicability_record["rule"])
            evidence_terms = OfficialEvidenceProvider._tokens(
                " ".join(f"{item['title']} {item['excerpt']}" for item in evidence)
            )
            if not primary_ids:
                self.safeguards["weak_evidence_coercions"] += 1
                status = "UNKNOWN"
                reason = f"A prepared legal or administrative action requires PRIMARY_OFFICIAL evidence. {reason}".strip()
            elif (
                not trigger_facts
                or unresolved_facts
                or any(resolved_facts.get(path) in {False, None, ""} for path in evidence_required_paths)
            ):
                self.safeguards["applicability_coercions"] += 1
                status = "UNKNOWN"
                reason = f"Alex-specific applicability was not fully established from declared context facts. {reason}".strip()
            elif not applicability_record["rule"] or len(rule_terms & evidence_terms) < 2:
                self.safeguards["applicability_coercions"] += 1
                status = "UNKNOWN"
                reason = f"The asserted rule was not sufficiently grounded in the retrieved evidence text. {reason}".strip()
            elif not action_what or len(action_terms & evidence_terms) < 2:
                self.safeguards["unsupported_action_coercions"] += 1
                status = "UNKNOWN"
                reason = f"The proposed action was not sufficiently supported by the retrieved evidence text. {reason}".strip()

        has_negated_trigger = any(value is False or value is None for value in resolved_facts.values())
        if status == "RESOLVED" and trusted_ids and trigger_facts and not unresolved_facts and has_negated_trigger:
            status = "DOES_NOT_APPLY"

        if status == "DOES_NOT_APPLY":
            rule_terms = OfficialEvidenceProvider._tokens(applicability_record["rule"])
            evidence_terms = OfficialEvidenceProvider._tokens(
                " ".join(f"{item['title']} {item['excerpt']}" for item in evidence)
            )
            if (
                not trusted_ids
                or not trigger_facts
                or unresolved_facts
                or not has_negated_trigger
                or len(rule_terms & evidence_terms) < 2
            ):
                self.safeguards["applicability_coercions"] += 1
                status = "UNKNOWN"
                reason = f"The applicability trigger was not authoritatively negated by Alex's context. {reason}".strip()

        decision_options = [str(item).strip() for item in action.get("decision_options", []) if str(item).strip()]
        if status == "HUMAN_DECISION" and (not primary_ids or len(decision_options) < 2):
            self.safeguards["human_decision_coercions"] += 1
            status = "UNKNOWN"
            reason = f"A genuine evidence-backed choice was not established. {reason}".strip()

        uncertainty_values = [str(item).strip() for item in (uncertainty or []) if str(item).strip()]
        uncertainty_values.extend(
            item["limitations"] for item in evidence if item.get("limitations")
        )
        if status == "UNKNOWN" and not uncertainty_values:
            uncertainty_values.append("Sufficient trustworthy evidence or Alex-specific facts were not established.")

        node.status = status
        node.reason = reason.strip() or "No reason supplied; treated as unresolved."
        node.evidence = evidence
        node.model_reasoning = model_reasoning.strip() or node.reason
        node.applicability = applicability_record
        node.action = {
            "what": action_what if status in {"ACTION_PREPARED", "HUMAN_DECISION"} else "No action prepared.",
            "why": applicability_record["why_applies"] or node.reason,
            "when": supported_when,
            "deadline_source_id": deadline_source_id if supported_when != "UNKNOWN" else None,
            "where": destination,
            "need": evidence_needs,
            "depends_on": depends_on,
            "decision_options": decision_options,
            "status": status,
        }
        node.uncertainty = list(dict.fromkeys(uncertainty_values))
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
            source_url=None,
            publisher="Ripple engine guard",
            title="Investigation ended without an evidence-backed conclusion",
            excerpt=reason,
            retrieved_at=self._now(),
            query=node.title,
            retrieval_context="Deterministic stop guard generated after orchestration interruption.",
            synthetic=False,
        )
        self.retrieved_evidence[gap.source_id] = gap
        self.node_evidence_ids.setdefault(node_id, set()).add(gap.source_id)
        self.record(node_id, "UNKNOWN", reason, [gap.source_id], reason)

    def result(self, model_id: str, strands_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        ordered = sorted(self.nodes.values(), key=lambda node: node.created_order)
        edges = [
            {"source": node.parent_id, "target": node.id}
            for node in ordered
            if node.parent_id is not None
        ]
        return {
            "checkpoint": 2,
            "run_id": self.run_id,
            "generated_at": self._now(),
            "generated_at_runtime": True,
            "engine": "Strands Agents SDK",
            "model": model_id,
            "evidence_mode": "VERIFIED PUBLIC SOURCES",
            "evidence_catalog": {
                "version": self.evidence_provider.catalog_version,
                "label": self.evidence_provider.label,
                "classification_policy": self.evidence_provider.classification_policy,
            },
            "scenario": self.scenario,
            "guardrail_config": {"max_depth": self.max_depth, "max_nodes": self.configured_max_nodes},
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
        self.evidence_path = evidence_path or Path(__file__).with_name("official_evidence.json")

    def _model(self) -> OpenAIModel:
        api_key = os.getenv("BUILT_IN_FORGE_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("BUILT_IN_FORGE_API_URL") or os.getenv("OPENAI_API_BASE")
        if not api_key or not base_url:
            raise RuntimeError("No managed LLM credentials are available to the Strands worker.")
        normalized_url = base_url.rstrip("/")
        if not normalized_url.endswith("/v1"):
            normalized_url = f"{normalized_url}/v1"
        if self.model_id.startswith("gemini-"):
            params: dict[str, Any] = {"max_tokens": 5000}
        elif self.model_id.startswith("claude-"):
            params = {"max_tokens": 5000}
        else:
            completion_limit = 3500 if self.model_id == "gpt-5-nano" else 5000
            params = {
                "max_completion_tokens": completion_limit,
                "extra_body": {"reasoning": {"effort": "low"}},
            }
        return OpenAIModel(
            client_args={"api_key": api_key, "base_url": normalized_url},
            model_id=self.model_id,
            stream=False,
            params=params,
        )

    @staticmethod
    def _metric_summary(result: Any, phase: str, node_id: str | None = None) -> dict[str, Any]:
        try:
            summary = result.metrics.get_summary()
        except Exception:
            summary = {}
        return {"phase": phase, "node_id": node_id, "summary": summary}

    def run(self) -> dict[str, Any]:
        provider = OfficialEvidenceProvider(self.evidence_path)
        store = InvestigationStore(
            scenario=self.scenario,
            evidence_provider=provider,
            max_depth=self.max_depth,
            max_nodes=self.max_nodes,
        )
        metrics: list[dict[str, Any]] = []
        orchestrator_failure: str | None = None

        def invoke_with_retry(agent: Agent, prompt: str, phase: str) -> Any:
            for attempt in range(2):
                try:
                    return agent(prompt)
                except Exception as exc:
                    if attempt == 1:
                        raise
                    store.log(
                        "engine",
                        "agent_retry",
                        f"Retrying {phase} after transient {type(exc).__name__}: {str(exc)[:180]}",
                        "root_move",
                    )
                    time.sleep(2)
            raise RuntimeError(f"{phase} did not return")

        def decode_batch(payload: str, tool_name: str) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
            try:
                items, repaired = parse_json_array(payload)
            except (json.JSONDecodeError, ValueError) as exc:
                store.safeguards["tool_payload_rejections"] += 1
                store.log("guard", "tool_payload_rejected", f"{tool_name}: {exc}", "root_move")
                return None, {"ok": False, "reason": "invalid_json_array", "tool": tool_name}
            if repaired:
                store.safeguards["tool_payload_repairs"] += 1
                store.log(
                    "guard",
                    "tool_payload_repaired",
                    f"{tool_name}: repaired an invalid apostrophe escape before parsing.",
                    "root_move",
                )
            return items, None

        @tool
        def get_person_context() -> dict[str, Any]:
            """Retrieve the complete synthetic person context and move event. Call this before deciding applicability."""
            store.log("tool", "context_retrieved", "Retrieved Alex Morgan's synthetic context.", "root_move")
            return {
                "evidence_label": "SYNTHETIC PERSON AND EVENT CONTEXT",
                "source_id": "SYNTHETIC-PERSON-001",
                "person": store.scenario["person"],
                "event": store.scenario["event"],
                "pending_nodes": [asdict(node) for node in store.pending_nodes()],
            }

        @tool
        def investigate_domain(requests_json: str) -> dict[str, Any]:
            """Retrieve verified public evidence for up to twelve nodes. Pass a JSON array with node_id, domain, and query. This is the only external-rule evidence source."""
            requests, error = decode_batch(requests_json, "investigate_domain")
            if error:
                return error
            assert requests is not None
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
            candidates, error = decode_batch(candidates_json, "find_existing_node")
            if error:
                return error
            assert candidates is not None
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
            candidates, error = decode_batch(candidates_json, "spawn_investigation")
            if error:
                return error
            assert candidates is not None
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
            """Record conclusions and evidence-backed children. Each JSON object needs node_id, status, reason, evidence_ids, model_reasoning, applicability, action, uncertainty, and spawned_consequences. Trust guards validate both conclusions and children."""
            conclusions, error = decode_batch(conclusions_json, "record_consequence")
            if error:
                return error
            assert conclusions is not None
            results = []
            accepted_child = False
            for conclusion in conclusions[:12]:
                node_id = str(conclusion.get("node_id", ""))
                raw_evidence_ids = conclusion.get("evidence_ids", []) or conclusion.get("evidence", [])
                evidence_ids = [
                    str(item.get("source_id", "")) if isinstance(item, dict) else str(item)
                    for item in raw_evidence_ids
                ]
                if not any(evidence_ids) and store.node_evidence_ids.get(node_id):
                    evidence_ids = sorted(store.node_evidence_ids[node_id])
                recorded = store.record(
                    node_id=node_id,
                    status=str(conclusion.get("status", "UNKNOWN")),
                    reason=str(conclusion.get("reason", "")),
                    evidence_ids=evidence_ids,
                    model_reasoning=str(conclusion.get("model_reasoning", "")),
                    applicability=conclusion.get("applicability"),
                    action=conclusion.get("action"),
                    uncertainty=conclusion.get("uncertainty"),
                )
                spawned = []
                if recorded.get("ok") and not accepted_child:
                    for child in conclusion.get("spawned_consequences", [])[:3]:
                        child_result = store.spawn(
                            title=str(child.get("title", "")),
                            domain=str(child.get("domain", "")),
                            parent_id=node_id,
                            why=str(child.get("why", "")),
                            discovered_by="Strands model reasoning via record_consequence",
                            caused_by_evidence_id=child.get("caused_by_evidence_id"),
                        )
                        spawned.append(child_result)
                        if child_result.get("accepted"):
                            accepted_child = True
                            break
                results.append({**recorded, "spawned": spawned})
            pending = [asdict(node) for node in store.pending_nodes()]
            return {"results": results, "pending_nodes": pending, "pending_count": len(pending)}

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
            nodes = [
                {
                    "id": node.id,
                    "title": node.title,
                    "domain": node.domain,
                    "parent_id": node.parent_id,
                    "depth": node.depth,
                    "status": node.status,
                    "caused_by_evidence_id": node.caused_by_evidence_id,
                    "spawned_consequences": node.spawned_consequences,
                    "evidence": [
                        {
                            "source_id": item["source_id"],
                            "source_type": item["source_type"],
                            "title": item["title"],
                            "excerpt": item["excerpt"][:700],
                        }
                        for item in node.evidence
                    ],
                }
                for node in sorted(store.nodes.values(), key=lambda item: item.created_order)
            ]
            store.log("tool", "graph_reviewed", f"Reviewed {len(nodes)} runtime graph node(s).", "root_move")
            return {"nodes": nodes, "safeguards": store.safeguards}

        discovery_prompt = """
You are Ripple's first-order consequence discovery planner. There is no predefined consequence checklist.

Call get_person_context. Reason broadly from only that event and context. Create a compact set of 6–7 materially plausible direct consequence candidates across at least five distinct topical domains. Pass the full candidate JSON array to spawn_investigation once with parent_id root_move. That tool performs deterministic duplicate checking before every insert.

At least one candidate should test applicability of a context attribute that is explicitly false or absent, so later investigation can record DOES_NOT_APPLY when supported. At least one candidate should expose a material uncertainty rather than silently omitting it. These are reasoning categories, not named consequences.

Do not investigate or conclude nodes in this phase. Do not create prerequisites or follow-on steps; those must be discovered later from retrieved evidence beneath their causal consequence. Use a specific affected system as domain, never the move event or generic planning. Keep nodes atomic and do not invent a requirement.
"""
        discovery_agent = Agent(
            model=self._model(),
            tools=[
                get_person_context,
                spawn_investigation,
            ],
            system_prompt=discovery_prompt,
            callback_handler=None,
            name="Ripple Discovery Planner",
        )
        try:
            discovery_result = invoke_with_retry(
                discovery_agent,
                f"Discover direct consequences of {store.nodes['root_move'].title}; configured move date "
                f"{self.scenario['event']['move_date']}.",
                "discovery",
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

Call get_person_context exactly once; its response includes pending_nodes. Repeat this loop until record_consequence returns pending_count zero:
1. Submit one investigate_domain call whose requests_json is a JSON array covering every pending node, with a focused open-text query for each. Only retrieved tool evidence may support a requirement.
2. Submit one record_consequence call whose conclusions_json is a JSON array with exactly one conclusion per pending node. Each conclusion must contain:
   - status: one of RESOLVED, DOES_NOT_APPLY, ACTION_PREPARED, HUMAN_DECISION, UNKNOWN.
   - reason, evidence_ids (source_id values from investigate_domain for that exact node), and model_reasoning. Never cite another node's source.
   - applicability: {{"rule":"rule stated by the evidence","why_applies":"why this rule applies to Alex","trigger_facts":["person.or.event.fact.paths"]}}. Use only paths returned by get_person_context.
   - action: {{"what":"narrow prepared step","when":"supported deadline text or UNKNOWN","deadline_source_id":"source id or null","where":"authoritative destination","depends_on":"prerequisite or null","decision_options":[]}}.
   - uncertainty: a list of every unresolved condition, missing fact, or source limitation.
   - spawned_consequences: a JSON array of distinct material prerequisites or follow-ons stated explicitly by the retrieved evidence. Each child needs title, domain, why, and caused_by_evidence_id. Use [] when none applies.
   Use ACTION_PREPARED only for the narrow step explicitly stated in PRIMARY_OFFICIAL evidence and supported by resolved Alex-specific trigger facts. Remove any bundled deadline, cancellation, minimum, filing, test, document, or detail that the excerpt does not state. Use DOES_NOT_APPLY when trusted evidence defines the trigger and Alex's declared context negates it. Use HUMAN_DECISION only when PRIMARY_OFFICIAL evidence establishes a genuine choice and provide at least two decision_options. Use UNKNOWN for missing facts, weak evidence, or evidence gaps; and RESOLVED only when no outstanding step remains.
3. Before record_consequence, inspect each node's retrieved evidence for a distinct material prerequisite or follow-on. Put any such child in that conclusion's spawned_consequences array. The tool accepts at most one material child per batch and applies duplicate, depth, node-budget, and parent-bound evidence guards. Its response includes the next pending_nodes list. Investigate an accepted child in the next loop. Do not call get_pending_nodes or get_graph_snapshot during this primary pass unless a tool response is malformed.

Safeguards are enforced by tools: maximum depth {self.max_depth}, maximum nodes {self.max_nodes}, duplicate and already-investigated detection, PRIMARY_OFFICIAL evidence for prepared administrative actions, node-bound evidence, source-backed deadlines, context-path applicability, evidence-grounded children, and empty-queue stopping. Keep retrieved evidence separate from model_reasoning. Do not invent deadlines, rules, person facts, documents, destinations, choices, or children unsupported by retrieved evidence.
"""
            investigator = Agent(
                model=self._model(),
                tools=[
                    get_person_context,
                    investigate_domain,
                    record_consequence,
                ],
                system_prompt=investigation_prompt,
                callback_handler=None,
                name="Ripple Recursive Investigator",
            )
            investigation_result = invoke_with_retry(
                investigator,
                "Investigate the runtime graph. Follow the evidence recursively and finish with an empty pending queue.",
                "recursive investigation",
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
                        "verified source catalog; investigate it and preserve the evidence gap as UNKNOWN."
                    )
                if not has_not_applicable:
                    coverage_allowance += 1
                    coverage_requests.append(
                        "Create at most one plausible context-negative candidate; if the retrieved applicability "
                        "rule and person context negate it, record DOES_NOT_APPLY."
                    )
                configured_budget = store.max_nodes
                store.max_nodes = min(store.max_nodes, len(store.nodes) + coverage_allowance)
                try:
                    coverage_agent = Agent(
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
                        name="Ripple Coverage Reviewer",
                    )
                    coverage_result = invoke_with_retry(
                        coverage_agent,
                        "Run a graph coverage review using get_graph_snapshot. "
                        + " ".join(coverage_requests)
                        + " Create no other nodes. Do not invent a requirement merely to satisfy coverage. Finish only when get_pending_nodes is empty.",
                        "coverage review",
                    )
                finally:
                    store.max_nodes = configured_budget
                metrics.append(self._metric_summary(coverage_result, "coverage_review"))
        except Exception as exc:
            orchestrator_failure = f"{type(exc).__name__}: {str(exc)[:240]}"
            store.log(
                "engine",
                "agent_error",
                f"Orchestrator error: {type(exc).__name__}: {str(exc)[:240]}",
                "root_move",
            )

        if len(store.nodes) == 1:
            raise RuntimeError(
                f"Strands discovery did not produce any consequence nodes. {orchestrator_failure or ''}".strip()
            )

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
    parser = argparse.ArgumentParser(description="Run Ripple Checkpoint 2")
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
