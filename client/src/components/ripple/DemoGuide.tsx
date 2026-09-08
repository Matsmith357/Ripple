import { Button } from "@/components/ui/button";
import type { WalkthroughStep } from "@/lib/ripple-view";
import { ArrowLeft, ArrowRight, Clapperboard } from "lucide-react";
import { ConsequenceStatus } from "./ConsequenceGraph";

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function DemoGuide({
  steps,
  activeId,
  onSelect,
}: {
  steps: WalkthroughStep[];
  activeId: string;
  onSelect: (step: WalkthroughStep) => void;
}) {
  const activeIndex = Math.max(0, steps.findIndex(step => step.id === activeId));
  const active = steps[activeIndex] ?? steps[0];
  const targetSeconds = steps.reduce((sum, step) => sum + step.targetSeconds, 0);
  if (!active) return null;

  return (
    <section aria-label="Judge walkthrough" className="overflow-hidden rounded-[24px] border border-[#cdd9d3] bg-[#183d32] text-white shadow-[0_16px_40px_rgba(24,61,50,0.16)]">
      <div className="grid gap-5 px-5 py-5 lg:grid-cols-[230px_minmax(0,1fr)_auto] lg:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2 text-[#ff9b7e]"><Clapperboard className="size-4" /><p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em]">Judge walkthrough</p></div>
          <p className="mt-2 text-sm font-semibold">Runtime-derived demo path</p>
          <p className="mt-1 text-[10px] leading-4 text-[#a9c2b8]">Target {formatDuration(targetSeconds)} · no static node names</p>
        </div>

        <div className="min-w-0">
          <div className="flex gap-1.5 overflow-x-auto pb-2">
            {steps.map((step, index) => (
              <button
                key={step.id}
                type="button"
                onClick={() => onSelect(step)}
                aria-pressed={step.id === active.id}
                className={`grid size-7 shrink-0 place-items-center rounded-full border font-mono text-[9px] font-semibold transition active:scale-95 ${step.id === active.id ? "border-[#ff9b7e] bg-[#ff9b7e] text-[#183d32]" : index < activeIndex ? "border-[#7fac9a] bg-[#315f50] text-white" : "border-white/20 text-white/55 hover:border-white/45"}`}
              >
                {index + 1}
              </button>
            ))}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-[#9cb9ae]">{active.label}</p>
            {active.id !== "event" && active.id !== "graph" && active.id !== "complete" && <ConsequenceStatus status={active.status} compact />}
          </div>
          <p className="mt-1 text-sm font-semibold">{active.title}</p>
          <p className="mt-1 text-[11px] leading-5 text-[#b9cec5]">{active.note}</p>
        </div>

        <div className="flex items-center gap-2 lg:justify-end">
          <Button
            type="button"
            variant="outline"
            size="icon"
            disabled={activeIndex === 0}
            onClick={() => onSelect(steps[activeIndex - 1])}
            className="size-9 rounded-xl border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white disabled:opacity-30"
            aria-label="Previous walkthrough step"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <Button
            type="button"
            disabled={activeIndex === steps.length - 1}
            onClick={() => onSelect(steps[activeIndex + 1])}
            className="h-9 rounded-xl bg-[#ef6b49] px-4 text-xs font-semibold text-white hover:bg-[#dc5939] disabled:bg-white/10 disabled:text-white/35"
          >
            {activeIndex === steps.length - 1 ? "Walkthrough complete" : "Next"}
            {activeIndex < steps.length - 1 && <ArrowRight className="size-3.5" />}
          </Button>
        </div>
      </div>
    </section>
  );
}
