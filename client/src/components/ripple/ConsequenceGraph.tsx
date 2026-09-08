import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { childrenOf, type ConsequenceNode } from "@/lib/ripple-view";
import {
  AlertCircle,
  Check,
  CircleSlash2,
  FileCheck2,
  GitBranch,
  Scale,
} from "lucide-react";

const statusPresentation: Record<
  string,
  { label: string; icon: typeof Check; accent: string; badge: string; surface: string }
> = {
  ACTION_PREPARED: {
    label: "Action prepared",
    icon: FileCheck2,
    accent: "bg-[#ec6544]",
    badge: "border-[#f4b9a8] bg-[#fff1ec] text-[#a43d25]",
    surface: "border-[#efb6a7]",
  },
  DOES_NOT_APPLY: {
    label: "Does not apply",
    icon: CircleSlash2,
    accent: "bg-[#9aa6a0]",
    badge: "border-[#d9dedb] bg-[#f2f4f3] text-[#52615a]",
    surface: "border-[#d8dedb]",
  },
  HUMAN_DECISION: {
    label: "Human decision",
    icon: Scale,
    accent: "bg-[#8167a9]",
    badge: "border-[#d8cde8] bg-[#f5f0fb] text-[#614882]",
    surface: "border-[#d5c9e5]",
  },
  UNKNOWN: {
    label: "Unknown",
    icon: AlertCircle,
    accent: "bg-[#d39b32]",
    badge: "border-[#ead6a8] bg-[#fff8e7] text-[#7b5a17]",
    surface: "border-[#e6d3a6]",
  },
  RESOLVED: {
    label: "Resolved",
    icon: Check,
    accent: "bg-[#347965]",
    badge: "border-[#bdd8ce] bg-[#ecf6f2] text-[#245c4c]",
    surface: "border-[#c9dcd5]",
  },
};

export function ConsequenceStatus({ status, compact = false }: { status: string; compact?: boolean }) {
  const style = statusPresentation[status] ?? statusPresentation.UNKNOWN;
  const Icon = style.icon;
  return (
    <Badge
      variant="outline"
      className={cn(
        "shrink-0 gap-1.5 rounded-md font-mono font-medium uppercase tracking-[0.08em]",
        compact ? "px-1.5 py-0.5 text-[8px]" : "px-2 py-1 text-[9px]",
        style.badge,
      )}
    >
      <Icon className={compact ? "size-2.5" : "size-3"} />
      {style.label}
    </Badge>
  );
}

function NodeCard({
  node,
  selectedId,
  onSelect,
  nested = false,
}: {
  node: ConsequenceNode;
  selectedId: string | null;
  onSelect: (id: string) => void;
  nested?: boolean;
}) {
  const style = statusPresentation[node.status] ?? statusPresentation.UNKNOWN;
  const selected = selectedId === node.id;

  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(node.id)}
      className={cn(
        "group relative w-full overflow-hidden rounded-2xl border bg-white text-left shadow-[0_8px_24px_rgba(29,48,40,0.07)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(29,48,40,0.12)] active:scale-[0.985]",
        nested ? "p-3.5" : "p-4",
        style.surface,
        selected && "ring-2 ring-[#193c32] ring-offset-2 ring-offset-[#f4f1ea]",
      )}
    >
      <span className={cn("absolute inset-y-0 left-0 w-1", style.accent)} />
      <div className="flex items-start justify-between gap-3 pl-1">
        <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-[#77837d]">
          {node.domain.replaceAll("_", " ")} · D{node.depth}
        </p>
        <ConsequenceStatus status={node.status} compact />
      </div>
      <h4 className={cn("pl-1 font-semibold leading-snug tracking-[-0.02em] text-[#172620]", nested ? "mt-2 text-[13px]" : "mt-3 text-sm")}>
        {node.title}
      </h4>
      {!nested && <p className="mt-2 line-clamp-2 pl-1 text-[11px] leading-5 text-[#69766f]">{node.reason}</p>}
      <div className="mt-3 flex items-center justify-between pl-1 text-[10px] text-[#87918c]">
        <span>{node.evidence.length} source{node.evidence.length === 1 ? "" : "s"}</span>
        <span className="font-semibold text-[#bd5136] opacity-0 transition group-hover:opacity-100">Inspect →</span>
      </div>
    </button>
  );
}

function Branch({
  node,
  nodes,
  selectedId,
  onSelect,
}: {
  node: ConsequenceNode;
  nodes: ConsequenceNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const children = childrenOf(nodes, node.id);

  return (
    <div className="relative min-w-0 pt-6">
      <span className="absolute left-1/2 top-0 h-6 w-px -translate-x-1/2 bg-[#9fb3aa]" />
      <NodeCard node={node} selectedId={selectedId} onSelect={onSelect} />
      {children.length > 0 && (
        <div className="relative ml-6 mt-3 space-y-3 border-l border-dashed border-[#9fb3aa] pl-4">
          <div className="absolute -left-px -top-3 h-3 border-l border-dashed border-[#9fb3aa]" />
          {children.map(child => (
            <div key={child.id} className="relative">
              <span className="absolute -left-4 top-7 h-px w-4 border-t border-dashed border-[#9fb3aa]" />
              <NodeCard node={child} selectedId={selectedId} onSelect={onSelect} nested />
              {childrenOf(nodes, child.id).length > 0 && (
                <div className="ml-4 mt-3 space-y-3 border-l border-dashed border-[#b7c5bf] pl-4">
                  {childrenOf(nodes, child.id).map(grandchild => (
                    <NodeCard key={grandchild.id} node={grandchild} selectedId={selectedId} onSelect={onSelect} nested />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ConsequenceGraph({
  root,
  nodes,
  selectedId,
  onSelect,
}: {
  root: ConsequenceNode;
  nodes: ConsequenceNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const branches = childrenOf(nodes, root.id);
  const graphWidth = Math.max(720, branches.length * 258);
  const connectorInset = branches.length > 0 ? `${50 / branches.length}%` : "50%";

  return (
    <div className="px-3 pb-5 pt-2" style={{ minWidth: graphWidth }}>
      <button
        type="button"
        onClick={() => onSelect(root.id)}
        aria-pressed={selectedId === root.id}
        className={cn(
          "mx-auto flex w-[310px] items-center gap-3 rounded-2xl border border-[#183d32] bg-[#183d32] p-4 text-left text-white shadow-[0_12px_30px_rgba(24,61,50,0.22)] transition active:scale-[0.985]",
          selectedId === root.id && "ring-2 ring-[#ef7454] ring-offset-2 ring-offset-[#f4f1ea]",
        )}
      >
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/10 text-[#ff9a7c]"><GitBranch className="size-5" /></span>
        <span>
          <span className="block font-mono text-[9px] uppercase tracking-[0.16em] text-[#a9c6bb]">Triggering event</span>
          <span className="mt-1 block text-sm font-semibold">Moved from Indiana to Ohio</span>
        </span>
      </button>

      <div className="mx-auto h-8 w-px bg-[#718f83]" />
      <div className="relative">
        {branches.length > 1 && <span className="absolute top-0 h-px bg-[#9fb3aa]" style={{ left: connectorInset, right: connectorInset }} />}
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.max(branches.length, 1)}, minmax(240px, 1fr))` }}>
          {branches.map(node => (
            <Branch key={node.id} node={node} nodes={nodes} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </div>
      </div>
    </div>
  );
}
