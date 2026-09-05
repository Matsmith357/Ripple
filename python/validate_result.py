from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(payload: dict) -> list[dict[str, object]]:
    nodes = payload["graph"]["nodes"]
    non_root = [node for node in nodes if node["parent_id"] is not None]
    domains = {node["domain"] for node in non_root}
    node_ids = {node["id"] for node in nodes}
    terminal = {"RESOLVED", "DOES_NOT_APPLY", "ACTION_NEEDED", "HUMAN_DECISION", "UNKNOWN"}
    checks = [
        {
            "id": 1,
            "name": "multiple consequence domains discovered without a supplied final checklist",
            "passed": len(domains) >= 3 and len(non_root) >= 3,
            "detail": f"{len(non_root)} runtime nodes across {len(domains)} domains",
        },
        {
            "id": 2,
            "name": "non-applicable consequence becomes DOES_NOT_APPLY",
            "passed": any(node["status"] == "DOES_NOT_APPLY" for node in non_root),
            "detail": [node["title"] for node in non_root if node["status"] == "DOES_NOT_APPLY"],
        },
        {
            "id": 3,
            "name": "a consequence legitimately spawns a downstream consequence",
            "passed": any(node["depth"] >= 2 and node["parent_id"] != "root_move" for node in non_root),
            "detail": [node["title"] for node in non_root if node["depth"] >= 2],
        },
        {
            "id": 4,
            "name": "duplicate investigations are prevented",
            "passed": len(node_ids) == len(nodes) and len({(node["domain"], node["title"].lower()) for node in nodes}) == len(nodes),
            "detail": payload["safeguards"]["duplicate_blocks"],
        },
        {
            "id": 5,
            "name": "maximum-depth and stopping safeguards work",
            "passed": max(node["depth"] for node in nodes) <= 3 and payload["safeguards"]["stop_reason"] == "NO_NEW_CONSEQUENCES",
            "detail": payload["safeguards"],
        },
        {
            "id": 6,
            "name": "missing evidence produces UNKNOWN",
            "passed": any(node["status"] == "UNKNOWN" for node in non_root),
            "detail": [node["title"] for node in non_root if node["status"] == "UNKNOWN"],
        },
        {
            "id": 7,
            "name": "every conclusion retains evidence and reason",
            "passed": all(node["status"] in terminal and node["reason"] and node["model_reasoning"] and node["evidence"] for node in nodes),
            "detail": f"checked {len(nodes)} terminal nodes",
        },
        {
            "id": 8,
            "name": "final graph is generated at runtime",
            "passed": payload.get("generated_at_runtime") is True and payload.get("run_id", "").startswith("run_") and len(nodes) > 1,
            "detail": {"run_id": payload.get("run_id"), "generated_at": payload.get("generated_at")},
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
