import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { ConsequenceGraph, ConsequenceStatus } from "@/components/ripple/ConsequenceGraph";
import { NodeInspector } from "@/components/ripple/NodeInspector";
import { trpc } from "@/lib/trpc";
import { isRuntimeGraph, summarizeGraph, type RippleRun } from "@/lib/ripple-view";
import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronDown,
  CircleDot,
  FileSearch,
  GitBranch,
  LoaderCircle,
  MapPin,
  Radar,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const investigationPhases = [
  { label: "Read the change", detail: "Grounding the event in Alex’s declared context." },
  { label: "Discover consequence domains", detail: "Reasoning outward without a preloaded checklist." },
  { label: "Retrieve public evidence", detail: "Querying the verified source catalog through tools." },
  { label: "Test applicability", detail: "Matching requirements to Alex-specific facts." },
  { label: "Follow second-order effects", detail: "Spawning only evidence-backed child investigations." },
  { label: "Know when to stop", detail: "Closing the graph when no material unresolved nodes remain." },
];

function BrandMark() {
  return (
    <div className="relative grid size-10 place-items-center rounded-xl bg-[#183d32] text-white shadow-[0_7px_18px_rgba(24,61,50,0.2)]">
      <GitBranch className="size-5" />
      <span className="absolute -right-1 -top-1 size-2.5 rounded-full border-2 border-[#f5f2eb] bg-[#ef6b49]" />
    </div>
  );
}

function InvestigationPanel({ phase }: { phase: number }) {
  return (
    <Card className="overflow-hidden rounded-[28px] border-[#183d32] bg-[#183d32] text-white shadow-[0_24px_65px_rgba(24,61,50,0.22)]">
      <div className="grid gap-8 p-6 lg:grid-cols-[1fr_1.2fr] lg:p-8">
        <div>
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-[#ff9b7e]">Live Strands investigation</p>
          <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Ripple is tracing what changed next.</h3>
          <p className="mt-3 max-w-md text-sm leading-6 text-[#bed0ca]">The graph stays empty until the model discovers consequences, retrieves evidence, tests applicability, and records guarded conclusions.</p>
        </div>
        <div className="space-y-1">
          {investigationPhases.map((item, index) => {
            const active = index === phase;
            const complete = index < phase;
            return (
              <div key={item.label} className={`flex gap-3 rounded-xl px-3 py-2.5 transition ${active ? "bg-white/10" : "bg-transparent"}`}>
                <div className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${complete ? "border-[#79ad99] bg-[#79ad99] text-[#183d32]" : active ? "border-[#ff9b7e] text-[#ff9b7e]" : "border-white/20 text-white/35"}`}>
                  {complete ? <Check className="size-3" /> : active ? <LoaderCircle className="size-3 animate-spin" /> : <CircleDot className="size-2.5" />}
                </div>
                <div>
                  <p className={`text-xs font-semibold ${active ? "text-white" : complete ? "text-[#c9dbd4]" : "text-white/45"}`}>{item.label}</p>
                  {active && <p className="mt-1 text-[11px] leading-5 text-[#afc7bd]">{item.detail}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

export default function Home() {
  const [moveDate, setMoveDate] = useState("2026-10-01");
  const [run, setRun] = useState<RippleRun | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState(0);
  const [traceOpen, setTraceOpen] = useState(false);

  const mutation = trpc.ripple.run.useMutation({
    onSuccess: data => {
      const typed = data as unknown as RippleRun;
      setRun(typed);
      const firstAction = typed.graph.nodes.find(node => node.status === "ACTION_PREPARED" && node.parent_id !== null);
      setSelectedId(firstAction?.id ?? typed.graph.nodes.find(node => node.parent_id !== null)?.id ?? typed.graph.root_id);
    },
  });

  useEffect(() => {
    if (!mutation.isPending) {
      setPhase(0);
      return;
    }
    const timer = window.setInterval(
      () => setPhase(value => Math.min(value + 1, investigationPhases.length - 1)),
      4500,
    );
    return () => window.clearInterval(timer);
  }, [mutation.isPending]);

  const nodes = run?.graph.nodes ?? [];
  const root = nodes.find(node => node.id === run?.graph.root_id) ?? null;
  const selected = nodes.find(node => node.id === selectedId) ?? root;
  const summary = useMemo(() => run ? summarizeGraph(run) : null, [run]);
  const generatedAt = run ? new Date(run.generated_at).toLocaleString() : null;

  const startRun = () => {
    mutation.reset();
    setRun(null);
    setSelectedId(null);
    setTraceOpen(false);
    mutation.mutate({ moveDate });
  };

  return (
    <div className="min-h-screen bg-[#f5f2eb] text-[#17251f]">
      <header className="border-b border-[#dbe1dd] bg-[#faf9f5]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3.5 lg:px-8">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-bold tracking-[-0.04em]">Ripple</h1>
                <Badge variant="outline" className="rounded-md border-[#cad6d0] bg-[#edf2ef] px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-[0.12em] text-[#496158]">Everyday Agents demo</Badge>
              </div>
              <p className="text-[11px] text-[#738079]">Consequence discovery for the change behind the task list</p>
            </div>
          </div>
          <div className="hidden items-center gap-5 lg:flex">
            <p className="max-w-xs text-right text-[11px] leading-5 text-[#718078]">One synthetic person. One move. Every conclusion tied to evidence or marked unknown.</p>
            <div className="h-8 w-px bg-[#d9dfdc]" />
            <div className="flex items-center gap-2 text-[11px] font-semibold text-[#2f5a4c]"><ShieldCheck className="size-4" />Evidence before action</div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-5 pb-14 pt-8 lg:px-8 lg:pt-11">
        <section className="grid items-end gap-8 lg:grid-cols-[minmax(0,1fr)_480px] lg:gap-12 xl:gap-16">
          <div className="max-w-3xl">
            <div className="mb-5 flex items-center gap-3">
              <span className="h-px w-10 bg-[#e36a49]" />
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-[#c95437]">A consequence-discovery agent</p>
            </div>
            <h2 className="text-[clamp(2.6rem,4.5vw,4rem)] font-semibold leading-[0.98] tracking-[-0.055em] text-[#15372d]">
              Something changed.<br /><span className="text-[#d85f40]">What else does that change?</span>
            </h2>
            <p className="mt-6 max-w-2xl text-base leading-7 text-[#617069] lg:text-lg lg:leading-8">
              Other agents help complete a known to-do list. Ripple discovers the important tasks, decisions, and uncertainties that were never on the list.
            </p>
          </div>

          <Card className="overflow-hidden rounded-[30px] border-[#ced8d3] bg-white shadow-[0_24px_70px_rgba(28,49,40,0.1)]">
            <div className="border-b border-[#e4e9e6] bg-[#f2f6f3] px-6 py-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-xl border border-[#cfddd6] bg-white text-[#315f50]"><UserRound className="size-5" /></div>
                  <div><p className="text-sm font-semibold">Alex Morgan</p><p className="text-[11px] text-[#78857f]">Synthetic scenario · single event</p></div>
                </div>
                <Badge variant="outline" className="rounded-md border-[#d5ddd9] bg-white font-mono text-[8px] uppercase tracking-[0.12em] text-[#65746d]">Not a checklist</Badge>
              </div>
            </div>
            <div className="p-6">
              <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#7d8983]">Triggering event</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-[-0.035em]">Moved from Indiana to Ohio</h3>
              <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-2xl border border-[#e0e5e2] bg-[#fafaf7] p-4">
                <div><p className="text-[10px] uppercase tracking-[0.08em] text-[#89938e]">From</p><p className="mt-1 text-sm font-semibold">Indianapolis, IN</p></div>
                <ArrowRight className="size-4 text-[#d85f40]" />
                <div className="text-right"><p className="text-[10px] uppercase tracking-[0.08em] text-[#89938e]">To</p><p className="mt-1 text-sm font-semibold">Columbus, OH</p></div>
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-[150px_1fr] sm:items-center">
                <label htmlFor="move-date" className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-[#74817a]">Effective move date</label>
                <Input id="move-date" type="date" value={moveDate} onChange={event => setMoveDate(event.target.value)} disabled={mutation.isPending} className="h-10 rounded-xl border-[#d4dcd8] bg-white" />
              </div>
              <Button
                size="lg"
                onClick={startRun}
                disabled={mutation.isPending || !moveDate}
                className="mt-5 h-13 w-full rounded-xl bg-[#e76343] text-sm font-semibold text-white shadow-[0_10px_24px_rgba(231,99,67,0.24)] hover:bg-[#d95839] active:scale-[0.98]"
              >
                {mutation.isPending ? <><LoaderCircle className="size-4 animate-spin" />Investigating ripples…</> : <><Radar className="size-4" />Discover Ripples</>}
              </Button>
              <p className="mt-3 text-center text-[10px] leading-4 text-[#89928e]">Live Strands reasoning · no predetermined consequence tree</p>
            </div>
          </Card>
        </section>

        <section className="mt-9">
          {mutation.isPending && <InvestigationPanel phase={phase} />}

          {mutation.error && (
            <Card className="rounded-[24px] border-[#e7c6bd] bg-[#fff3ef] p-5 text-[#7c3525] shadow-none">
              <div className="flex gap-3"><AlertTriangle className="mt-0.5 size-5 shrink-0" /><div><p className="text-sm font-semibold">The investigation did not complete</p><p className="mt-1 text-xs leading-5 opacity-80">{mutation.error.message}</p><p className="mt-2 text-[10px] leading-4 opacity-70">No partial or stale graph was accepted. Retry when the live model path is available.</p></div></div>
            </Card>
          )}

          {!run && !mutation.isPending && (
            <Card className="overflow-hidden rounded-[30px] border-[#ced8d3] bg-[#fbfbf8] shadow-[0_16px_48px_rgba(28,49,40,0.06)]">
              <div className="grid min-h-[430px] place-items-center px-6 py-12 text-center">
                <div className="max-w-2xl">
                  <div className="relative mx-auto size-28">
                    <span className="absolute left-1/2 top-1/2 size-24 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-[#a9bbb3]" />
                    <span className="absolute left-1/2 top-1/2 size-14 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#c8d5cf] bg-white" />
                    <span className="absolute left-1/2 top-1/2 grid size-10 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-xl bg-[#183d32] text-white"><GitBranch className="size-5" /></span>
                  </div>
                  <p className="mt-4 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#c95437]">Runtime consequence graph</p>
                  <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">The graph does not exist yet.</h3>
                  <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[#69766f]">Press Discover Ripples. Strands will reason from the move, call evidence tools, test Alex-specific applicability, and create only the branches it can justify.</p>
                  <div className="mx-auto mt-7 grid max-w-xl grid-cols-5 text-[9px] font-semibold uppercase tracking-[0.1em] text-[#7f8a85]">
                    {["Discover", "Retrieve", "Test", "Recurse", "Stop"].map((label, index) => <div key={label} className="relative"><span className="mx-auto mb-2 block size-2 rounded-full bg-[#728d82]" />{index < 4 && <span className="absolute left-[calc(50%+8px)] right-[calc(-50%+8px)] top-1 h-px bg-[#c6d2cd]" />}{label}</div>)}
                  </div>
                </div>
              </div>
            </Card>
          )}
        </section>

        {run && root && summary && (
          <section className="mt-9 space-y-5">
            <div className="flex flex-col justify-between gap-5 border-b border-[#d6ddd9] pb-5 lg:flex-row lg:items-end">
              <div>
                <div className="flex items-center gap-2"><Sparkles className="size-4 text-[#d85f40]" /><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#c95437]">Investigation complete</p></div>
                <h3 className="mt-2 text-3xl font-semibold tracking-[-0.045em]">What changed after the move</h3>
                <p className="mt-2 text-sm text-[#69766f]">Generated at runtime from {summary.officialSources} verified public sources · {generatedAt}</p>
              </div>
              <div className="grid grid-cols-3 divide-x divide-[#d5ddd9] rounded-2xl border border-[#d5ddd9] bg-white px-2 py-3 shadow-sm">
                <div className="px-4"><p className="text-xl font-semibold">{summary.discovered}</p><p className="font-mono text-[8px] uppercase tracking-[0.12em] text-[#7b8781]">Consequences</p></div>
                <div className="px-4"><p className="text-xl font-semibold text-[#b9492f]">{summary.actions}</p><p className="font-mono text-[8px] uppercase tracking-[0.12em] text-[#7b8781]">Actions</p></div>
                <div className="px-4"><p className="text-xl font-semibold text-[#9a6c1f]">{summary.unknown}</p><p className="font-mono text-[8px] uppercase tracking-[0.12em] text-[#7b8781]">Unknown</p></div>
              </div>
            </div>

            <div className="grid min-h-[820px] overflow-hidden rounded-[30px] border border-[#ced8d3] bg-white shadow-[0_20px_60px_rgba(28,49,40,0.08)] xl:grid-cols-[minmax(0,1.65fr)_minmax(390px,.75fr)]">
              <div className="min-w-0 border-b border-[#dce3df] bg-[#f7f6f1] xl:border-b-0 xl:border-r">
                <div className="flex flex-col gap-4 border-b border-[#dce3df] bg-[#fbfbf8] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#bd5136]">Consequence graph</p>
                    <p className="mt-1 text-sm font-semibold">Cause → consequence → downstream consequence</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {summary.recursive > 0 && <Badge variant="outline" className="rounded-md border-[#bed4cb] bg-[#eef6f2] text-[9px] text-[#315f50]"><GitBranch className="mr-1 size-3" />{summary.recursive} recursive</Badge>}
                    <Badge variant="outline" className={`rounded-md text-[9px] ${isRuntimeGraph(run) ? "border-[#bed4cb] bg-[#eef6f2] text-[#315f50]" : "border-[#e5cc96] bg-[#fff8e7] text-[#7b5a17]"}`}>
                      {isRuntimeGraph(run) ? "Runtime generated" : "Runtime proof unavailable"}
                    </Badge>
                    <span className="font-mono text-[8px] text-[#8a948f]">{run.run_id}</span>
                  </div>
                </div>
                <ScrollArea className="h-[760px] w-full">
                  <ConsequenceGraph root={root} nodes={nodes} selectedId={selectedId} onSelect={setSelectedId} />
                  <ScrollBar orientation="horizontal" />
                </ScrollArea>
              </div>
              <div className="min-w-0 bg-white">
                {selected && <NodeInspector node={selected} />}
              </div>
            </div>

            <Card className="overflow-hidden rounded-[26px] border-[#d4ddd8] bg-white shadow-sm">
              <button type="button" onClick={() => setTraceOpen(value => !value)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-[#f8faf8] active:bg-[#f2f5f3]">
                <div className="flex items-center gap-3">
                  <div className="grid size-9 place-items-center rounded-xl bg-[#edf3f0] text-[#315f50]"><FileSearch className="size-4" /></div>
                  <div><p className="text-sm font-semibold">Agent & tool trace</p><p className="text-[11px] text-[#7b8781]">{run.activity.length} events · stopped: {String(run.safeguards.stop_reason).replaceAll("_", " ")}</p></div>
                </div>
                <ChevronDown className={`size-4 text-[#74817a] transition ${traceOpen ? "rotate-180" : ""}`} />
              </button>
              {traceOpen && (
                <div className="grid gap-x-8 gap-y-3 border-t border-[#e4e9e6] px-5 pb-5 md:grid-cols-2">
                  {run.activity.map(event => <div key={event.sequence} className="flex gap-3 border-t border-[#edf0ee] pt-3 first:border-t-0"><span className="font-mono text-[9px] text-[#98a19d]">{String(event.sequence).padStart(2, "0")}</span><div><p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#52635b]">{event.actor} · {event.kind.replaceAll("_", " ")}</p><p className="mt-1 text-[11px] leading-5 text-[#78837e]">{event.message}</p></div></div>)}
                </div>
              )}
            </Card>

            <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-[#d7dfdb] bg-[#edf3f0] px-5 py-4 sm:flex-row sm:items-center">
              <div className="flex gap-3"><ShieldCheck className="mt-0.5 size-5 shrink-0 text-[#315f50]" /><div><p className="text-sm font-semibold">Ripple does not invent obligations when evidence is missing.</p><p className="mt-1 text-[11px] leading-5 text-[#66746d]">Weak evidence and missing Alex-specific facts end in UNKNOWN. Source evidence and Ripple reasoning remain visibly separate.</p></div></div>
              <Button variant="outline" onClick={startRun} disabled={mutation.isPending} className="rounded-xl border-[#aebeb7] bg-white text-xs"><RotateCcw className="size-3.5" />Run again</Button>
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-[#dbe1dd] bg-[#faf9f5]">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-2 px-5 py-5 text-[10px] leading-4 text-[#7b8781] sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <p>Prepared actions only. Ripple never submits filings, payments, insurance changes, or government actions.</p>
          <p className="font-mono uppercase tracking-[0.1em]">Checkpoint 3 · Part 1</p>
        </div>
      </footer>
    </div>
  );
}
