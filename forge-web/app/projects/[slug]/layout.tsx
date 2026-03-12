"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/stores/projectStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { dispatchWsEvent, setLastEventTimestamp } from "@/stores/wsDispatcher";
import { DebugToggle } from "@/components/debug/DebugToggle";
import { ProjectSidebar } from "@/components/layout/ProjectSidebar";
import { Breadcrumb } from "@/components/layout/Breadcrumb";

import { CommandPalette } from "@/components/layout/CommandPalette";
import { useDebugPanelStore } from "@/stores/debugPanelStore";
import { useLeftPanel } from "@/components/layout/LeftPanelProvider";

type ConnectionState = "connected" | "stale" | "disconnected";

function useConnectionState(connected: boolean, lastEventTime: number | null): { state: ConnectionState; tick: number } {
  const [state, setState] = useState<ConnectionState>("disconnected");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!connected) {
      setState("disconnected");
      return;
    }

    // Check staleness + refresh timestamp display every 10s
    const check = () => {
      if (!connected) {
        setState("disconnected");
      } else if (lastEventTime && Date.now() - lastEventTime > 30_000) {
        setState("stale");
      } else {
        setState("connected");
      }
      setTick((t) => t + 1);
    };
    check();
    const interval = setInterval(check, 10_000);
    return () => clearInterval(interval);
  }, [connected, lastEventTime]);

  return { state, tick };
}

const CONNECTION_STYLES: Record<ConnectionState, { color: string; label: string }> = {
  connected: { color: "bg-green-500", label: "Connected" },
  stale: { color: "bg-yellow-500", label: "Connected (no recent events)" },
  disconnected: { color: "bg-red-500", label: "Disconnected" },
};

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const slug = params.slug as string;
  const { details, selectProject } = useProjectStore();
  const detail = details[slug];
  const { connected, onAny } = useWebSocket(slug);
  const incrementEvents = useDebugPanelStore((s) => s.incrementEvents);
  const [lastEventTime, setLastEventTime] = useState<number | null>(null);

  const { state: connectionState } = useConnectionState(connected, lastEventTime);
  const connStyle = CONNECTION_STYLES[connectionState];

  useEffect(() => {
    if (slug) selectProject(slug);
  }, [slug, selectProject]);

  // Register ProjectSidebar in the LeftPanel
  useLeftPanel(<ProjectSidebar slug={slug} />);

  // Forward all WebSocket events to per-entity stores + count events + track timestamps
  useEffect(() => {
    const unsub = onAny((event) => {
      dispatchWsEvent(event);
      incrementEvents();
      setLastEventTime(Date.now());
      if (event.timestamp) {
        setLastEventTimestamp(event.timestamp);
      }
    });
    return unsub;
  }, [onAny, incrementEvents]);

  return (
    <div className="flex flex-col h-full">
      {/* Command palette (Cmd+K / Ctrl+K) */}
      <CommandPalette />

      {/* Project header bar */}
      <div className="flex-shrink-0 px-6 pt-4 pb-2 border-b bg-white">
        <div className="flex items-center gap-2 text-sm">
          <Link href="/projects" className="text-gray-400 hover:text-gray-600">
            Projects
          </Link>
          <span className="text-gray-300">/</span>
          <span className="text-gray-700 font-medium">{slug}</span>
          {detail && (
            <span className="text-gray-400 ml-2 truncate hidden sm:inline">
              — {detail.goal}
            </span>
          )}
          <div className="ml-auto flex items-center gap-3">
            <DebugToggle slug={slug} />
            <div className="flex items-center gap-1.5" title={connStyle.label}>
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${connStyle.color}`}
              />
              {lastEventTime && connectionState === "connected" && (
                <span className="text-[10px] text-gray-400 hidden sm:inline">
                  {formatTimeAgo(lastEventTime)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <Breadcrumb />
        {children}
      </div>

      {/* Debug bottom panel is now in root layout */}
    </div>
  );
}

function formatTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}
