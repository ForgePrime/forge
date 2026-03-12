"use client";

import { useState, useCallback, useEffect } from "react";
import useSWR from "swr";
import { llm, skills as skillsApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { useToastStore } from "@/stores/toastStore";
import { useDebugPanelStore } from "@/stores/debugPanelStore";
import type {
  LLMConfig,
  LLMProvider,
  LLMProviderTestResult,
  LLMFeatureFlags,
  LLMModulePermission,
} from "@/lib/types";
import {
  CAPABILITY_CONTRACTS,
  getPermissionStatus,
  type CapabilityDef,
  type CapabilityContract,
} from "@/lib/capabilities";

const MODULE_LABELS: Record<string, string> = {
  skills: "Skills",
  objectives: "Objectives",
  ideas: "Ideas",
  tasks: "Tasks",
  knowledge: "Knowledge",
  guidelines: "Guidelines",
  decisions: "Decisions",
  lessons: "Lessons",
  ac_templates: "AC Templates",
  projects: "Projects",
  changes: "Changes",
  research: "Research",
};

const MODULE_DESCRIPTIONS: Record<string, string> = {
  skills: "AI assistance for creating and editing skills",
  objectives: "AI suggestions for objectives and key results",
  ideas: "AI exploration and analysis of ideas",
  tasks: "AI help with task planning and execution",
  knowledge: "AI-powered knowledge management",
  guidelines: "AI suggestions for coding guidelines",
  decisions: "AI-assisted decision analysis",
  lessons: "AI extraction of lessons learned",
  ac_templates: "AI generation of acceptance criteria",
  projects: "AI assistance at project level",
  changes: "AI recording of file changes for audit trail",
  research: "AI access to research objects and findings",
};

export default function LLMSettingsPage() {
  return (
    <div className="space-y-8 max-w-4xl p-6">
      <div>
        <h2 className="text-lg font-semibold">LLM Settings</h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure AI providers, feature flags, and module permissions.
        </p>
      </div>
      <ProvidersSection />
      <SkillsGitSyncSection />
      <FeatureFlagsSection />
      <PermissionsSection />
      <CapabilitiesSection />
      <LimitsSection />
      <DebugConsoleSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

function ProvidersSection() {
  const { data, error, isLoading } = useSWR<{ providers: LLMProvider[] }>(
    "/llm/providers",
  );
  const { data: config } = useSWR<LLMConfig>("/llm/config");
  const { addToast } = useToastStore();
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<LLMProviderTestResult | null>(null);

  const handleTest = useCallback(async (providerName: string) => {
    setTesting(providerName);
    setTestResult(null);
    try {
      const result = await llm.testProvider(providerName);
      setTestResult(result);
      addToast({
        message: result.status === "ok"
          ? `${providerName}: connected (${result.latency_ms}ms)`
          : `${providerName}: ${result.error ?? "failed"}`,
        action: result.status === "ok" ? "info" : "failed",
      });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setTesting(null);
    }
  }, [addToast]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Providers</h3>

      {isLoading && <p className="text-xs text-gray-400">Loading providers...</p>}
      {error && <p className="text-xs text-red-600">Failed to load providers</p>}

      {data && data.providers.length === 0 && (
        <p className="text-xs text-gray-400">
          No providers configured. Set <code className="bg-gray-100 px-1 rounded">ANTHROPIC_API_KEY</code> or{" "}
          <code className="bg-gray-100 px-1 rounded">OPENAI_API_KEY</code> environment variable on the API server.
        </p>
      )}

      <div className="space-y-2">
        {data?.providers.map((p) => {
          const isDefault = config?.default_provider === p.name;
          return (
            <div
              key={p.name}
              className="flex items-center gap-3 bg-gray-50 rounded-md px-4 py-3"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">{p.name}</span>
                  <span className="text-[10px] text-gray-400">{p.provider_type}</span>
                  {isDefault && <Badge variant="success">default</Badge>}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  Model: <code className="text-[10px]">{p.default_model}</code>
                </p>
              </div>
              <Badge variant={p.status === "ready" ? "success" : "warning"}>
                {p.status}
              </Badge>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleTest(p.name)}
                disabled={testing === p.name}
              >
                {testing === p.name ? "Testing..." : "Test"}
              </Button>
            </div>
          );
        })}
      </div>

      {testResult && (
        <div className={`mt-3 p-3 rounded-md text-xs ${
          testResult.status === "ok"
            ? "bg-green-50 border border-green-200 text-green-700"
            : "bg-red-50 border border-red-200 text-red-700"
        }`}>
          <div className="flex items-center gap-2">
            <span className="font-medium">{testResult.provider}</span>
            <span>{testResult.status === "ok" ? "Connected" : "Failed"}</span>
          </div>
          {testResult.model && <p className="mt-1">Model: {testResult.model}</p>}
          {testResult.latency_ms != null && <p>Latency: {testResult.latency_ms}ms</p>}
          {testResult.error && <p className="mt-1">{testResult.error}</p>}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Skills Git Sync
// ---------------------------------------------------------------------------

function SkillsGitSyncSection() {
  const { addToast } = useToastStore();
  const [repoUrl, setRepoUrl] = useState("");
  const [configuredVia, setConfiguredVia] = useState("");
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    skillsApi.getConfig().then((config) => {
      setRepoUrl(config.repo_url ?? "");
      setConfiguredVia(config.configured_via ?? "none");
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await skillsApi.updateConfig({ repo_url: repoUrl });
      setConfiguredVia(repoUrl ? "persisted" : "none");
      addToast({ message: "Skills repo URL saved", action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [repoUrl, addToast]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Skills Git Sync</h3>
      <p className="text-xs text-gray-500 mb-3">
        Configure the git repository URL for syncing skills. Can also be set via{" "}
        <code className="bg-gray-100 px-1 rounded text-[10px]">FORGE_SKILLS_REPO_URL</code> env var.
      </p>

      {!loaded ? (
        <p className="text-xs text-gray-400">Loading...</p>
      ) : (
        <div className="space-y-3 max-w-lg">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Repository URL</label>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/org/forge-skills.git"
              className="w-full text-sm border rounded-md px-3 py-1.5 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
          </div>
          <div className="flex items-center gap-3">
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
            {configuredVia !== "none" && (
              <span className="text-[10px] text-gray-400">
                Configured via: {configuredVia}
              </span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Feature Flags
// ---------------------------------------------------------------------------

function FeatureFlagsSection() {
  const { data: config, error: fetchError, mutate } = useSWR<LLMConfig>("/llm/config");
  const { addToast } = useToastStore();
  const [saving, setSaving] = useState(false);

  const flags = config?.feature_flags;

  const handleToggle = useCallback(async (module: string, enabled: boolean) => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await llm.updateConfig({
        feature_flags: { ...config.feature_flags, [module]: enabled },
      });
      mutate(updated, { revalidate: false });
      addToast({
        message: `${MODULE_LABELS[module] ?? module}: ${enabled ? "enabled" : "disabled"}`,
        action: "updated",
      });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [config, mutate, addToast]);

  if (fetchError) {
    return (
      <section className="border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Feature Flags</h3>
        <p className="text-xs text-red-600">Failed to load LLM config</p>
      </section>
    );
  }

  if (!flags) {
    return (
      <section className="border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Feature Flags</h3>
        <p className="text-xs text-gray-400">Loading...</p>
      </section>
    );
  }

  const modules = Object.keys(MODULE_LABELS) as (keyof LLMFeatureFlags)[];

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Feature Flags</h3>
      <p className="text-xs text-gray-500 mb-3">Enable or disable AI features per module.</p>

      <div className="space-y-2">
        {modules.map((mod) => (
          <div
            key={mod}
            className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-50 transition-colors"
          >
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={flags[mod] ?? false}
                onChange={(e) => handleToggle(mod, e.target.checked)}
                disabled={saving}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-forge-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-forge-600" />
            </label>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-700">
                {MODULE_LABELS[mod]}
              </span>
              <p className="text-xs text-gray-400">{MODULE_DESCRIPTIONS[mod]}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

function PermissionsSection() {
  const { data: config, error: fetchError, mutate } = useSWR<LLMConfig>("/llm/config");
  const { addToast } = useToastStore();
  const [saving, setSaving] = useState(false);

  const permissions = config?.permissions;

  const handleToggle = useCallback(async (
    module: string,
    action: keyof LLMModulePermission,
    enabled: boolean,
  ) => {
    if (!config) return;
    setSaving(true);
    try {
      const currentPerm = config.permissions[module] ?? { read: true, write: false, delete: false };
      const updated = await llm.updateConfig({
        permissions: {
          ...config.permissions,
          [module]: { ...currentPerm, [action]: enabled },
        },
      });
      mutate(updated, { revalidate: false });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [config, mutate, addToast]);

  if (fetchError) {
    return (
      <section className="border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Permissions</h3>
        <p className="text-xs text-red-600">Failed to load LLM config</p>
      </section>
    );
  }

  if (!permissions) {
    return (
      <section className="border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Permissions</h3>
        <p className="text-xs text-gray-400">Loading...</p>
      </section>
    );
  }

  const modules = Object.keys(MODULE_LABELS);
  const actions: (keyof LLMModulePermission)[] = ["read", "write", "delete"];

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Permissions</h3>
      <p className="text-xs text-gray-500 mb-3">
        Control what the AI can do in each module.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">
                Module
              </th>
              {actions.map((a) => (
                <th key={a} className="text-center py-2 px-4 text-xs font-medium text-gray-500 uppercase">
                  {a}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {modules.map((mod) => {
              const perm = permissions[mod] ?? { read: true, write: false, delete: false };
              return (
                <tr key={mod} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2 pr-4 text-gray-700">{MODULE_LABELS[mod]}</td>
                  {actions.map((action) => (
                    <td key={action} className="text-center py-2 px-4">
                      <input
                        type="checkbox"
                        checked={perm[action] ?? false}
                        onChange={(e) => handleToggle(mod, action, e.target.checked)}
                        disabled={saving}
                        className="h-4 w-4 rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// AI Capabilities — per-scope operation registry with contracts
// ---------------------------------------------------------------------------

const ACTION_COLORS: Record<string, string> = {
  READ: "bg-blue-100 text-blue-700",
  WRITE: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
};

function ContractView({ contract }: { contract: CapabilityContract }) {
  return (
    <div className="mt-2 p-2 bg-gray-50 rounded text-[11px] font-mono space-y-1.5">
      {contract.params.length > 0 && (
        <div>
          <span className="text-gray-500 font-sans text-[10px] uppercase">Parameters:</span>
          <div className="mt-1 space-y-0.5">
            {contract.params.map((p) => (
              <div key={p.name} className="flex gap-1.5">
                <span className={`${p.required ? "text-gray-800" : "text-gray-500"}`}>
                  {p.name}{p.required ? "" : "?"}
                </span>
                <span className="text-gray-400">:</span>
                <span className="text-purple-600">{p.type}</span>
                {p.enum && (
                  <span className="text-gray-400">({p.enum.join(" | ")})</span>
                )}
                <span className="text-gray-400 font-sans">— {p.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div>
        <span className="text-gray-500 font-sans text-[10px] uppercase">Returns:</span>
        <span className="ml-1.5 text-gray-600 font-sans">{contract.returns}</span>
      </div>
    </div>
  );
}

function CapabilityRow({
  cap,
  permissions,
}: {
  cap: CapabilityDef;
  permissions: Record<string, LLMModulePermission>;
}) {
  const [showContract, setShowContract] = useState(false);
  const status = getPermissionStatus(cap, permissions);

  return (
    <div className="py-1.5">
      <div className="flex items-center gap-2">
        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${ACTION_COLORS[cap.action] ?? "bg-gray-100 text-gray-600"}`}>
          {cap.action}
        </span>
        <span className="text-xs text-gray-800 flex-1">{cap.label}</span>
        <span className={`text-[10px] ${
          status === "enabled" ? "text-green-600" : status === "no-permission" ? "text-red-500" : "text-gray-400"
        }`}>
          {status === "enabled" ? "Enabled" : status === "no-permission" ? "Blocked" : "Coming soon"}
        </span>
        {cap.contract && (
          <button
            onClick={() => setShowContract(!showContract)}
            className="text-[10px] text-forge-600 hover:text-forge-800 underline"
          >
            {showContract ? "Hide" : "Contract"}
          </button>
        )}
      </div>
      <p className="text-[10px] text-gray-400 ml-[38px]">{cap.description}</p>
      {showContract && cap.contract && (
        <div className="ml-[38px]">
          <ContractView contract={cap.contract} />
        </div>
      )}
    </div>
  );
}

function CapabilitiesSection() {
  const { data: config } = useSWR<LLMConfig>("/llm/config");
  const [expandedScopes, setExpandedScopes] = useState<Set<string>>(new Set());
  const permissions = config?.permissions ?? {};

  const toggleScope = useCallback((scope: string) => {
    setExpandedScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) {
        next.delete(scope);
      } else {
        next.add(scope);
      }
      return next;
    });
  }, []);

  const scopes = Object.keys(CAPABILITY_CONTRACTS);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">AI Capabilities</h3>
      <p className="text-xs text-gray-500 mb-3">
        All operations the AI can perform, grouped by scope. Each operation shows its permission status
        (based on Permissions above) and contract details.
      </p>

      <div className="space-y-1">
        {scopes.map((scope) => {
          const caps = CAPABILITY_CONTRACTS[scope] ?? [];
          const expanded = expandedScopes.has(scope);
          const readCount = caps.filter((c) => c.action === "READ").length;
          const writeCount = caps.filter((c) => c.action === "WRITE").length;
          const deleteCount = caps.filter((c) => c.action === "DELETE").length;

          return (
            <div key={scope} className="border rounded-md">
              <button
                onClick={() => toggleScope(scope)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-50 transition-colors text-left"
              >
                <svg
                  className={`h-3 w-3 text-gray-400 transition-transform ${expanded ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="text-sm font-medium text-gray-700 flex-1">
                  {MODULE_LABELS[scope] ?? scope}
                </span>
                <span className="text-[10px] text-gray-400">
                  {readCount}R {writeCount > 0 ? `${writeCount}W ` : ""}{deleteCount > 0 ? `${deleteCount}D ` : ""}
                  ({caps.length} total)
                </span>
              </button>
              {expanded && (
                <div className="px-3 pb-2 border-t divide-y divide-gray-100">
                  {caps.map((cap) => (
                    <CapabilityRow key={cap.id} cap={cap} permissions={permissions} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Limits
// ---------------------------------------------------------------------------

function LimitsSection() {
  const { data: config, mutate } = useSWR<LLMConfig>("/llm/config");
  const { addToast } = useToastStore();
  const [saving, setSaving] = useState(false);
  const [maxTokens, setMaxTokens] = useState<string>("");
  const [maxIter, setMaxIter] = useState<string>("");
  const [ttl, setTtl] = useState<string>("");
  const [initialized, setInitialized] = useState(false);

  // Sync from config once loaded
  useEffect(() => {
    if (config && !initialized) {
      setMaxTokens(String(config.max_tokens_per_session));
      setMaxIter(String(config.max_iterations_per_turn));
      setTtl(String(config.session_ttl_hours));
      setInitialized(true);
    }
  }, [config, initialized]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await llm.updateConfig({
        max_tokens_per_session: Number(maxTokens) || 100000,
        max_iterations_per_turn: Number(maxIter) || 10,
        session_ttl_hours: Number(ttl) || 24,
      });
      mutate(updated, { revalidate: false });
      addToast({ message: "Limits saved", action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [maxTokens, maxIter, ttl, mutate, addToast]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Limits</h3>
      <p className="text-xs text-gray-500 mb-3">Session and safety limits.</p>

      <div className="space-y-3 max-w-md">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Max Tokens per Session</label>
          <input
            type="number"
            value={maxTokens}
            onChange={(e) => setMaxTokens(e.target.value)}
            className="w-full text-sm border rounded-md px-3 py-1.5"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Max Iterations per Turn</label>
          <input
            type="number"
            value={maxIter}
            onChange={(e) => setMaxIter(e.target.value)}
            className="w-full text-sm border rounded-md px-3 py-1.5"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Session TTL (hours)</label>
          <input
            type="number"
            value={ttl}
            onChange={(e) => setTtl(e.target.value)}
            className="w-full text-sm border rounded-md px-3 py-1.5"
          />
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Limits"}
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Debug Console
// ---------------------------------------------------------------------------

function DebugConsoleSection() {
  const { panelState, toggle } = useDebugPanelStore();
  const isOpen = panelState !== "collapsed";

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Debug Console</h3>
      <p className="text-xs text-gray-500 mb-3">
        View API requests, LLM calls, and WebSocket events.
        Toggle with <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">Ctrl+`</kbd>
      </p>
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-forge-500 focus:ring-offset-2"
          style={{ backgroundColor: isOpen ? "#2563eb" : "#d1d5db" }}
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
              isOpen ? "translate-x-[18px]" : "translate-x-[2px]"
            }`}
          />
        </button>
        <span className="text-sm text-gray-600">
          {isOpen ? "Open" : "Closed"}
        </span>
      </div>
    </section>
  );
}
