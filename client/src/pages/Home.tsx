import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { trpc } from "@/lib/trpc";
import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  Car,
  CheckCircle2,
  CircleDot,
  Clock3,
  Database,
  ExternalLink,
  FileCheck2,
  GitBranch,
  HelpCircle,
  LoaderCircle,
  MapPin,
  Play,
  ShieldCheck,
  UserRound,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const statusStyles: Record<string, string> = {
  RESOLVED: "bg-slate-100 text-slate-700 border-slate-200",
  DOES_NOT_APPLY: "bg-zinc-100 text-zinc-600 border-zinc-200",
  ACTION_PREPARED: "bg-amber-50 text-amber-800 border-amber-200",
  HUMAN_DECISION: "bg-violet-50 text-violet-800 border-violet-200",
  UNKNOWN: "bg-rose-50 text-rose-800 border-rose-200",
  PENDING: "bg-sky-50 text-sky-800 border-sky-200",
};

const statusIcon: Record<string, typeof CheckCircle2> = {
  RESOLVED: CheckCircle2,
  DOES_NOT_APPLY: XCircle,
  ACTION_PREPARED: FileCheck2,
  HUMAN_DECISION: CircleDot,
  UNKNOWN: HelpCircle,
};

type Evidence = {
  source_id: string;
  source_type: string;
  source_url: string | null;
  publisher: string;
  title: string;
  excerpt: string;
  retrieved_at: string;
  query: string;
  retrieval_context: string;
  supports: string[];
  limitations: string;
  deadline: { text: string; kind: string; days?: number } | null;
  destination: string | null;
  required_items: string[];
  synthetic: boolean;
};

type Action = {
  what: string;
  why: string;
  when: string;
  deadline_source_id: string | null;
  where: string;
  need: string[];
  depends_on: string | null;
  decision_options: string[];
  status: string;
};

type Applicability = {
  rule: string;
  why_applies: string;
  trigger_facts: string[];
  resolved_facts: Record<string, unknown>;
  unresolved_facts: string[];
};

type Node = {
  id: string;
  title: string;
  domain: string;
  parent_id: string | null;
  depth: number;
  status: string;
  reason: string;
  evidence: Evidence[];
  discovered_by: string;
  spawned_consequences: string[];
  why_investigated: string;
  model_reasoning: string;
  caused_by_evidence_id: string | null;
  applicability: Applicability;
  action: Action;
  uncertainty: string[];
};

type Run = {
  checkpoint: number;
  run_id: string;
  generated_at: string;
  engine: string;
  model: string;
  evidence_mode: string;
  graph: { root_id: string; nodes: Node[]; edges: Array<{ source: string; target: string }> };
  activity: Array<{
    sequence: number;
    at: string;
    actor: string;
    kind: string;
    message: string;
    node_id: string | null;
  }>;
  safeguards: Record<string, string | number | null>;
};

function StatusBadge({ status }: { status: string }) {
  const Icon = statusIcon[status] ?? CircleDot;
  return (
    <Badge variant="outline" className={`gap-1.5 rounded-full px-2.5 py-1 text-[10px] tracking-[0.08em] ${statusStyles[status] ?? statusStyles.PENDING}`}>
      <Icon className="size-3" />
      {status.replaceAll("_", " ")}
    </Badge>
  );
}

const qualityStyles: Record<string, string> = {
  PRIMARY_OFFICIAL: "border-emerald-200 bg-emerald-50 text-emerald-800",
  AUTHORITATIVE_SECONDARY: "border-sky-200 bg-sky-50 text-sky-800",
  UNVERIFIED: "border-orange-200 bg-orange-50 text-orange-800",
  EVIDENCE_GAP: "border-rose-200 bg-rose-50 text-rose-800",
  SYNTHETIC_SCENARIO: "border-slate-200 bg-slate-50 text-slate-700",
};

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="grid gap-1 border-t border-[#edf0ee] py-2.5 sm:grid-cols-[92px_1fr]">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#7b8781]">{label}</dt>
      <dd className="text-xs leading-5 text-[#364740]">{value || "UNKNOWN"}</dd>
    </div>
  );
}

function GraphNode({
  node,
  children,
  selectedId,
  onSelect,
}: {
  node: Node;
  children: Node[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const selected = node.id === selectedId;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onSelect(node.id)}
        className={`group w-full rounded-2xl border bg-white p-4 text-left shadow-[0_10px_30px_rgba(28,39,49,0.06)] transition duration-150 active:scale-[0.98] ${
          selected ? "border-[#ef6f4d] ring-2 ring-[#ef6f4d]/15" : "border-[#dfe5e2] hover:border-[#aebbb5]"
        }`}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <span className="rounded-lg bg-[#eff4f1] px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#587066]">
            d{node.depth} · {node.domain.replaceAll("_", " ")}
          </span>
          <StatusBadge status={node.status} />
        </div>
        <p className="text-sm font-semibold leading-5 text-[#16231f]">{node.title}</p>
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-[#66756f]">{node.reason}</p>
        <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-[#d45839] opacity-0 transition group-hover:opacity-100">
          Inspect reasoning <ArrowRight className="size-3" />
        </div>
      </button>
      {children.length > 0 && (
        <div className="ml-6 mt-3 space-y-3 border-l border-dashed border-[#b8c8c1] pl-4">
          {children.map(child => (
            <GraphNode
              key={child.id}
              node={child}
              children={[]}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [moveDate, setMoveDate] = useState("2026-10-01");
  const [run, setRun] = useState<Run | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState(0);
  const mutation = trpc.ripple.run.useMutation({
    onSuccess: data => {
      const typed = data as unknown as Run;
      setRun(typed);
      setSelectedId(typed.graph.nodes.find(node => node.parent_id !== null)?.id ?? typed.graph.root_id);
    },
  });

  const phases = [
    "Reading the event and person context",
    "Discovering possible consequence domains",
    "Retrieving verified public evidence",
    "Applying source-quality and applicability guards",
    "Following downstream consequences",
    "Checking stopping conditions",
  ];

  useEffect(() => {
    if (!mutation.isPending) {
      setPhase(0);
      return;
    }
    const timer = window.setInterval(() => setPhase(value => (value + 1) % phases.length), 5000);
    return () => window.clearInterval(timer);
  }, [mutation.isPending, phases.length]);

  const nodes = run?.graph.nodes ?? [];
  const root = nodes.find(node => node.id === run?.graph.root_id);
  const firstOrder = nodes.filter(node => node.parent_id === run?.graph.root_id);
  const selected = nodes.find(node => node.id === selectedId) ?? root ?? null;
  const statusCounts = useMemo(() => {
    return nodes.reduce<Record<string, number>>((acc, node) => {
      acc[node.status] = (acc[node.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [nodes]);

  return (
    <div className="min-h-screen bg-[#f5f3ee] text-[#17231f]">
      <header className="border-b border-[#d9dfdb] bg-[#f9f8f4]/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-[#183d32] text-white shadow-sm">
              <GitBranch className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-[-0.03em]">Ripple</h1>
                <Badge className="rounded-full bg-[#e8eee9] text-[10px] font-semibold text-[#40584e] hover:bg-[#e8eee9]">CHECKPOINT 2</Badge>
              </div>
              <p className="text-xs text-[#6c7772]">Consequence discovery, not task completion</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 text-xs text-[#65736c] sm:flex">
            <BrainCircuit className="size-4 text-[#d75d3e]" />
            Strands reasoning · verified public evidence
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-5 py-7 lg:px-8 lg:py-9">
        <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <div className="space-y-5">
            <div>
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#d75d3e]">The change</p>
              <h2 className="max-w-xl text-4xl font-bold leading-[1.05] tracking-[-0.045em] text-[#183028]">
                What else changed<br />when Alex moved?
              </h2>
              <p className="mt-4 max-w-sm text-sm leading-6 text-[#67756f]">
                Ripple reasons outward from one event, tests applicability with evidence, and stops when no material unresolved consequences remain.
              </p>
            </div>

            <Card className="overflow-hidden rounded-3xl border-[#d9dfdb] bg-white shadow-[0_16px_45px_rgba(28,39,49,0.08)]">
              <div className="border-b border-[#e6e9e6] bg-[#f7faf8] p-5">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-full bg-[#e5eee9] text-[#285445]"><UserRound className="size-5" /></div>
                  <div>
                    <h3 className="font-semibold">Alex Morgan</h3>
                    <p className="text-xs text-[#718078]">Synthetic user · United States citizen</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4 p-5">
                <div className="flex items-center justify-between rounded-2xl bg-[#f4f2ed] p-4">
                  <div>
                    <p className="text-xs font-medium text-[#76817c]">Origin</p>
                    <p className="mt-1 text-sm font-semibold">Indianapolis, Indiana</p>
                  </div>
                  <ArrowRight className="size-4 text-[#d75d3e]" />
                  <div className="text-right">
                    <p className="text-xs font-medium text-[#76817c]">Destination</p>
                    <p className="mt-1 text-sm font-semibold">Columbus, Ohio</p>
                  </div>
                </div>
                <div>
                  <label htmlFor="move-date" className="mb-2 block text-xs font-semibold uppercase tracking-[0.1em] text-[#6a7771]">Move date</label>
                  <Input id="move-date" type="date" value={moveDate} onChange={event => setMoveDate(event.target.value)} disabled={mutation.isPending} className="h-11 rounded-xl border-[#d8dfda] bg-white" />
                </div>
                <div className="flex flex-wrap gap-2 text-[11px] text-[#516159]">
                  <span className="rounded-full bg-[#edf3f0] px-2.5 py-1"><Car className="mr-1 inline size-3" />Indiana license + vehicle</span>
                  <span className="rounded-full bg-[#edf3f0] px-2.5 py-1"><ShieldCheck className="mr-1 inline size-3" />Auto insurance</span>
                  <span className="rounded-full bg-[#edf3f0] px-2.5 py-1">Employer + voter registration</span>
                </div>
                <Button
                  size="lg"
                  onClick={() => mutation.mutate({ moveDate })}
                  disabled={mutation.isPending || !moveDate}
                  className="h-12 w-full rounded-xl bg-[#e76343] font-semibold text-white shadow-[0_8px_20px_rgba(231,99,67,0.25)] hover:bg-[#d95638] active:scale-[0.98]"
                >
                  {mutation.isPending ? <><LoaderCircle className="animate-spin" /> Running Ripple…</> : <><Play className="fill-current" /> Run Ripple</>}
                </Button>
                <p className="text-center text-[10px] leading-4 text-[#89928e]">Uses live Strands tool calls. A run can take up to three minutes.</p>
              </div>
            </Card>
          </div>

          <div className="min-w-0 space-y-5">
            {mutation.isPending && (
              <Card className="overflow-hidden rounded-3xl border-[#d7e1dc] bg-[#183d32] p-6 text-white shadow-xl">
                <div className="flex items-start gap-4">
                  <div className="relative mt-0.5 grid size-11 shrink-0 place-items-center rounded-2xl bg-white/10">
                    <LoaderCircle className="size-5 animate-spin text-[#f5a88f]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#a8c3b8]">Live investigation</p>
                      <span className="text-xs text-[#afc7bd]">tool-driven</span>
                    </div>
                    <h3 className="mt-2 text-xl font-semibold tracking-[-0.02em]">{phases[phase]}</h3>
                    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-2/3 animate-pulse rounded-full bg-[#ef7a58]" /></div>
                    <p className="mt-3 text-xs leading-5 text-[#bad0c7]">The model is discovering nodes at runtime; the final graph is not loaded from a static tree.</p>
                  </div>
                </div>
              </Card>
            )}

            {mutation.error && (
              <Card className="rounded-3xl border-rose-200 bg-rose-50 p-6 text-rose-900">
                <div className="flex gap-3"><AlertTriangle className="mt-0.5 size-5 shrink-0" /><div><p className="font-semibold">The investigation did not complete</p><p className="mt-1 text-sm opacity-80">{mutation.error.message}</p></div></div>
              </Card>
            )}

            {!run && !mutation.isPending && (
              <Card className="grid min-h-[520px] place-items-center rounded-3xl border border-dashed border-[#cdd7d2] bg-white/55 p-10 text-center shadow-none">
                <div className="max-w-md">
                  <div className="mx-auto grid size-16 place-items-center rounded-3xl bg-[#e8eee9] text-[#365f50]"><GitBranch className="size-7" /></div>
                  <h3 className="mt-5 text-xl font-semibold tracking-[-0.025em]">No graph exists yet</h3>
                  <p className="mt-2 text-sm leading-6 text-[#6d7a74]">That is intentional. Press Run Ripple and Strands will discover the consequence graph from the move, person context, and general-purpose tools.</p>
                </div>
              </Card>
            )}

            {run && (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Card className="rounded-2xl border-[#dce2de] bg-white p-4 shadow-sm"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7b8781]">Discovered</p><p className="mt-1 text-2xl font-bold">{nodes.length - 1}</p></Card>
                  <Card className="rounded-2xl border-[#dce2de] bg-white p-4 shadow-sm"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7b8781]">Actions prepared</p><p className="mt-1 text-2xl font-bold text-amber-700">{statusCounts.ACTION_PREPARED ?? 0}</p></Card>
                  <Card className="rounded-2xl border-[#dce2de] bg-white p-4 shadow-sm"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7b8781]">Unknown</p><p className="mt-1 text-2xl font-bold text-rose-700">{statusCounts.UNKNOWN ?? 0}</p></Card>
                  <Card className="rounded-2xl border-[#dce2de] bg-white p-4 shadow-sm"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7b8781]">Max depth used</p><p className="mt-1 text-2xl font-bold">{Math.max(...nodes.map(node => node.depth))}</p></Card>
                </div>

                <div className="grid gap-5 2xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,.65fr)]">
                  <Card className="rounded-3xl border-[#dce2de] bg-[#fbfbf8] p-5 shadow-sm lg:p-6">
                    <div className="mb-5 flex items-start justify-between gap-4">
                      <div><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#d75d3e]">Runtime consequence graph</p><h3 className="mt-1 text-lg font-semibold">Cause → consequence → consequence</h3></div>
                      <Badge variant="outline" className="rounded-full border-[#dbe2de] bg-white text-[10px] text-[#5c6b64]">{run.run_id}</Badge>
                    </div>
                    {root && (
                      <button type="button" onClick={() => setSelectedId(root.id)} className={`mb-5 w-full rounded-2xl border p-4 text-left transition active:scale-[0.99] ${selectedId === root.id ? "border-[#ef6f4d] bg-[#fff8f5]" : "border-[#bfcac5] bg-[#183d32] text-white"}`}>
                        <div className="flex items-center gap-3"><MapPin className="size-5 text-[#ef7a58]" /><div><p className="font-mono text-[10px] uppercase tracking-[0.13em] opacity-70">Root event</p><p className="mt-1 font-semibold">{root.title}</p></div></div>
                      </button>
                    )}
                    <div className="grid gap-3 md:grid-cols-2">
                      {firstOrder.map(node => (
                        <GraphNode key={node.id} node={node} children={nodes.filter(item => item.parent_id === node.id)} selectedId={selectedId} onSelect={setSelectedId} />
                      ))}
                    </div>
                  </Card>

                  <Card className="rounded-3xl border-[#dce2de] bg-white shadow-sm">
                    {selected ? (
                      <ScrollArea className="h-[760px]">
                        <div className="p-6">
                          <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#7b8781]">Node inspection</p><h3 className="mt-2 text-xl font-semibold leading-7 tracking-[-0.025em]">{selected.title}</h3></div><StatusBadge status={selected.status} /></div>
                          <div className="mt-6 space-y-5">
                            <section><p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><GitBranch className="size-3.5" />Why was this investigated?</p><p className="rounded-xl bg-[#f5f7f5] p-3 text-sm leading-6 text-[#46564f]">{selected.why_investigated}</p></section>
                            <section>
                              <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><FileCheck2 className="size-3.5" />Prepared action</p>
                              <dl className="rounded-2xl border border-[#e1e6e3] bg-[#fafbf9] px-4">
                                <DetailRow label="What" value={selected.action?.what} />
                                <DetailRow label="Why" value={selected.action?.why} />
                                <DetailRow label="When" value={selected.action?.when} />
                                <DetailRow label="Where" value={selected.action?.where} />
                                <DetailRow label="Need" value={selected.action?.need?.join(" • ")} />
                                <DetailRow label="Depends on" value={selected.action?.depends_on} />
                              </dl>
                            </section>
                            <section>
                              <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><ShieldCheck className="size-3.5" />Applicability to Alex</p>
                              <p className="text-sm leading-6 text-[#364740]">{selected.applicability?.why_applies || selected.reason}</p>
                              {selected.applicability?.rule && <p className="mt-2 rounded-xl bg-[#f5f7f5] p-3 text-xs leading-5 text-[#68756f]"><span className="font-semibold">Rule:</span> {selected.applicability.rule}</p>}
                              {selected.applicability?.trigger_facts?.length > 0 && <p className="mt-2 font-mono text-[10px] leading-5 text-[#78837e]">Context facts: {selected.applicability.trigger_facts.join(" · ")}</p>}
                            </section>
                            <section><p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><BrainCircuit className="size-3.5" />Why this status?</p><p className="text-sm font-medium leading-6">{selected.reason}</p><p className="mt-2 border-l-2 border-[#e4a08c] pl-3 text-xs leading-5 text-[#68756f]"><span className="font-semibold">Ripple reasoning:</span> {selected.model_reasoning}</p></section>
                            <section>
                              <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><Database className="size-3.5" />Retrieved evidence</p>
                              <div className="space-y-3">
                                {selected.evidence.map(item => (
                                  <div key={item.source_id} className="rounded-2xl border border-[#e1e6e3] bg-[#fafbf9] p-4">
                                    <div className="flex items-start justify-between gap-2">
                                      <div>
                                        {item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-[#234d40] underline decoration-[#b8ccc3] underline-offset-4 hover:text-[#d45839]">{item.title}<ExternalLink className="size-3" /></a> : <p className="text-sm font-semibold">{item.title}</p>}
                                        <p className="mt-1 text-[10px] text-[#78837e]">{item.publisher}</p>
                                      </div>
                                      <Badge variant="outline" className={`shrink-0 rounded-full text-[9px] ${qualityStyles[item.source_type] ?? qualityStyles.UNVERIFIED}`}>{item.source_type.replaceAll("_", " ")}</Badge>
                                    </div>
                                    <p className="mt-3 whitespace-pre-line text-xs leading-5 text-[#52635b]">{item.excerpt}</p>
                                    {item.limitations && <p className="mt-3 border-l-2 border-[#e7b5a6] pl-3 text-[11px] leading-5 text-[#78837e]"><span className="font-semibold">Source limitation:</span> {item.limitations}</p>}
                                    <div className="mt-3 space-y-1 font-mono text-[9px] leading-4 text-[#8a948f]"><p>{item.source_id} · retrieved {item.retrieved_at}</p><p>Query: {item.query}</p><p>{item.retrieval_context}</p></div>
                                  </div>
                                ))}
                              </div>
                            </section>
                            <section><p className="mb-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]">Uncertainty</p>{selected.uncertainty?.length ? <ul className="space-y-2">{selected.uncertainty.map((item, index) => <li key={`${index}-${item.slice(0, 24)}`} className="text-xs leading-5 text-[#68756f]">• {item}</li>)}</ul> : <p className="text-xs text-[#78837e]">No unresolved uncertainty recorded.</p>}</section>
                            <section><p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-[#65736d]"><ArrowRight className="size-3.5" />Did it create another consequence?</p><p className="text-sm leading-6 text-[#46564f]">{selected.spawned_consequences.length ? `Yes — ${selected.spawned_consequences.length} child investigation${selected.spawned_consequences.length === 1 ? "" : "s"} spawned.` : "No material downstream consequence was added."}</p>{selected.caused_by_evidence_id && <p className="mt-2 font-mono text-[10px] leading-5 text-[#78837e]">This node was caused by parent evidence: {selected.caused_by_evidence_id}</p>}</section>
                          </div>
                        </div>
                      </ScrollArea>
                    ) : null}
                  </Card>
                </div>

                <Card className="rounded-3xl border-[#dce2de] bg-white p-6 shadow-sm">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#d75d3e]">Agent & tool activity</p><h3 className="mt-1 text-lg font-semibold">Investigation trace</h3></div><div className="flex items-center gap-2 text-xs text-[#66746d]"><Clock3 className="size-3.5" />Stopped: {String(run.safeguards.stop_reason).replaceAll("_", " ")}</div></div>
                  <div className="grid gap-x-6 gap-y-3 md:grid-cols-2">
                    {run.activity.map(event => <div key={event.sequence} className="flex gap-3 border-t border-[#edf0ee] pt-3"><span className="font-mono text-[10px] text-[#98a19d]">{String(event.sequence).padStart(2, "0")}</span><div><p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#5a6962]">{event.actor} · {event.kind.replaceAll("_", " ")}</p><p className="mt-1 text-xs leading-5 text-[#78837e]">{event.message}</p></div></div>)}
                  </div>
                </Card>
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
