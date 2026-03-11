"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  projects as projectsApi,
  gates as gatesApi,
  guidelines as guidelinesApi,
  health as healthApi,
} from "@/lib/api";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { Badge } from "@/components/shared/Badge";
import type { ProjectDetail, Gate, Guideline } from "@/lib/types";

export default function SettingsPage() {
  const { slug } = useParams() as { slug: string };

  return (
    <div className="space-y-8 max-w-3xl">
      <h2 className="text-lg font-semibold">Settings</h2>
      <ProjectConfigSection slug={slug} />
      <GatesSection slug={slug} />
      <GuidelineScopesSection slug={slug} />
      <ConnectionInfoSection slug={slug} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Project Config
// ---------------------------------------------------------------------------

function ProjectConfigSection({ slug }: { slug: string }) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [goal, setGoal] = useState("");
  const [testCmd, setTestCmd] = useState("");
  const [lintCmd, setLintCmd] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    projectsApi.get(slug).then((p) => {
      setProject(p);
      setGoal(p.goal);
      setTestCmd((p.config?.test_cmd as string) ?? "");
      setLintCmd((p.config?.lint_cmd as string) ?? "");
    }).catch((e) => setError((e as Error).message));
  }, [slug]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const config = { ...project?.config, test_cmd: testCmd || undefined, lint_cmd: lintCmd || undefined };
      const updated = await projectsApi.update(slug, { goal, config });
      setProject(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (!project && !error) {
    return <p className="text-sm text-gray-400">Loading project config...</p>;
  }

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Project Configuration</h3>
      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Goal</label>
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="w-full text-sm border rounded-md px-3 py-1.5"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Test Command</label>
          <input
            type="text"
            value={testCmd}
            onChange={(e) => setTestCmd(e.target.value)}
            placeholder="e.g. npm test"
            className="w-full text-sm border rounded-md px-3 py-1.5 font-mono"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Lint Command</label>
          <input
            type="text"
            value={lintCmd}
            onChange={(e) => setLintCmd(e.target.value)}
            placeholder="e.g. npm run lint"
            className="w-full text-sm border rounded-md px-3 py-1.5 font-mono"
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          {saved && <span className="text-xs text-green-600">Saved</span>}
        </div>
      </div>

      {project && (
        <div className="mt-3 pt-3 border-t text-[10px] text-gray-400 flex gap-4">
          <span>Created: {new Date(project.created).toLocaleDateString()}</span>
          <span>Updated: {new Date(project.updated).toLocaleDateString()}</span>
          <span>Tasks: {project.task_count}</span>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Gates
// ---------------------------------------------------------------------------

function GatesSection({ slug }: { slug: string }) {
  const [gatesList, setGatesList] = useState<Gate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New gate form
  const [newName, setNewName] = useState("");
  const [newCommand, setNewCommand] = useState("");
  const [newRequired, setNewRequired] = useState(true);
  const [adding, setAdding] = useState(false);

  // Gate check
  const [checkResult, setCheckResult] = useState<Array<Record<string, unknown>> | null>(null);
  const [checking, setChecking] = useState(false);

  const fetchGates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await gatesApi.list(slug);
      setGatesList(res.gates);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    fetchGates();
  }, [fetchGates]);

  const handleAddGate = async () => {
    if (!newName.trim() || !newCommand.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await gatesApi.create(slug, [{ name: newName.trim(), command: newCommand.trim(), required: newRequired }]);
      setNewName("");
      setNewCommand("");
      setNewRequired(true);
      fetchGates();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  const handleRunGates = async () => {
    setChecking(true);
    setCheckResult(null);
    setError(null);
    try {
      const res = await gatesApi.check(slug);
      setCheckResult(res.gates);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <section className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Gates ({gatesList.length})</h3>
        <button
          onClick={handleRunGates}
          disabled={checking || gatesList.length === 0}
          className="px-3 py-1 text-xs text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
        >
          {checking ? "Running..." : "Run Gates"}
        </button>
      </div>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
      {loading && <p className="text-xs text-gray-400">Loading gates...</p>}

      {/* Existing gates */}
      <div className="space-y-2 mb-3">
        {gatesList.map((gate) => (
          <div key={gate.name} className="flex items-center gap-2 bg-gray-50 rounded-md px-3 py-2">
            <Badge variant={gate.required ? "danger" : "default"}>
              {gate.required ? "required" : "optional"}
            </Badge>
            <span className="text-sm font-medium text-gray-700">{gate.name}</span>
            <code className="text-[10px] text-gray-500 ml-auto font-mono truncate max-w-[200px]">
              {gate.command}
            </code>
          </div>
        ))}
        {!loading && gatesList.length === 0 && (
          <p className="text-xs text-gray-400">No gates configured</p>
        )}
      </div>

      {/* Add gate form */}
      <div className="border-t pt-3">
        <p className="text-xs text-gray-500 mb-2">Add Gate</p>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full text-xs border rounded px-2 py-1"
            />
          </div>
          <div className="flex-[2]">
            <input
              type="text"
              placeholder="Command"
              value={newCommand}
              onChange={(e) => setNewCommand(e.target.value)}
              className="w-full text-xs border rounded px-2 py-1 font-mono"
            />
          </div>
          <label className="flex items-center gap-1 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={newRequired}
              onChange={(e) => setNewRequired(e.target.checked)}
            />
            Required
          </label>
          <button
            onClick={handleAddGate}
            disabled={adding || !newName.trim() || !newCommand.trim()}
            className="px-2 py-1 text-xs text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
          >
            {adding ? "..." : "Add"}
          </button>
        </div>
      </div>

      {/* Check results */}
      {checkResult && (
        <div className="mt-3 border-t pt-3">
          <p className="text-xs font-medium text-gray-600 mb-2">Gate Check Results</p>
          <div className="space-y-1">
            {checkResult.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className={`font-medium ${r.passed ? "text-green-600" : "text-red-600"}`}>
                  {r.passed ? "PASS" : "FAIL"}
                </span>
                <span className="text-gray-700">{String(r.name)}</span>
                {r.output != null && (
                  <span className="text-[10px] text-gray-400 truncate max-w-[300px]">{String(r.output)}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Guideline Scopes
// ---------------------------------------------------------------------------

function GuidelineScopesSection({ slug }: { slug: string }) {
  const [guidelines, setGuidelines] = useState<Guideline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    guidelinesApi.list(slug).then((res) => {
      setGuidelines(res.guidelines);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [slug]);

  // Count scopes
  const scopeCounts: Record<string, number> = {};
  for (const g of guidelines) {
    const scope = g.scope ?? "general";
    scopeCounts[scope] = (scopeCounts[scope] ?? 0) + 1;
  }
  const sortedScopes = Object.entries(scopeCounts).sort((a, b) => b[1] - a[1]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Guideline Scopes ({sortedScopes.length})
      </h3>

      {loading && <p className="text-xs text-gray-400">Loading...</p>}

      <div className="flex flex-wrap gap-2">
        {sortedScopes.map(([scope, count]) => (
          <div
            key={scope}
            className="flex items-center gap-1.5 bg-gray-50 rounded-md px-3 py-1.5"
          >
            <span className="text-sm text-gray-700">{scope}</span>
            <span className="text-[10px] text-gray-400 bg-gray-200 rounded-full px-1.5 py-0.5 tabular-nums">
              {count}
            </span>
          </div>
        ))}
        {!loading && sortedScopes.length === 0 && (
          <p className="text-xs text-gray-400">No guidelines defined</p>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Connection Info
// ---------------------------------------------------------------------------

function ConnectionInfoSection({ slug }: { slug: string }) {
  const { connected } = useWebSocket(slug);
  const [apiHealth, setApiHealth] = useState<{ status: string; version: string } | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    healthApi()
      .then(setApiHealth)
      .catch((e) => setHealthError((e as Error).message));
  }, []);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Connection Info</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <span className="text-xs text-gray-500 block mb-1">API Health</span>
          {healthError ? (
            <span className="text-xs text-red-600">{healthError}</span>
          ) : apiHealth ? (
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${apiHealth.status === "ok" ? "bg-green-500" : "bg-red-500"}`} />
              <span className="text-sm text-gray-700">{apiHealth.status}</span>
              <span className="text-[10px] text-gray-400">v{apiHealth.version}</span>
            </div>
          ) : (
            <span className="text-xs text-gray-400">Checking...</span>
          )}
        </div>

        <div>
          <span className="text-xs text-gray-500 block mb-1">WebSocket</span>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-sm text-gray-700">{connected ? "Connected" : "Disconnected"}</span>
          </div>
        </div>

        <div>
          <span className="text-xs text-gray-500 block mb-1">API Base</span>
          <code className="text-xs text-gray-700 font-mono">
            {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}
          </code>
        </div>

        <div>
          <span className="text-xs text-gray-500 block mb-1">Project</span>
          <span className="text-sm text-gray-700">{slug}</span>
        </div>
      </div>
    </section>
  );
}
