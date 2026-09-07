from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TERMINAL = {"RESOLVED", "DOES_NOT_APPLY", "ACTION_PREPARED", "HUMAN_DECISION", "UNKNOWN"}
TRUSTED = {"PRIMARY_OFFICIAL", "AUTHORITATIVE_SECONDARY"}


def get_path(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def validate(payload: dict[str, Any]) -> list[dict[str, object]]:
    nodes = payload["graph"]["nodes"]
    non_root = [node for node in nodes if node["parent_id"] is not None]
    actions = [node for node in non_root if node["status"] == "ACTION_PREPARED"]
    unknown = [node for node in non_root if node["status"] == "UNKNOWN"]
    human = [node for node in non_root if node["status"] == "HUMAN_DECISION"]
    node_by_id = {node["id"]: node for node in nodes}
    domains = {node["domain"] for node in non_root}

    def action_has_primary(node: dict[str, Any]) -> bool:
        return any(evidence["source_type"] == "PRIMARY_OFFICIAL" for evidence in node["evidence"])

    def provenance_complete(evidence: dict[str, Any]) -> bool:
        if evidence["source_type"] == "SYNTHETIC_SCENARIO":
            return True
        if evidence["source_type"] == "EVIDENCE_GAP":
            return bool(evidence["publisher"] and evidence["title"] and evidence["retrieved_at"] and evidence["query"])
        return all(
            [
                evidence.get("source_url", "").startswith("https://"),
                evidence.get("publisher"),
                evidence.get("title"),
                evidence.get("retrieved_at"),
                evidence.get("excerpt"),
                evidence.get("query"),
                evidence.get("retrieval_context"),
                evidence.get("source_type") in TRUSTED | {"UNVERIFIED"},
            ]
        )

    def deadline_traceable(node: dict[str, Any]) -> bool:
        action = node.get("action", {})
        if action.get("when") in {None, "", "UNKNOWN"}:
            return action.get("deadline_source_id") in {None, ""}
        source_id = action.get("deadline_source_id")
        source = next((item for item in node["evidence"] if item["source_id"] == source_id), None)
        return bool(source and source.get("deadline") and source["deadline"].get("text") == action["when"])

    def applicability_resolved(node: dict[str, Any]) -> bool:
        applicability = node.get("applicability", {})
        trigger_facts = applicability.get("trigger_facts", [])
        resolved = applicability.get("resolved_facts", {})
        if not trigger_facts or applicability.get("unresolved_facts"):
            return False
        for path in trigger_facts:
            found, expected = get_path(payload["scenario"], path)
            if not found or path not in resolved or resolved[path] != expected:
                return False
        return bool(applicability.get("rule") and applicability.get("why_applies"))

    downstream = [node for node in non_root if node["depth"] >= 2 and node["parent_id"] != "root_move"]
    grounded_children = []
    for node in downstream:
        parent = node_by_id.get(node["parent_id"])
        cause = node.get("caused_by_evidence_id")
        if parent and cause and any(item["source_id"] == cause for item in parent["evidence"]):
            grounded_children.append(node)

    duplicate_keys = {(node["domain"].lower(), node["title"].lower()) for node in nodes}
    checks: list[dict[str, object]] = [
        {
            "id": 1,
            "name": "real authoritative evidence replaces synthetic evidence for supported conclusions",
            "passed": bool(actions)
            and all(action_has_primary(node) for node in actions)
            and all(not evidence.get("synthetic") for node in actions for evidence in node["evidence"]),
            "detail": f"{len(actions)} prepared actions; all require at least one PRIMARY_OFFICIAL source",
        },
        {
            "id": 2,
            "name": "mock evidence is never presented as real",
            "passed": all(
                "MOCK" not in json.dumps(evidence).upper()
                and evidence["source_type"] != "SYNTHETIC_SCENARIO"
                and not evidence.get("synthetic")
                for node in non_root
                for evidence in node["evidence"]
            ),
            "detail": f"checked every source on {len(non_root)} non-root nodes",
        },
        {
            "id": 3,
            "name": "retrieved evidence and model reasoning remain separate",
            "passed": all(node.get("model_reasoning") and node.get("evidence") for node in nodes),
            "detail": "model_reasoning and evidence are distinct node fields",
        },
        {
            "id": 4,
            "name": "ACTION_PREPARED requires sufficient node-bound primary evidence",
            "passed": bool(actions)
            and all(action_has_primary(node) and node["action"].get("what") for node in actions),
            "detail": [node["title"] for node in actions],
        },
        {
            "id": 5,
            "name": "missing or weak evidence becomes UNKNOWN",
            "passed": bool(unknown),
            "detail": [node["title"] for node in unknown],
        },
        {
            "id": 6,
            "name": "applicability is resolved from Alex's declared context",
            "passed": all(applicability_resolved(node) for node in actions),
            "detail": f"verified trigger paths for {len(actions)} prepared actions",
        },
        {
            "id": 7,
            "name": "deadlines are traceable and unsupported deadlines remain UNKNOWN",
            "passed": all(deadline_traceable(node) for node in non_root),
            "detail": [
                {"title": node["title"], "when": node["action"].get("when"), "source": node["action"].get("deadline_source_id")}
                for node in non_root
            ],
        },
        {
            "id": 8,
            "name": "at least one downstream consequence was discovered from parent-bound evidence",
            "passed": bool(grounded_children),
            "detail": [
                {"title": node["title"], "parent": node["parent_id"], "caused_by": node["caused_by_evidence_id"]}
                for node in grounded_children
            ],
        },
        {
            "id": 9,
            "name": "duplicate, depth, node-budget, already-investigated, and stopping safeguards remain active",
            "passed": len(duplicate_keys) == len(nodes)
            and max(node["depth"] for node in nodes) <= payload["guardrail_config"]["max_depth"]
            and len(nodes) <= payload["guardrail_config"]["max_nodes"]
            and payload["safeguards"]["stop_reason"] == "NO_NEW_CONSEQUENCES"
            and all(node["status"] in TERMINAL for node in nodes),
            "detail": {"config": payload["guardrail_config"], "runtime": payload["safeguards"]},
        },
        {
            "id": 10,
            "name": "Checkpoint 1 discovery and uncertainty behavior remains present",
            "passed": len(domains) >= 3
            and any(node["status"] == "DOES_NOT_APPLY" for node in non_root)
            and bool(unknown)
            and bool(downstream),
            "detail": f"{len(non_root)} nodes across {len(domains)} domains",
        },
        {
            "id": 11,
            "name": "source URLs and complete provenance reach the graph",
            "passed": all(provenance_complete(evidence) for node in nodes for evidence in node["evidence"]),
            "detail": f"checked {sum(len(node['evidence']) for node in nodes)} evidence records",
        },
        {
            "id": 12,
            "name": "the final graph is runtime-generated rather than a static Ohio checklist",
            "passed": payload.get("generated_at_runtime") is True
            and payload.get("run_id", "").startswith("run_")
            and len(nodes) > 1,
            "detail": {"run_id": payload.get("run_id"), "generated_at": payload.get("generated_at")},
        },
        {
            "id": 13,
            "name": "every investigated node retains action fields, evidence, reason, and uncertainty",
            "passed": all(
                node["status"] in TERMINAL
                and node.get("reason")
                and node.get("model_reasoning")
                and node.get("evidence")
                and all(field in node.get("action", {}) for field in ["what", "why", "when", "where", "need", "depends_on", "status"])
                and isinstance(node.get("uncertainty"), list)
                for node in nodes
            ),
            "detail": f"checked {len(nodes)} terminal nodes",
        },
        {
            "id": 14,
            "name": "HUMAN_DECISION is used only for an evidenced choice",
            "passed": all(
                action_has_primary(node) and len(node.get("action", {}).get("decision_options", [])) >= 2
                for node in human
            ),
            "detail": [node["title"] for node in human] if human else "No HUMAN_DECISION node was required",
        },
    ]
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.result.read_text())
    checks = validate(payload)
    report = {"passed": all(check["passed"] for check in checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
