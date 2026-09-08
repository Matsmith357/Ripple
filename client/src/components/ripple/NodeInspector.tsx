import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { deadlineEvidence, isVerifiedPublicEvidence, type ConsequenceNode } from "@/lib/ripple-view";
import {
  AlertCircle,
  ArrowUpRight,
  BrainCircuit,
  CalendarClock,
  CheckCircle2,
  FileText,
  GitBranch,
  Link2,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { ConsequenceStatus } from "./ConsequenceGraph";

const qualityLabel: Record<string, string> = {
  PRIMARY_OFFICIAL: "Primary official",
  AUTHORITATIVE_SECONDARY: "Authoritative secondary",
  UNVERIFIED: "Unverified",
  EVIDENCE_GAP: "Evidence gap",
  SYNTHETIC_SCENARIO: "Scenario input",
};

const qualityStyle: Record<string, string> = {
  PRIMARY_OFFICIAL: "border-[#b9d9cd] bg-[#edf7f3] text-[#245c4c]",
  AUTHORITATIVE_SECONDARY: "border-[#bcd7e4] bg-[#eef7fb] text-[#285b72]",
  UNVERIFIED: "border-[#e7c99a] bg-[#fff7e8] text-[#79571e]",
  EVIDENCE_GAP: "border-[#e8c79a] bg-[#fff7e8] text-[#79571e]",
  SYNTHETIC_SCENARIO: "border-[#d8dedb] bg-[#f1f3f2] text-[#59665f]",
};

function Fact({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="border-t border-[#e8ece9] py-3 first:border-t-0">
      <dt className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-[#85908a]">{label}</dt>
      <dd className="mt-1 text-[13px] leading-5 text-[#2e4139]">{value?.trim() || "UNKNOWN"}</dd>
    </div>
  );
}

export function NodeInspector({ node }: { node: ConsequenceNode }) {
  const deadlineSource = deadlineEvidence(node);
  const verifiedCount = node.evidence.filter(isVerifiedPublicEvidence).length;
  const isUnknown = node.status === "UNKNOWN";

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="border-b border-[#e2e7e4] px-5 py-5 lg:px-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#75827b]">Selected consequence · depth {node.depth}</p>
            <h3 className="mt-2 text-xl font-semibold leading-7 tracking-[-0.03em] text-[#172620]">{node.title}</h3>
          </div>
          <ConsequenceStatus status={node.status} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-[#6c7972]">
          <span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-3.5 text-[#347965]" />{verifiedCount} verified source{verifiedCount === 1 ? "" : "s"}</span>
          <span className="inline-flex items-center gap-1.5"><GitBranch className="size-3.5 text-[#bd5136]" />{node.spawned_consequences.length} child investigation{node.spawned_consequences.length === 1 ? "" : "s"}</span>
        </div>
      </div>

      <ScrollArea className="h-[740px] min-h-0">
        <div className="space-y-6 p-5 lg:p-6">
          {isUnknown && (
            <section className="rounded-2xl border border-[#e5cc96] bg-[#fff9ea] p-4">
              <div className="flex gap-3">
                <AlertCircle className="mt-0.5 size-5 shrink-0 text-[#a97820]" />
                <div>
                  <p className="text-sm font-semibold text-[#5f471a]">Ripple stopped rather than guessed</p>
                  <p className="mt-1 text-xs leading-5 text-[#7a653b]">The available evidence or Alex-specific facts do not support a confident obligation. UNKNOWN is a trust outcome, not a failed investigation.</p>
                </div>
              </div>
            </section>
          )}

          <section>
            <p className="mb-2 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#bd5136]">What changed</p>
            <p className="text-sm leading-6 text-[#405149]">{node.why_investigated}</p>
          </section>

          <section className="overflow-hidden rounded-2xl border border-[#dce3df] bg-[#f8faf8]">
            <div className="border-b border-[#dce3df] bg-[#183d32] px-4 py-3 text-white">
              <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-[#ff9a7c]" /><p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#b8d0c7]">Prepared action</p></div>
              <p className="mt-2 text-base font-semibold leading-6">{node.action?.what || "No action prepared"}</p>
            </div>
            <dl className="px-4">
              <Fact label="Why" value={node.action?.why || node.reason} />
              <Fact label="When" value={node.action?.when} />
              <Fact label="Where" value={node.action?.where} />
              <Fact label="Need" value={node.action?.need?.join(" · ")} />
              <Fact label="Depends on" value={node.action?.depends_on} />
            </dl>
            {deadlineSource && (
              <div className="mx-4 mb-4 flex gap-2 border-t border-[#e3e8e5] pt-3 text-[10px] leading-4 text-[#728078]">
                <CalendarClock className="mt-0.5 size-3.5 shrink-0" />
                <span>Deadline traced to {deadlineSource.publisher} · {deadlineSource.source_id}</span>
              </div>
            )}
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#347965]">Source evidence</p>
                <p className="mt-1 text-xs text-[#76827c]">Retrieved facts, kept separate from model reasoning</p>
              </div>
              <FileText className="size-4 text-[#347965]" />
            </div>
            <div className="space-y-3">
              {node.evidence.map(item => (
                <article key={item.source_id} className="rounded-2xl border border-[#dce3df] p-4 shadow-[0_5px_18px_rgba(29,48,40,0.04)]">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      {item.source_url ? (
                        <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1.5 text-sm font-semibold leading-5 text-[#1e4b3d] underline decoration-[#b5cbc2] underline-offset-4 transition hover:text-[#bd5136]">
                          {item.title}<ArrowUpRight className="mt-0.5 size-3.5 shrink-0" />
                        </a>
                      ) : <p className="text-sm font-semibold leading-5">{item.title}</p>}
                      <p className="mt-1 text-[10px] leading-4 text-[#7d8882]">{item.publisher}</p>
                    </div>
                    <Badge variant="outline" className={`shrink-0 rounded-md px-1.5 py-0.5 text-[8px] uppercase tracking-[0.08em] ${qualityStyle[item.source_type] ?? qualityStyle.UNVERIFIED}`}>
                      {qualityLabel[item.source_type] ?? item.source_type}
                    </Badge>
                  </div>
                  <blockquote className="mt-3 border-l-2 border-[#8eb5a6] pl-3 text-[11px] leading-5 text-[#53635c]">{item.excerpt}</blockquote>
                  {item.limitations && <p className="mt-3 text-[10px] leading-4 text-[#7f8984]"><span className="font-semibold">Source limitation:</span> {item.limitations}</p>}
                  <div className="mt-3 border-t border-[#edf0ee] pt-2 font-mono text-[8px] leading-4 text-[#8c9590]">
                    <p>{item.source_id} · retrieved {item.retrieved_at}</p>
                    <p className="mt-1">Query: {item.query}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-[#d8e0dc] bg-[#f2f6f4] p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#315f50]">Ripple reasoning</p>
              <BrainCircuit className="size-4 text-[#315f50]" />
            </div>
            <p className="mt-3 text-xs leading-5 text-[#465850]">{node.model_reasoning}</p>
            <div className="mt-4 border-t border-[#dce5e1] pt-3">
              <p className="font-mono text-[8px] font-semibold uppercase tracking-[0.14em] text-[#84908a]">Why this status</p>
              <p className="mt-1 text-xs font-medium leading-5 text-[#31463d]">{node.reason}</p>
            </div>
          </section>

          <section>
            <p className="mb-2 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#68766f]">Why it applies to Alex</p>
            <p className="text-sm leading-6 text-[#405149]">{node.applicability?.why_applies || node.reason}</p>
            {node.applicability?.rule && <p className="mt-3 border-l-2 border-[#c5d4ce] pl-3 text-xs leading-5 text-[#69766f]">{node.applicability.rule}</p>}
            {node.applicability?.trigger_facts?.length > 0 && <p className="mt-3 font-mono text-[9px] leading-4 text-[#89938e]">Context used: {node.applicability.trigger_facts.join(" · ")}</p>}
          </section>

          <section>
            <p className="mb-2 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#68766f]">Uncertainty</p>
            {node.uncertainty?.length ? (
              <div className="space-y-2">
                {node.uncertainty.map((item, index) => <p key={`${index}-${item.slice(0, 24)}`} className="flex gap-2 text-xs leading-5 text-[#66746d]"><AlertCircle className="mt-0.5 size-3.5 shrink-0 text-[#b18027]" />{item}</p>)}
              </div>
            ) : <p className="text-xs text-[#7d8882]">No unresolved uncertainty recorded.</p>}
          </section>

          <section className="rounded-xl border border-[#e2e7e4] px-4 py-3 text-xs leading-5 text-[#66746d]">
            <p className="flex items-center gap-2 font-semibold text-[#33483f]"><Link2 className="size-3.5" />Recursion provenance</p>
            <p className="mt-1">{node.spawned_consequences.length ? `This consequence produced ${node.spawned_consequences.length} downstream investigation${node.spawned_consequences.length === 1 ? "" : "s"}.` : "No material downstream consequence was added."}</p>
            {node.caused_by_evidence_id && <p className="mt-1 font-mono text-[9px]">Created from parent source {node.caused_by_evidence_id}</p>}
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
