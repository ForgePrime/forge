"use client";

import { useState, useCallback } from "react";
import { gates as gatesApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";

interface GateResult {
  name: string;
  passed: boolean;
  output?: string;
  required: boolean;
  command?: string;
}

export interface GateRunnerState {
  ran: boolean;
  allRequiredPassed: boolean;
  results: GateResult[];
}

interface GateRunnerProps {
  slug: string;
  taskId: string;
  onChange?: (state: GateRunnerState) => void;
}

export function GateRunner({ slug, taskId, onChange }: GateRunnerProps) {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<GateResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedGate, setExpandedGate] = useState<string | null>(null);
  const [noGates, setNoGates] = useState(false);

  const allRequiredPassed = results
    ? results.every((r) => !r.required || r.passed)
    : false;
  const hasRun = results !== null;

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await gatesApi.check(slug, taskId);
      const gateResults: GateResult[] = (res.gates || []).map(
        (g: Record<string, unknown>) => ({
          name: g.name as string,
          passed: g.passed as boolean,
          output: g.output as string | undefined,
          required: (g.required as boolean) ?? true,
          command: g.command as string | undefined,
        })
      );

      if (gateResults.length === 0) {
        setNoGates(true);
        setResults([]);
        onChange?.({ ran: true, allRequiredPassed: true, results: [] });
      } else {
        setResults(gateResults);
        const allReqPassed = gateResults.every((r) => !r.required || r.passed);
        onChange?.({ ran: true, allRequiredPassed: allReqPassed, results: gateResults });
      }
    } catch (e) {
      const msg = (e as Error).message;
      // 404 usually means no gates configured
      if (msg.includes("404") || msg.includes("No gates")) {
        setNoGates(true);
        setResults([]);
        onChange?.({ ran: true, allRequiredPassed: true, results: [] });
      } else {
        setError(msg);
      }
    } finally {
      setRunning(false);
    }
  }, [slug, taskId, onChange]);

  // AI annotation
  useAIElement({
    id: "gate-runner",
    type: "section",
    label: "Gate Checks",
    description: hasRun
      ? `${results?.filter((r) => r.passed).length}/${results?.length} passed`
      : noGates
        ? "No gates configured"
        : "Not run yet",
    data: {
      ran: hasRun,
      running,
      noGates,
      allRequiredPassed,
      results: results?.map((r) => ({ name: r.name, passed: r.passed, required: r.required })),
    },
    actions: [
      {
        label: "Run gates",
        toolName: "runGates",
        toolParams: ["task_id*"],
        description: "Execute configured gate checks",
      },
    ],
  });

  if (noGates && !running) {
    return (
      <div className="rounded-lg border bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-400">No gates configured for this project.</p>
        <p className="text-xs text-gray-300 mt-1">Gate checks will be skipped.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Gate Checks</span>
          {hasRun && (
            <Badge variant={allRequiredPassed ? "success" : "danger"}>
              {allRequiredPassed ? "PASSED" : "FAILED"}
            </Badge>
          )}
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-3 py-1.5 text-xs text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
        >
          {running ? "Running..." : hasRun ? "Re-run Gates" : "Run Gates"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div className="divide-y">
          {results.map((gate) => {
            const isExpanded = expandedGate === gate.name;
            return (
              <div key={gate.name} className="px-4 py-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${gate.passed ? "text-green-600" : "text-red-600"}`}>
                      {gate.passed ? "\u2713" : "\u2717"}
                    </span>
                    <span className="text-sm text-gray-700">{gate.name}</span>
                    {!gate.required && (
                      <span className="text-[10px] text-gray-400">advisory</span>
                    )}
                    {!gate.passed && !gate.required && (
                      <Badge variant="warning">warning</Badge>
                    )}
                    {!gate.passed && gate.required && (
                      <Badge variant="danger">BLOCKING</Badge>
                    )}
                  </div>
                  {gate.output && (
                    <button
                      onClick={() => setExpandedGate(isExpanded ? null : gate.name)}
                      className="text-[10px] text-gray-400 hover:text-gray-600"
                    >
                      {isExpanded ? "Hide output" : "Show output"}
                    </button>
                  )}
                </div>
                {gate.command && (
                  <p className="text-[10px] font-mono text-gray-400 mt-0.5 ml-6">{gate.command}</p>
                )}
                {isExpanded && gate.output && (
                  <pre className="mt-2 text-xs font-mono bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre-wrap text-gray-600 max-h-60 overflow-y-auto">
                    {gate.output}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Not yet run hint */}
      {!hasRun && !running && !error && (
        <div className="px-4 py-4 text-center">
          <p className="text-xs text-gray-400">Click &quot;Run Gates&quot; to execute configured checks.</p>
        </div>
      )}
    </div>
  );
}
