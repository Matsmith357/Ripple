import json
from pathlib import Path

import pytest

from ripple_engine import DEFAULT_SCENARIO, InvestigationStore, OfficialEvidenceProvider


@pytest.fixture()
def store() -> InvestigationStore:
    provider = OfficialEvidenceProvider(Path(__file__).with_name("official_evidence.json"), clock=lambda: "2026-09-05T00:00:00Z")
    return InvestigationStore(
        scenario=json.loads(json.dumps(DEFAULT_SCENARIO)),
        evidence_provider=provider,
        max_depth=2,
        max_nodes=12,
    )


def test_runtime_graph_starts_with_only_the_supplied_event(store: InvestigationStore) -> None:
    assert list(store.nodes) == ["root_move"]
    assert store.nodes["root_move"].title == "Interstate Move: Indiana → Ohio"
    assert store.result("test-model", [])["generated_at_runtime"] is True


def test_multiple_domains_can_be_discovered_through_general_spawn(store: InvestigationStore) -> None:
    driving = store.spawn("Review driving credential after move", "driving", "root_move", "Move changed state", "test model")
    civic = store.spawn("Review voter registration after move", "civic", "root_move", "Move changed state", "test model")
    assert driving["accepted"] is True
    assert civic["accepted"] is True
    assert {node.domain for node in store.nodes.values()} >= {"driving", "civic"}


def test_non_applicable_consequence_can_be_recorded(store: InvestigationStore) -> None:
    created = store.spawn("Professional license portability", "professional licensing", "root_move", "Possible state credential", "test model")
    evidence = store.search_evidence(created["node_id"], "professional license reciprocity after move", "professional licensing")
    source_ids = [item["source_id"] for item in evidence["results"]]
    recorded = store.record(
        created["node_id"],
        "DOES_NOT_APPLY",
        "Alex has no professional license, so the retrieved trigger is absent.",
        source_ids,
        "The person context negates the source's applicability condition.",
        applicability={
            "rule": "Professional licensing applies to a person seeking or holding a regulated credential.",
            "why_applies": "Alex has no professional license.",
            "trigger_facts": ["person.professional_license"],
        },
    )
    assert recorded["status"] == "DOES_NOT_APPLY"


def test_consequence_can_spawn_a_downstream_child(store: InvestigationStore) -> None:
    parent = store.spawn("Transfer vehicle title", "vehicle", "root_move", "Personally owned vehicle moved", "test model")
    evidence = store.search_evidence(parent["node_id"], "vehicle title identification inspection prerequisite", "vehicle")
    vin_source = next(
        item["source_id"]
        for item in evidence["results"]
        if "inspection" in f"{item['title']} {item['excerpt']}".lower()
    )
    child = store.spawn(
        "Complete prerequisite vehicle identification inspection",
        "inspection",
        parent["node_id"],
        "Title evidence identifies a prerequisite",
        "test model",
        caused_by_evidence_id=vin_source,
    )
    assert child["accepted"] is True
    assert store.nodes[child["node_id"]].parent_id == parent["node_id"]
    assert store.nodes[child["node_id"]].depth == 2


def test_downstream_child_requires_matching_parent_evidence(store: InvestigationStore) -> None:
    parent = store.spawn("Transfer vehicle title", "vehicle", "root_move", "Vehicle moved", "test model")
    evidence = store.search_evidence(parent["node_id"], "vehicle title identification inspection prerequisite", "vehicle")
    source_id = evidence["results"][0]["source_id"]
    blocked = store.spawn(
        "Enroll in a public library",
        "library",
        parent["node_id"],
        "Unsupported follow-on",
        "test model",
        caused_by_evidence_id=source_id,
    )
    assert blocked["reason"] == "child_evidence_mismatch"


def test_duplicate_investigations_are_prevented(store: InvestigationStore) -> None:
    first = store.spawn("Notify auto insurer", "insurance", "root_move", "Address changed", "test model")
    duplicate = store.spawn("Notify auto insurer", "insurance", "root_move", "Same candidate", "test model")
    assert first["accepted"] is True
    assert duplicate == {"accepted": False, "reason": "duplicate", "existing_node_id": first["node_id"]}
    assert store.safeguards["duplicate_blocks"] == 1


def test_maximum_depth_guard_and_no_pending_stop_condition(store: InvestigationStore) -> None:
    level_one = store.spawn("Level one", "test", "root_move", "test", "test model")
    evidence = store.search_evidence(level_one["node_id"], "vehicle title identification inspection prerequisite", "vehicle")
    vin_source = next(
        item["source_id"]
        for item in evidence["results"]
        if "inspection" in f"{item['title']} {item['excerpt']}".lower()
    )
    level_two = store.spawn(
        "Vehicle identification inspection",
        "inspection",
        level_one["node_id"],
        "test",
        "test model",
        caused_by_evidence_id=vin_source,
    )
    blocked = store.spawn("Level three", "test", level_two["node_id"], "test", "test model")
    assert blocked["reason"] == "max_depth"
    assert store.safeguards["max_depth_blocks"] == 1
    for node in store.pending_nodes():
        store.force_unknown(node.id, "Test stopped without additional evidence.")
    assert store.pending_nodes() == []


def test_missing_evidence_is_coerced_to_unknown(store: InvestigationStore) -> None:
    created = store.spawn("Uncovered consequence", "unmapped", "root_move", "Plausible but unsupported", "test model")
    recorded = store.record(
        created["node_id"],
        "ACTION_NEEDED",
        "The model guessed an action.",
        [],
        "Unsupported reasoning.",
    )
    node = store.nodes[created["node_id"]]
    assert recorded["status"] == "UNKNOWN"
    assert node.evidence[0]["source_type"] == "EVIDENCE_GAP"


def test_evidence_cannot_be_reused_across_unrelated_nodes(store: InvestigationStore) -> None:
    insured = store.spawn("Notify insurer", "insurance", "root_move", "Vehicle moved", "test model")
    unsupported = store.spawn("Forward mail", "postal", "root_move", "Address changed", "test model")
    evidence = store.search_evidence(insured["node_id"], "auto insurance policy garaging", "insurance")
    source_ids = [item["source_id"] for item in evidence["results"]]
    recorded = store.record(
        unsupported["node_id"],
        "ACTION_NEEDED",
        "Attempted to reuse another node's source.",
        source_ids,
        "This should be rejected by provenance binding.",
    )
    assert recorded["status"] == "UNKNOWN"
    assert store.nodes[unsupported["node_id"]].evidence[0]["source_type"] == "EVIDENCE_GAP"


def test_every_terminal_conclusion_retains_evidence_and_reason(store: InvestigationStore) -> None:
    created = store.spawn("Notify insurer", "insurance", "root_move", "Vehicle moved", "test model")
    evidence = store.search_evidence(created["node_id"], "auto insurance garaging address move", "insurance")
    store.record(
        created["node_id"],
        "ACTION_NEEDED",
        "The controlled source requires insurer notification.",
        [item["source_id"] for item in evidence["results"]],
        "The person owns an insured vehicle and changed its garaging state.",
    )
    node = store.nodes[created["node_id"]]
    assert node.reason
    assert node.model_reasoning
    assert node.evidence
    assert node.evidence[0]["source_type"] in {"PRIMARY_OFFICIAL", "AUTHORITATIVE_SECONDARY", "EVIDENCE_GAP"}


def test_final_graph_is_assembled_from_mutable_runtime_state(store: InvestigationStore) -> None:
    before = store.result("test-model", [])
    created = store.spawn("Runtime-only node", "runtime", "root_move", "Created during execution", "test model")
    store.force_unknown(created["node_id"], "No source was retrieved in this test.")
    after = store.result("test-model", [])
    assert len(before["graph"]["nodes"]) == 1
    assert len(after["graph"]["nodes"]) == 2
    assert after["run_id"] == store.run_id
    assert after["graph"]["nodes"][1]["title"] == "Runtime-only node"
