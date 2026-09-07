import hashlib
import json
from pathlib import Path

import pytest

from ripple_engine import (
    DEFAULT_SCENARIO,
    Evidence,
    InvestigationStore,
    OfficialEvidenceProvider,
    parse_json_array,
)


@pytest.fixture()
def official_provider() -> OfficialEvidenceProvider:
    return OfficialEvidenceProvider(Path(__file__).with_name("official_evidence.json"))


@pytest.fixture()
def store(official_provider: OfficialEvidenceProvider) -> InvestigationStore:
    return InvestigationStore(
        scenario=json.loads(json.dumps(DEFAULT_SCENARIO)),
        evidence_provider=official_provider,
        max_depth=2,
        max_nodes=12,
    )


def test_official_catalog_has_real_urls_and_never_presents_mock_evidence(official_provider: OfficialEvidenceProvider) -> None:
    assert official_provider.documents
    assert len({document["source_id"] for document in official_provider.documents}) == len(official_provider.documents)
    assert all(document["source_url"].startswith("https://") for document in official_provider.documents)
    assert all(document["source_type"] != "MOCK_SYNTHETIC" for document in official_provider.documents)
    assert all(document["content_sha256"] for document in official_provider.documents)


def test_source_quality_is_recomputed_from_url_not_trusted_from_catalog(tmp_path: Path) -> None:
    excerpt = "A source can claim anything in metadata."
    payload = {
        "catalog_version": "red-team",
        "label": "red-team",
        "documents": [
            {
                "source_id": "ATTACKER",
                "source_type": "PRIMARY_OFFICIAL",
                "source_url": "https://example.com/not-government",
                "publisher": "Attacker",
                "title": "Spoofed official source",
                "domains": ["test"],
                "keywords": ["test evidence"],
                "content": excerpt,
                "retrieved_at": "2026-09-07T00:00:00Z",
                "retrieval_context": "Red-team fixture",
                "supports": [],
                "limitations": "Unverified host",
                "deadline": None,
                "destination": None,
                "required_items": [],
                "content_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
            }
        ],
    }
    path = tmp_path / "spoof.json"
    path.write_text(json.dumps(payload))
    provider = OfficialEvidenceProvider(path)
    result = provider.search("test evidence", "test")
    assert result[0].source_type == "UNVERIFIED"


def test_action_prepared_requires_primary_node_bound_evidence_and_context(store: InvestigationStore) -> None:
    created = store.spawn("Transfer Indiana driver license", "driver license", "root_move", "State changed", "test")
    evidence = store.search_evidence(
        created["node_id"],
        "Ohio new resident transfer out of state driver license within 30 days",
        "driver license",
    )
    primary = next(
        item for item in evidence["results"]
        if item["source_type"] == "PRIMARY_OFFICIAL" and item.get("deadline")
    )
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "Ohio requires an incoming resident to transfer an out-of-state driver license.",
        [primary["source_id"]],
        "The retrieved BMV rule is applied to the configured Indiana license and Ohio move.",
        action={
            "what": "Transfer the out-of-state driver license to an Ohio driver license.",
            "when": "within 30 days",
            "deadline_source_id": primary["source_id"],
            "where": "Ohio BMV",
        },
        applicability={
            "rule": "Incoming Ohio residents transfer an out-of-state driver license.",
            "why_applies": "Alex holds an Indiana driver license and is moving to Ohio.",
            "trigger_facts": ["person.drivers_license.held", "person.drivers_license.state", "event.to_state"],
        },
        uncertainty=[],
    )
    node = store.nodes[created["node_id"]]
    assert result["status"] == "ACTION_PREPARED"
    assert node.action["when"] == "Within 30 days of establishing Ohio residency."
    assert node.action["need"]
    assert node.evidence[0]["source_url"].startswith("https://")


def test_unverified_evidence_cannot_become_action_prepared(store: InvestigationStore) -> None:
    created = store.spawn("Unsupported filing", "test", "root_move", "Red team", "test")
    excerpt = "File a test form after moving to Ohio."
    evidence = Evidence(
        source_id="UNVERIFIED-ATTACK",
        source_type="UNVERIFIED",
        source_url="https://example.com/advice",
        publisher="Unknown",
        title="Unofficial advice",
        excerpt=excerpt,
        retrieved_at="2026-09-07T00:00:00Z",
        query="test filing",
        retrieval_context="Red-team fixture",
        content_sha256=hashlib.sha256(excerpt.encode()).hexdigest(),
    )
    store.retrieved_evidence[evidence.source_id] = evidence
    store.node_evidence_ids[created["node_id"]] = {evidence.source_id}
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "The model tried to use weak evidence.",
        [evidence.source_id],
        "Unsupported model claim.",
        action={"what": "File the test form after moving to Ohio.", "when": "UNKNOWN"},
        applicability={
            "rule": "Unverified rule",
            "why_applies": "Alex moved to Ohio.",
            "trigger_facts": ["event.to_state"],
        },
    )
    assert result["status"] == "UNKNOWN"
    assert store.safeguards["weak_evidence_coercions"] == 1


def test_missing_alex_fact_blocks_action_prepared(store: InvestigationStore) -> None:
    created = store.spawn("Update payroll", "tax", "root_move", "Alex has an employer", "test")
    evidence = store.search_evidence(created["node_id"], "move update IT 4 employer withholding", "tax payroll")
    source = next(item for item in evidence["results"] if "IT 4" in item["excerpt"])
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "Attempted action with an invented Alex fact.",
        [source["source_id"]],
        "The model asserted an unprovided employer location.",
        action={"what": "Update employer withholding using an IT 4.", "when": "UNKNOWN"},
        applicability={
            "rule": "An employee who moves during the tax year updates IT 4.",
            "why_applies": "Alex allegedly works in Ohio.",
            "trigger_facts": ["person.employer", "person.employer_ohio_nexus"],
        },
    )
    assert result["status"] == "UNKNOWN"
    assert "person.employer_ohio_nexus" in store.nodes[created["node_id"]].applicability["unresolved_facts"]


def test_source_required_age_fact_blocks_voter_action_when_age_is_missing(store: InvestigationStore) -> None:
    created = store.spawn("Register to vote in Ohio", "voter registration", "root_move", "State changed", "test")
    evidence = store.search_evidence(created["node_id"], "Ohio voter registration eligibility deadline", "voter registration")
    source = next(item for item in evidence["results"] if item["source_type"] == "PRIMARY_OFFICIAL")
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "Attempted voter action without Alex's age.",
        [source["source_id"]],
        "Citizenship and destination are known, but age is not.",
        action={"what": "Register to vote in Ohio.", "when": "UNKNOWN"},
        applicability={
            "rule": "Ohio voter registration has eligibility conditions.",
            "why_applies": "Alex is a U.S. citizen moving to Ohio.",
            "trigger_facts": ["person.citizenship", "event.to_state"],
        },
    )
    assert result["status"] == "UNKNOWN"
    assert "person.age" in store.nodes[created["node_id"]].applicability["unresolved_facts"]


def test_invented_deadline_is_removed_even_when_action_is_supported(store: InvestigationStore) -> None:
    created = store.spawn("Report insurance address", "auto insurance", "root_move", "Address changed", "test")
    evidence = store.search_evidence(created["node_id"], "report auto insurance policy address change", "auto insurance")
    source = next(
        item
        for item in evidence["results"]
        if item["source_type"] == "PRIMARY_OFFICIAL" and "report any changes" in item["excerpt"].lower()
    )
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "The Ohio insurance regulator says policyholders should report address changes.",
        [source["source_id"]],
        "Alex has auto insurance and the move changes the address.",
        action={
            "what": "Report the changed address to the auto insurer.",
            "when": "Within 10 days",
            "deadline_source_id": source["source_id"],
        },
        applicability={
            "rule": "Report address changes that affect the policy.",
            "why_applies": "Alex has auto insurance and changed states.",
            "trigger_facts": ["person.auto_insurance", "event.from_state", "event.to_state"],
        },
    )
    assert result["status"] == "ACTION_PREPARED"
    assert store.nodes[created["node_id"]].action["when"] == "UNKNOWN"
    assert store.safeguards["deadline_coercions"] == 1


def test_unsupported_model_action_is_downgraded(store: InvestigationStore) -> None:
    created = store.spawn("Review vehicle title", "vehicle", "root_move", "Vehicle moved", "test")
    evidence = store.search_evidence(created["node_id"], "out of state vehicle title Ohio", "vehicle")
    source = next(
        item
        for item in evidence["results"]
        if item["source_type"] == "PRIMARY_OFFICIAL" and "out-of-state title must be converted" in item["excerpt"].lower()
    )
    result = store.record(
        created["node_id"],
        "ACTION_PREPARED",
        "The model tried to add an unrelated action.",
        [source["source_id"]],
        "Unsupported model knowledge.",
        action={"what": "Enroll Alex in a public library.", "when": "UNKNOWN"},
        applicability={
            "rule": "An out-of-state vehicle title must be converted to an Ohio title.",
            "why_applies": "Alex owns an Indiana vehicle and moved to Ohio.",
            "trigger_facts": ["person.vehicle.owns_personally", "person.vehicle.state", "event.to_state"],
        },
    )
    assert result["status"] == "UNKNOWN"
    assert store.safeguards["unsupported_action_coercions"] == 1


def test_does_not_apply_requires_a_negated_context_trigger(store: InvestigationStore) -> None:
    created = store.spawn("Professional license transfer", "professional licensing", "root_move", "Possible credential", "test")
    evidence = store.search_evidence(created["node_id"], "Ohio professional license apply renew", "professional licensing")
    result = store.record(
        created["node_id"],
        "DOES_NOT_APPLY",
        "Alex has no professional license.",
        [item["source_id"] for item in evidence["results"]],
        "The official portal concerns licenses Alex does not hold.",
        applicability={
            "rule": "Professional licensing applies to a relevant regulated credential.",
            "why_applies": "The trigger is absent because Alex has no professional license.",
            "trigger_facts": ["person.professional_license"],
        },
    )
    assert result["status"] == "DOES_NOT_APPLY"


def test_fabricated_human_decision_is_downgraded(store: InvestigationStore) -> None:
    created = store.spawn("Invent a choice", "driver license", "root_move", "Red team", "test")
    evidence = store.search_evidence(created["node_id"], "Ohio driver license transfer", "driver license")
    source = next(item for item in evidence["results"] if item["source_type"] == "PRIMARY_OFFICIAL")
    result = store.record(
        created["node_id"],
        "HUMAN_DECISION",
        "The model tried to manufacture a choice.",
        [source["source_id"]],
        "No genuine alternatives were evidenced.",
        action={"what": "Choose an unspecified option.", "decision_options": []},
        applicability={
            "rule": "Driver license transfer rule",
            "why_applies": "Alex has an Indiana driver license.",
            "trigger_facts": ["person.drivers_license.held"],
        },
    )
    assert result["status"] == "UNKNOWN"
    assert store.safeguards["human_decision_coercions"] == 1


def test_find_existing_payload_repairs_invalid_apostrophe_escape() -> None:
    payload = "[{\"title\":\"Ohio driver\\'s license transfer\",\"domain\":\"driver license\"}]"
    parsed, repaired = parse_json_array(payload)
    assert repaired is True
    assert parsed[0]["title"] == "Ohio driver's license transfer"


def test_tool_payload_parser_recovers_first_array_from_duplicated_output() -> None:
    payload = '[{"title":"first","domain":"test"}][{"title":"duplicate","domain":"test"}]'
    parsed, repaired = parse_json_array(payload)
    assert repaired is True
    assert parsed == [{"title": "first", "domain": "test"}]


def test_catalog_integrity_tampering_is_rejected(tmp_path: Path) -> None:
    source_path = Path(__file__).with_name("official_evidence.json")
    payload = json.loads(source_path.read_text())
    payload["documents"][0]["content"] += " tampered"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="integrity check failed"):
        OfficialEvidenceProvider(path)
