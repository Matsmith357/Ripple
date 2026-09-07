import { describe, expect, it } from "vitest";
import { parseWorkerPayload } from "./ripple";

describe("parseWorkerPayload", () => {
  it("preserves a successful runtime graph payload", () => {
    const payload = parseWorkerPayload(
      JSON.stringify({
        checkpoint: 2,
        run_id: "run_test",
        generated_at: "2026-09-07T00:00:00Z",
        generated_at_runtime: true,
        engine: "Strands Agents SDK",
        model: "test-model",
        evidence_mode: "VERIFIED PUBLIC SOURCES",
        scenario: {},
        graph: { root_id: "root_move", nodes: [], edges: [] },
        activity: [],
        safeguards: {},
        strands_metrics: [],
      }),
    );

    expect("run_id" in payload && payload.run_id).toBe("run_test");
  });

  it("preserves the worker's safe structured error", () => {
    const payload = parseWorkerPayload(
      JSON.stringify({
        error: "Strands discovery did not produce any consequence nodes. APIStatusError: usage exhausted",
        error_type: "RuntimeError",
      }),
    );

    expect(payload).toEqual({
      error: "The model gateway returned HTTP 412: usage is exhausted for this environment. No partial graph was accepted.",
      error_type: "RuntimeError",
    });
  });
});
