from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

WORKFLOW_OUTPUT = Path(__file__).parents[1] / "artifacts" / "cp2-official-source-research.json"
OUTPUT = Path(__file__).with_name("official_evidence.json")

DOMAIN_CONFIG = {
    "ripple-checkpoint-2-ohio-new-resident-driver-license": {
        "domains": ["driver license", "driving", "identity", "ohio bmv"],
        "keywords": ["driver license", "out of state license", "new resident", "deputy registrar", "vision screening", "acceptable documents"],
        "required_context_paths": ["person.drivers_license.held", "person.drivers_license.state", "event.to_state", "event.move_date"],
    },
    "ripple-checkpoint-2-ohio-out-of-state-vehicle-title-registration-inspection": {
        "domains": ["vehicle", "title", "registration", "inspection", "ohio bmv"],
        "keywords": ["vehicle title", "vehicle registration", "license plates", "out of state", "vin inspection", "physical inspection"],
        "required_context_paths": ["person.vehicle.owns_personally", "person.vehicle.state", "event.to_state", "event.move_date"],
    },
    "ripple_checkpoint_2_ohio_voter_registration_after_interstate_move": {
        "domains": ["voter registration", "elections", "civic"],
        "keywords": ["register to vote", "voter registration", "address", "citizen", "county board", "election deadline"],
        "required_context_paths": ["person.citizenship", "person.voter_registration.registered", "event.to_state", "person.age"],
    },
    "ripple-checkpoint-2-ohio-residency-tax-employer-withholding": {
        "domains": ["tax", "payroll", "employer", "withholding", "residency", "school district"],
        "keywords": ["part year resident", "income tax", "withholding", "it 4", "employer", "school district", "permanent move"],
        "required_context_paths": ["person.employer", "event.to_state", "event.move_date"],
    },
    "ripple-checkpoint-2-usps-change-of-address-mail-forwarding": {
        "domains": ["mail forwarding", "postal", "usps", "change of address"],
        "keywords": ["mail forwarding", "change of address", "permanent", "temporary", "identity verification", "ps form 3575"],
        "required_context_paths": ["person.name", "event.from_city", "event.to_city", "event.move_date"],
    },
    "ripple-checkpoint-2-auto-insurance-address-or-garaging-state-change": {
        "domains": ["auto insurance", "insurance", "policy", "garaging"],
        "keywords": ["auto insurance", "policy", "address", "vehicle", "garaging", "premium", "report changes"],
        "required_context_paths": ["person.auto_insurance", "person.vehicle.owns_personally", "event.to_state"],
    },
    "ripple-checkpoint-2-professional-license-applicability": {
        "domains": ["professional licensing", "occupation", "employment"],
        "keywords": ["professional license", "licensing board", "elicense", "apply", "renew"],
        "required_context_paths": ["person.professional_license"],
    },
    "ripple_checkpoint_2_context_negative_education": {
        "domains": ["education", "school", "children", "family"],
        "keywords": ["child", "children", "school attendance", "enrollment", "compulsory school age"],
        "required_context_paths": ["person.children"],
    },
}

EXCLUDED_URL_PARTS = ["/2025/it1040-booklet.pdf"]

DEADLINES = {
    "https://www.bmv.ohio.gov/new-to-ohio.aspx": {
        "text": "Within 30 days of establishing Ohio residency.",
        "kind": "DAYS_AFTER_MOVE_DATE",
        "days": 30,
    },
    "https://codes.ohio.gov/ohio-revised-code/section-4507.213": {
        "text": "Within 30 days of becoming an Ohio resident.",
        "kind": "DAYS_AFTER_MOVE_DATE",
        "days": 30,
    },
    "https://www.ohiosos.gov/elections/register-to-vote": {
        "text": "Received or postmarked by the 30th day before the election in which Alex intends to vote.",
        "kind": "CONDITIONAL",
    },
    "https://www.ohiosos.gov/assets/vr-form-english.pdf": {
        "text": "Received or postmarked by the 30th day before the election in which Alex intends to vote.",
        "kind": "CONDITIONAL",
    },
    "https://tax.ohio.gov/static/forms/employer_withholding/generic/wth-it4-combined.pdf": {
        "text": "Immediately after moving during the tax year.",
        "kind": "TEXTUAL",
    },
    "https://www.usps.com/manage/forward.htm": {
        "text": "No mandatory deadline stated; USPS recommends allowing up to 2 weeks for forwarding to begin.",
        "kind": "GUIDANCE",
    },
}

DESTINATIONS = {
    "https://www.bmv.ohio.gov/new-to-ohio.aspx": "Ohio BMV Deputy Registrar license agency; County Clerk of Courts Title Office for vehicle title",
    "https://www.bmv.ohio.gov/titles-new.aspx": "Ohio County Clerk of Courts Title Office",
    "https://codes.ohio.gov/ohio-revised-code/section-4505.061": "Ohio deputy registrar, participating title office, or licensed Ohio motor vehicle dealer",
    "https://www.ohiosos.gov/elections/register-to-vote": "Ohio online voter registration or Alex's county board of elections",
    "https://www.ohiosos.gov/assets/vr-form-english.pdf": "Alex's Ohio county board of elections",
    "https://www.franklincountyohio.gov/County-Government/Elections/Voter-Registration": "Franklin County Board of Elections",
    "https://tax.ohio.gov/static/forms/employer_withholding/generic/wth-it4-combined.pdf": "Alex's employer",
    "https://tax.ohio.gov/individual/who-must-file/what-does-ohio-residency-mean-for-taxes": "Ohio Department of Taxation",
    "https://tax.ohio.gov/individual/school-district-income-tax": "Alex's employer after confirming the school district with Ohio's Finder",
    "https://www.usps.com/manage/forward.htm": "Official USPS Change of Address website or a local Post Office",
    "https://pe.usps.com/text/dmm300/507.htm": "Official USPS Change of Address website or a local Post Office",
    "https://insurance.ohio.gov/consumers/automobile/automobile-insurance-guide": "Alex's auto insurer",
    "https://ohio.gov/jobs/resources/elicense-ohio": "Applicable Ohio licensing board, only if Alex later needs a regulated credential",
}

REQUIRED_ITEMS = {
    "https://www.bmv.ohio.gov/new-to-ohio.aspx": [
        "Unexpired out-of-state driver license",
        "Proof of legal name, date of birth, Social Security number, U.S. citizenship or legal presence, and Ohio residential address",
        "BMV 5745 application",
        "Vision screening",
    ],
    "https://www.bmv.ohio.gov/titles-new.aspx": [
        "Out-of-state title certificate; photocopies are not accepted",
        "Acceptable identification and Social Security numbers for all parties",
        "Out-of-state VIN inspection",
        "Title fees and any supported conditional documents",
    ],
    "https://codes.ohio.gov/ohio-revised-code/section-4505.061": [
        "Physical inspection certificate verifying make, body type, model, mileage, and VIN",
    ],
    "https://www.ohiosos.gov/elections/register-to-vote": [
        "Online: Ohio driver license or ID number, name, date of birth, address, and last four SSN digits",
        "If online information is unavailable: signed voter registration form sent to county board of elections",
    ],
    "https://www.ohiosos.gov/assets/vr-form-english.pdf": [
        "Residential address, identification number or last four SSN digits, signature, and date",
    ],
    "https://tax.ohio.gov/static/forms/employer_withholding/generic/wth-it4-combined.pdf": [
        "Updated IT 4 with name, SSN, address, school district name and number, signature, and date",
    ],
    "https://www.usps.com/manage/forward.htm": [
        "Old and new mailing addresses",
        "Online identity verification and matching billing address, or acceptable photo ID for in-person filing",
        "PS Form 3575 for in-person filing",
    ],
    "https://pe.usps.com/text/dmm300/608.htm": [
        "Current primary photo identification; secondary address identification may be required",
    ],
    "https://insurance.ohio.gov/consumers/automobile/automobile-insurance-guide": [
        "New address and any changed driver or vehicle information; carrier-specific documentation remains unknown",
    ],
}

OFFICIAL_HOSTS = {
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
SECONDARY_HOSTS = {"content.naic.org"}


def classify(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host in OFFICIAL_HOSTS:
        return "PRIMARY_OFFICIAL"
    if host in SECONDARY_HOSTS:
        return "AUTHORITATIVE_SECONDARY"
    return "UNVERIFIED"


def main() -> None:
    payload = json.loads(WORKFLOW_OUTPUT.read_text())
    documents = []
    for item in payload["items"]:
        if not item.get("ok"):
            continue
        value = item["value"]
        config = DOMAIN_CONFIG[value["id"]]
        for source in value["sources"]:
            url = source["url"]
            if any(part in url for part in EXCLUDED_URL_PARTS):
                continue
            source_id = "OFFICIAL-" + hashlib.sha256(f"{value['id']}|{url}".encode()).hexdigest()[:12].upper()
            documents.append(
                {
                    "source_id": source_id,
                    "source_type": classify(url),
                    "source_url": url,
                    "publisher": source["publisher"],
                    "title": source["title"],
                    "domains": config["domains"],
                    "keywords": config["keywords"],
                    "content": source["exact_excerpt"],
                    "retrieved_at": source["retrieved_at"],
                    "retrieval_context": source["retrieval_context"],
                    "supports": source["supports"],
                    "limitations": source["limitations"],
                    "deadline": DEADLINES.get(url),
                    "destination": DESTINATIONS.get(url),
                    "required_items": REQUIRED_ITEMS.get(url, []),
                    "required_context_paths": config["required_context_paths"],
                    "content_sha256": hashlib.sha256(source["exact_excerpt"].encode()).hexdigest(),
                }
            )
    output = {
        "catalog_version": "checkpoint-2.official.1",
        "label": "VERIFIED PUBLIC EVIDENCE — RETRIEVED FROM OFFICIAL SOURCES",
        "generated_from": "Independent direct retrieval of underlying public pages and official PDFs; never search snippets",
        "classification_policy": {
            "PRIMARY_OFFICIAL": "Official government, statutory, agency, or USPS source on an allowlisted domain.",
            "AUTHORITATIVE_SECONDARY": "Recognized regulator association or similar authoritative secondary body.",
            "UNVERIFIED": "Source not on an allowlisted authoritative domain.",
            "EVIDENCE_GAP": "No adequate evidence retrieved for the queried consequence.",
        },
        "documents": sorted(documents, key=lambda document: document["source_id"]),
    }
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(documents)} sources to {OUTPUT}")


if __name__ == "__main__":
    main()
