"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useProjectStore } from "@/stores/projectStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { dispatchWsEvent } from "@/stores/wsDispatcher";
import { DebugToggle } from "@/components/debug/DebugToggle";

interface NavItem {
  label: string;
  segment: string;
  /** If true, only show this tab when the route matches. */
  contextual?: boolean;
}

const entityNav: NavItem[] = [
  { label: "Overview", segment: "" },
  { label: "Tasks", segment: "tasks" },
  { label: "Board", segment: "board" },
  { label: "Decisions", segment: "decisions" },
  { label: "Objectives", segment: "objectives" },
  { label: "Ideas", segment: "ideas" },
  { label: "Knowledge", segment: "knowledge" },
  { label: "Guidelines", segment: "guidelines" },
  { label: "AC Templates", segment: "ac-templates" },
  { label: "Changes", segment: "changes" },
  { label: "Lessons", segment: "lessons" },
  { label: "Debug", segment: "debug" },
  { label: "Execution", segment: "execution", contextual: true },
];

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const slug = params.slug as string;
  const { details, selectProject } = useProjectStore();
  const detail = details[slug];
  const { connected, onAny } = useWebSocket(slug);
  useEffect(() => {
    if (slug) selectProject(slug);
  }, [slug, selectProject]);

  // Forward all WebSocket events to per-entity stores
  useEffect(() => {
    const unsub = onAny(dispatchWsEvent);
    return unsub;
  }, [onAny]);

  const basePath = `/projects/${slug}`;

  return (
    <div>
      {/* Project header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
          <Link href="/projects" className="hover:text-gray-600">Projects</Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">{slug}</span>
          <div className="ml-auto flex items-center gap-2">
            <DebugToggle slug={slug} />
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${
                connected ? "bg-green-500" : "bg-red-500"
              }`}
              title={connected ? "WebSocket connected" : "WebSocket disconnected"}
            />
          </div>
        </div>
        {detail && (
          <p className="text-sm text-gray-500">{detail.goal}</p>
        )}
      </div>

      {/* Entity navigation tabs */}
      <nav className="flex gap-1 border-b mb-6 overflow-x-auto">
        {entityNav.map((item) => {
          const href = item.segment ? `${basePath}/${item.segment}` : basePath;
          const isActive = item.segment
            ? pathname.startsWith(`${basePath}/${item.segment}`)
            : pathname === basePath;

          // Contextual tabs only appear when the route matches
          if (item.contextual && !isActive) return null;

          return (
            <Link
              key={item.segment}
              href={href}
              className={`px-3 py-2 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors ${
                isActive
                  ? "border-forge-600 text-forge-700 font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
