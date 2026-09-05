import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

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
  const { stdout, stderr } = await execFileAsync(
    "python3",
    [script, "--move-date", moveDate, "--max-depth", "3", "--max-nodes", "14"],
    {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      timeout: 175_000,
      maxBuffer: 12 * 1024 * 1024,
    },
  );

  if (stderr.trim()) {
    console.warn("[Ripple worker]", stderr.trim().slice(-2000));
  }

  const payload = JSON.parse(stdout) as RippleRun | { error: string; error_type: string };
  if ("error" in payload) {
    throw new Error(`${payload.error_type}: ${payload.error}`);
  }
  return payload;
}
