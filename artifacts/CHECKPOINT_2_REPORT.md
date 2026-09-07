# Ripple — Checkpoint 2 Report

**Author:** Manus AI  
**Scenario:** Alex Morgan, Indianapolis, Indiana → Columbus, Ohio  
**Configured demonstration date:** 2026-10-01  
**Scope:** Checkpoint 2 only

## Executive conclusion

Checkpoint 2 replaces Ripple's active synthetic rule layer with a reproducible catalog of 27 verified public-source records. It preserves the Checkpoint 1 Strands discovery engine, recursive graph, provenance separation, uncertainty handling, and stopping guards. It adds deterministic source classification, source integrity checks, node-bound applicability, supported deadlines, prepared-action output, causal child provenance, and adversarial trust tests.

**Checkpoint 2 does not receive an unconditional full-pass designation in this report.** A successful CP2 Strands run produced a runtime graph that passes all 14 current graph validators. However, the final exact-code live rerun was blocked after the configured model gateway returned HTTP 412 `usage exhausted`. The successful live artifact predates the last source-required context-path and payload-hardening changes. Those final changes pass all deterministic tests, TypeScript checks, the production build, and server tests, but were not re-proven with a fresh model run. This is a validation-infrastructure failure, not concealed as a pass.

## 1. Architecture and evidence changes

The working Checkpoint 1 design remains intact. A React interface calls a public tRPC mutation. The Node server starts a request-scoped Python worker. A Strands discovery agent creates first-order candidate nodes without a supplied checklist. A Strands investigator retrieves evidence, produces applicability and action proposals, and discovers evidence-backed children. The mutable graph store is the deterministic trust boundary.

The former `MockEvidenceProvider` was replaced by `OfficialEvidenceProvider`. The active catalog stores source URL, publisher, title, retrieval time, relevant excerpt, research context, source limitations, deadline metadata, destination, required items, required Alex-context paths, and a SHA-256 content hash. The archived Checkpoint 1 catalog is retained for audit only and is not imported by runtime code.

## 2. Real sources used

Ripple's catalog includes Ohio BMV and Ohio Department of Public Safety pages for new residents, driver credentials, vehicle title transfer, VIN inspection, and first registration.[1] [2] [3] [4] [5] It includes Ohio Revised Code and Ohio Administrative Code sources for out-of-state vehicle inspection, license surrender, identification, and employer withholding.[6] [7] [8] [9] It includes Ohio Secretary of State and Franklin County election sources.[10] [11] [12] It includes Ohio Department of Taxation sources for residency, IT 4 withholding, and school-district income tax.[13] [14] [15] It includes USPS change-of-address and identification rules.[16] [17] [18] It also includes Ohio insurance-regulator guidance, a National Association of Insurance Commissioners consumer document, Ohio eLicense sources, and official school-attendance sources.[19] [20] [21] [22] [23]

Search snippets were not used as evidence. The catalog contains relevant text retrieved from the underlying source pages or official documents. Each record identifies the original research task and source limitations.

## 3. Source-quality enforcement

Source classification is deterministic and URL-host based. The engine does not trust a quality label supplied by catalog metadata. Allowlisted government and regulator hosts become `PRIMARY_OFFICIAL`. The National Association of Insurance Commissioners host becomes `AUTHORITATIVE_SECONDARY`. Other hosts become `UNVERIFIED`. A missing source becomes `EVIDENCE_GAP`.

Every catalog excerpt is hashed. A mismatch raises an error before the run begins. A red-team fixture that labels `example.com` as official is reclassified as `UNVERIFIED`. Administrative `ACTION_PREPARED` conclusions require a primary official source bound to that same node. Weak or unbound evidence causes a safe downgrade to `UNKNOWN`.

## 4. Applicability and prepared-action method

Every conclusion carries an applicability record with the retrieved rule, why it applies to Alex, context fact paths, resolved values, and unresolved paths. The trust layer resolves fact paths directly against the configured scenario. It also merges source-required context paths into the check. This prevents the model from omitting a controlling fact. For example, the voter source requires `person.age`; Alex's age is absent, so a voter action must remain `UNKNOWN` even if citizenship and destination are known.

Each node carries a prepared action with **WHAT**, **WHY**, **WHEN**, **WHERE**, **NEED**, **DEPENDS ON**, **STATUS**, and any decision options. `WHERE` and `NEED` are derived from retrieved evidence metadata rather than accepted from unsupported model text. A non-`UNKNOWN` deadline must name a node-bound trusted source with matching structured deadline text. Unsupported dates are removed and recorded as `UNKNOWN`; the node may remain `ACTION_PREPARED` when the action itself is supported.

Ripple does not submit, pay, file, notify, change insurance, or perform any external action.

## 5. Recursive discovery result

The preserved successful CP2 live graph contained three depth-two nodes. It discovered address-document preparation beneath the driver-license consequence, title transfer beneath the vehicle-registration consequence, and school-district lookup beneath the tax/payroll consequence. These nodes were created at runtime from retrieved parent evidence.

The final engine adds an explicit `caused_by_evidence_id` to every non-root child. The store accepts a child only when that source was retrieved for its parent and its text semantically supports the child. Duplicate, depth, and node-budget guards still execute before insertion. No child name, including VIN inspection, is hard-coded in the graph or orchestration logic.

## 6. Prior successful runtime graph

The latest completed live artifact before the final hardening contained the following runtime-generated graph:

| Depth | Status | Consequence | Parent |
| --- | --- | --- | --- |
| 0 | RESOLVED | Interstate Move: Indiana → Ohio | — |
| 1 | ACTION_PREPARED | Obtain Ohio driver's license within state deadline | Root |
| 1 | ACTION_PREPARED | Register vehicle in Ohio and obtain Ohio plates | Root |
| 1 | ACTION_PREPARED | Update auto insurance to Ohio residency and verify coverage | Root |
| 1 | ACTION_PREPARED | Update voter registration to Ohio | Root |
| 1 | ACTION_PREPARED | Change state income tax withholding and file resident tax in Ohio | Root |
| 1 | UNKNOWN | Jury duty eligibility in Ohio | Root |
| 1 | RESOLVED | Professional license applicability check | Root |
| 1 | ACTION_PREPARED | Employer payroll/state registration uncertainty | Root |
| 2 | ACTION_PREPARED | Gather two acceptable documents proving Ohio street address | Driver license |
| 2 | ACTION_PREPARED | Transfer out-of-state title at County Clerk of Courts Title Office | Vehicle registration |
| 2 | ACTION_PREPARED | Find Alex's Ohio school district | Tax/withholding |
| 1 | DOES_NOT_APPLY | Transfer or notify Ohio professional licensing boards | Root |

This graph is retained as a **prior successful live artifact**, not misrepresented as the final exact-code rerun. The current deterministic layer is stricter. In particular, it would force unsupported eligibility or source-required context gaps to `UNKNOWN`.

## 7. UNKNOWN and HUMAN_DECISION behavior

Missing evidence, missing source-required person facts, unverified evidence, cross-node evidence reuse, unsupported action text, and orchestration incompleteness all produce `UNKNOWN`. The final exact code also fails visibly if discovery produces no nodes, rather than returning a root-only graph as a successful investigation.

`HUMAN_DECISION` requires primary evidence and at least two genuine evidence-backed options. A red-team attempt to manufacture a choice is downgraded to `UNKNOWN`. No `HUMAN_DECISION` node is required merely to satisfy a test.

## 8. Red-team results

| Attack | Deterministic result |
| --- | --- |
| Use unsupported model knowledge | Unsupported action text is downgraded to `UNKNOWN`. |
| Reuse evidence from another node | Node-binding check rejects the evidence and produces an evidence gap. |
| Invent a deadline | The deadline is removed; `WHEN` becomes `UNKNOWN`. |
| Promote weak evidence to `ACTION_PREPARED` | Non-primary evidence cannot support the administrative action. |
| Spoof source metadata | Source class is recomputed from the URL host. |
| Alter a captured excerpt | SHA-256 integrity verification rejects the catalog. |
| Create a duplicate | Normalized duplicate detection blocks insertion. |
| Create an unsupported child | Parent-bound source and semantic-overlap guards block insertion. |
| Omit a controlling Alex fact | Source-required context paths force a downgrade to `UNKNOWN`. |
| Manufacture a human choice | Missing evidenced options force `UNKNOWN`. |
| Send invalid apostrophe JSON | The parser repairs the known invalid escape and records the repair. |
| Send duplicated trailing JSON | The parser recovers the first complete array and records the repair. |

All 24 deterministic Python tests pass.

## 9. Full tests, build, and Checkpoint 1 regressions

| Gate | Result |
| --- | --- |
| Preserved Checkpoint 1 Python regressions | PASS, included in 24-test suite |
| Checkpoint 2 trust and red-team tests | PASS |
| Python total | **24 passed** |
| TypeScript type check | PASS |
| Vite/Express production build | PASS |
| Vitest server suite | **3 passed** across two files |
| WebDev health and pre-run/error-path UI verification | PASS; no type errors and no partial graph accepted on gateway failure |
| Prior live CP2 graph under current validator | **14/14 PASS** |
| Final exact-code live Strands rerun | **BLOCKED** by HTTP 412 `usage exhausted` |

The production build emitted only the existing large-chunk warning. No type or build error was reported.

## 10. `find_existing_node` investigation

The Checkpoint 1 failure was an invalid JSON escape in a model-generated tool payload: an apostrophe appeared as `\'`, which is not valid JSON. The issue was not a duplicate-detection algorithm failure. All batched JSON tools now share a guarded parser. It repairs that specific escape, can recover the first complete array from duplicated trailing model output, records every repair, and rejects other malformed payloads. Dedicated regression tests cover both cases.

The main discovery path no longer requires a separate `find_existing_node` call because `spawn_investigation` performs the same deterministic lookup immediately before insertion. The tool remains available for fallback graph review and diagnostics. Duplicate insertion is still impossible through either route.

## 11. Known limitations

The catalog is a verified snapshot, not a live crawler. Source pages can change after retrieval. The catalog builder is reproducible, but refreshing it still requires a new research pass. Some official pages were not sufficiently explicit for every desired conclusion. Ripple therefore retains `UNKNOWN` rather than filling gaps from model knowledge.

Alex's context intentionally lacks age, exact street address, vehicle model year/fuel type, lien status, work location, employment nexus, insurer contract terms, and whether the move satisfies a specific statutory residency trigger on the configurable date. These omissions can prevent otherwise plausible actions from reaching `ACTION_PREPARED`.

The final exact-code live rerun failed because the configured model gateway returned `usage exhausted`. The engine now surfaces that as an error. This limitation prevents an unconditional CP2 full-pass claim even though a prior CP2 live run passed all current graph validators and all final deterministic gates pass.

## 12. Files changed

| Component | Purpose |
| --- | --- |
| `python/ripple_engine.py` | Official provider, trust guards, action/applicability model, causal source IDs, payload recovery, visible model-failure handling. |
| `python/official_evidence.json` | Active 27-record verified evidence catalog. |
| `python/build_official_catalog.py` | Reproducible catalog builder. |
| `python/test_ripple_engine.py` | Preserved Checkpoint 1 regressions migrated to the official provider. |
| `python/test_trust_layer.py` | Checkpoint 2 trust and red-team tests. |
| `python/validate_result.py` | Fourteen runtime graph acceptance checks. |
| `client/src/pages/Home.tsx` | Existing graph plus action, applicability, deadline, source link, quality, reasoning, uncertainty, and causal-evidence inspection. |
| `server/ripple.ts` | Request timeout aligned to managed runtime. |
| `server/ripple.test.ts` | Structured success/error payload parsing regressions. |
| `README.md` | Checkpoint 2 architecture and validation documentation. |
| `artifacts/cp2-official-source-research.json` | Structured source-research output. |
| `artifacts/checkpoint1-mock-evidence.json` | Archived and inactive CP1 synthetic catalog. |
| `artifacts/checkpoint2-prior-live-runtime-graph.json` | Prior successful CP2 Strands graph. |
| `artifacts/checkpoint2-prior-live-validation.json` | Current-validator result for that graph. |
| `artifacts/checkpoint2-final-validation-summary.json` | Exact final pass/blocker summary. |

## 13. Pass determination

**Checkpoint 2 is functionally implemented but not fully revalidated on the final exact code.** Requirements 1–13 are implemented and deterministically tested. A real Strands CP2 graph exists and passes all current runtime validators. However, because the last live rerun was blocked by the model gateway after final hardening, the strict final answer is **NO: CP2 does not fully pass the requested completion standard yet**. The remaining step is a fresh successful Strands run and browser inspection under the final commit; no Checkpoint 3 work is required or included.

## References

[1]: https://www.bmv.ohio.gov/new-to-ohio.aspx "Ohio BMV — New Ohio Residents"
[2]: https://www.bmv.ohio.gov/titles-new.aspx "Ohio BMV — Vehicle Titles: How to Title"
[3]: https://www.bmv.ohio.gov/vr-firstissuance.aspx "Ohio BMV — Vehicle Registration: First Issuance"
[4]: https://www.bmv.ohio.gov/dl-identity-documents.aspx "Ohio BMV — Driver License and ID Acceptable Documents"
[5]: https://bmv.ohio.gov/more-inv-about.aspx "Ohio BMV — Investigations"
[6]: https://codes.ohio.gov/ohio-revised-code/section-4505.061 "Ohio Revised Code Section 4505.061"
[7]: https://codes.ohio.gov/ohio-revised-code/section-4507.213 "Ohio Revised Code Section 4507.213"
[8]: https://codes.ohio.gov/ohio-administrative-code/rule-4501:1-1-21 "Ohio Administrative Code Rule 4501:1-1-21"
[9]: https://codes.ohio.gov/ohio-revised-code/section-5747.06 "Ohio Revised Code Section 5747.06"
[10]: https://www.ohiosos.gov/elections/register-to-vote "Ohio Secretary of State — Register to Vote"
[11]: https://www.ohiosos.gov/assets/vr-form-english.pdf "Ohio Voter Registration and Information Update Form"
[12]: https://www.franklincountyohio.gov/County-Government/Elections/Voter-Registration "Franklin County Board of Elections — Register to Vote"
[13]: https://tax.ohio.gov/individual/who-must-file/what-does-ohio-residency-mean-for-taxes "Ohio Department of Taxation — What Does Ohio Residency Mean for Taxes"
[14]: https://tax.ohio.gov/static/forms/employer_withholding/generic/wth-it4-combined.pdf "Ohio IT 4 and Instructions"
[15]: https://tax.ohio.gov/individual/school-district-income-tax "Ohio Department of Taxation — School District Income Tax"
[16]: https://www.usps.com/manage/forward.htm "USPS — Standard Forward Mail and Change of Address"
[17]: https://pe.usps.com/text/dmm300/507.htm "USPS Domestic Mail Manual 507"
[18]: https://pe.usps.com/text/dmm300/608.htm "USPS Domestic Mail Manual 608"
[19]: https://insurance.ohio.gov/consumers/automobile/automobile-insurance-guide "Ohio Department of Insurance — Automobile Insurance Guide"
[20]: https://insurance.ohio.gov/wps/wcm/connect/gov/d40aa62a-ab81-4f57-b315-99ba5ed64e7f/Automobile+Insurance+101-4.pdf?MOD=AJPERES "Ohio Department of Insurance — Automobile Insurance 101"
[21]: https://content.naic.org/sites/default/files/consumer-auto-shopping-tool.pdf "NAIC — A Shopping Tool for Auto Insurance"
[22]: https://ohio.gov/jobs/resources/elicense-ohio "Ohio.gov — eLicense Ohio"
[23]: https://codes.ohio.gov/ohio-revised-code/chapter-3321 "Ohio Revised Code Chapter 3321 — School Attendance"
