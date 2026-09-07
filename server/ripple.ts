import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

type WorkerError = { error: string; error_type?: string };

export function parseWorkerPayload(stdout: string): RippleRun | WorkerError {
  const payload = JSON.parse(stdout) as RippleRun | WorkerError;
  if ("error" in payload && payload.error.includes("usage exhausted")) {
    return {
      error: "The model gateway returned HTTP 412: usage is exhausted for this environment. No partial graph was accepted.",
      error_type: payload.error_type ?? "RuntimeError",
    };
  }
  return payload;
}

export type RippleRun = {
  checkpoint: number;
  run_id: string;
  generated_at: string;
  generated_at_runtime: boolean;
  engine: string;
  model: string;
  evidence_mode: string;
  scenario: Record<string, unknown>;
  graph: {
    root_id: string;
    nodes: Array<Record<string, any>>;
    edges: Array<{ source: string; target: string }>;
  };
  activity: Array<Record<string, any>>;
  safeguards: Record<string, any>;
  strands_metrics: Array<Record<string, any>>;
};

export async function runRipple(moveDate: string): Promise<RippleRun> {
  const script = path.resolve(process.cwd(), "python", "ripple_engine.py");
  let stdout = "";
  let stderr = "";
  try {
    const result = await execFileAsync(
      "python3",
      [script, "--move-date", moveDate, "--max-depth", "3", "--max-nodes", "14"],
      {
        cwd: process.cwd(),
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
        timeout: 179_000,
        maxBuffer: 12 * 1024 * 1024,
      },
    );
    stdout = result.stdout;
    stderr = result.stderr;
  } catch (error) {
    const failed = error as Error & { stdout?: string; stderr?: string };
    stdout = failed.stdout ?? "";
    stderr = failed.stderr ?? "";
    if (!stdout.trim()) throw error;
  }

  if (stderr.trim()) {
    console.warn("[Ripple worker]", stderr.trim().slice(-2000));
  }

  const payload = parseWorkerPayload(stdout);
  if ("error" in payload) {
    throw new Error(`${payload.error_type}: ${payload.error}`);
  }
  return payload;
}
