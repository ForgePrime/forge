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
  ProviderModel,
} from "@/lib/types";
import {
  ALL_SCOPES,
  fetchAllContracts,
  getPermissionStatus,
  type CapabilityDef,
  type CapabilityContract,
} from "@/lib/capabilities";
import { useAIPage } from "@/lib/ai-context";

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
  useAIPage({
    id: "llm-settings",
    title: "LLM Settings",
    description: "AI providers, feature flags, module permissions",
    route: "/settings/llm",
  });

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
      <CapabilitiesSection />
      <CustomAppContextSection />
      <LimitsSection />
      <DebugConsoleSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

const KEY_SOURCE_LABELS: Record<string, string> = {
  ui: "Settings (UI)",
  env: "Environment variable",
  config: "providers.toml",
  login: "Claude Max subscription",
  none: "Not configured",
};

function ProviderCard({
  provider,
  config,
  onConfigUpdate,
}: {
  provider: LLMProvider;
  config: LLMConfig;
  onConfigUpdate: (data: Partial<LLMConfig>) => Promise<void>;
}) {
  const { addToast } = useToastStore();
  const isDefault = config.default_provider === provider.name;
  const needsKey = !["ollama", "claude-code"].includes(provider.provider_type);

  // API key state
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  // Model state
  const { data: modelsData, isLoading: modelsLoading } = useSWR<{
    provider: string;
    models: ProviderModel[];
  }>(`/llm/providers/${provider.name}/models`, () =>
    llm.getProviderModels(provider.name),
  );
  const models = modelsData?.models ?? [];
  const selectedModel = config.default_provider === provider.name
    ? config.default_model ?? provider.default_model
    : provider.default_model;

  // Test state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LLMProviderTestResult | null>(null);

  const handleSaveKey = useCallback(async () => {
    if (!apiKey.trim()) return;
    setSavingKey(true);
    try {
      await onConfigUpdate({
        api_keys: { ...config.api_keys, [provider.name]: apiKey },
      } as Partial<LLMConfig>);
      setApiKey("");
      addToast({ message: `API key saved for ${provider.name}`, action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSavingKey(false);
    }
  }, [apiKey, provider.name, config.api_keys, onConfigUpdate, addToast]);

  const handleRemoveKey = useCallback(async () => {
    try {
      await onConfigUpdate({
        api_keys: { ...config.api_keys, [provider.name]: "" },
      } as Partial<LLMConfig>);
      addToast({ message: `API key removed for ${provider.name}`, action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    }
  }, [provider.name, config.api_keys, onConfigUpdate, addToast]);

  const handleSetDefault = useCallback(async (model?: string) => {
    try {
      await onConfigUpdate({
        default_provider: provider.name,
        default_model: model ?? provider.default_model,
      });
      addToast({ message: `Default provider: ${provider.name}`, action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    }
  }, [provider.name, provider.default_model, onConfigUpdate, addToast]);

  const handleModelChange = useCallback(async (modelId: string) => {
    try {
      await onConfigUpdate({
        default_provider: provider.name,
        default_model: modelId,
      });
      addToast({ message: `Model: ${modelId}`, action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    }
  }, [provider.name, onConfigUpdate, addToast]);

  const handleTest = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await llm.testProvider(provider.name);
      setTestResult(result);
      addToast({
        message: result.status === "ok"
          ? `${provider.name}: connected (${result.latency_ms}ms)`
          : `${provider.name}: ${result.error ?? "failed"}`,
        action: result.status === "ok" ? "info" : "failed",
      });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setTesting(false);
    }
  }, [provider.name, addToast]);

  // Find selected model caps
  const selectedModelInfo = models.find((m) => m.id === selectedModel);

  return (
    <div className="border rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-gray-800">{provider.name}</span>
        <span className="text-[10px] text-gray-400 uppercase">{provider.provider_type}</span>
        {isDefault && <Badge variant="success">default</Badge>}
        {!isDefault && (
          <button
            onClick={() => handleSetDefault()}
            className="text-[10px] text-forge-600 hover:text-forge-800 underline ml-auto"
          >
            Set as default
          </button>
        )}
        {/* Status dot */}
        <span className={`ml-auto h-2 w-2 rounded-full ${
          testResult?.status === "ok" ? "bg-green-500"
          : testResult?.status === "error" ? "bg-red-500"
          : provider.has_api_key ? "bg-gray-300"
          : "bg-yellow-400"
        }`} title={testResult?.status ?? provider.has_api_key ? "Ready" : "No API key"} />
      </div>

      {/* API Key */}
      {needsKey && (
        <div>
          <label className="text-xs text-gray-500 block mb-1">API Key</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={
                  config.api_keys?.[provider.name]
                    ? config.api_keys[provider.name]
                    : "Enter API key..."
                }
                className="w-full text-sm border rounded-md px-3 py-1.5 pr-8 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                title={showKey ? "Hide" : "Show"}
                type="button"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {showKey ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  ) : (
                    <>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </>
                  )}
                </svg>
              </button>
            </div>
            <Button size="sm" onClick={handleSaveKey} disabled={savingKey || !apiKey.trim()}>
              {savingKey ? "..." : "Save"}
            </Button>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-gray-400">
              Source: {KEY_SOURCE_LABELS[provider.api_key_source] ?? provider.api_key_source}
            </span>
            {provider.api_key_source === "ui" && (
              <button
                onClick={handleRemoveKey}
                className="text-[10px] text-red-400 hover:text-red-600 underline"
              >
                Remove
              </button>
            )}
          </div>
        </div>
      )}

      {/* Model Selector */}
      <div>
        <label className="text-xs text-gray-500 block mb-1">Model</label>
        <select
          value={selectedModel}
          onChange={(e) => handleModelChange(e.target.value)}
          className="w-full text-sm border rounded-md px-3 py-1.5 focus:border-forge-500 focus:ring-1 focus:ring-forge-500 bg-white"
          disabled={modelsLoading}
        >
          {modelsLoading && <option>Loading models...</option>}
          {!modelsLoading && models.length === 0 && (
            <option value={provider.default_model}>{provider.default_model}</option>
          )}
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        {selectedModelInfo && (
          <p className="text-[10px] text-gray-400 mt-1">
            {selectedModelInfo.context_window
              ? `${Math.round(selectedModelInfo.context_window / 1000)}k context`
              : ""}
            {selectedModelInfo.max_output
              ? ` · ${Math.round(selectedModelInfo.max_output / 1000)}k output`
              : ""}
            {selectedModelInfo.supports_vision ? " · vision" : ""}
          </p>
        )}
      </div>

      {/* Test + Result */}
      <div className="flex items-center gap-3">
        <Button size="sm" variant="secondary" onClick={handleTest} disabled={testing}>
          {testing ? "Testing..." : "Test Connection"}
        </Button>
        {testResult && (
          <span className={`text-xs ${testResult.status === "ok" ? "text-green-600" : "text-red-600"}`}>
            {testResult.status === "ok"
              ? `Connected (${testResult.latency_ms}ms)`
              : testResult.error ?? "Failed"}
          </span>
        )}
      </div>
    </div>
  );
}

function ProvidersSection() {
  const { data, error, isLoading } = useSWR<{ providers: LLMProvider[] }>(
    "/llm/providers",
    () => llm.getProviders(),
  );
  const { data: config, mutate: mutateConfig } = useSWR<LLMConfig>(
    "/llm/config",
    () => llm.getConfig(),
  );

  const handleConfigUpdate = useCallback(async (update: Partial<LLMConfig>) => {
    const updated = await llm.updateConfig(update);
    mutateConfig(updated, { revalidate: false });
  }, [mutateConfig]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Providers</h3>
      <p className="text-xs text-gray-500 mb-3">
        Configure API keys, select models, and test connections.
      </p>

      {isLoading && <p className="text-xs text-gray-400">Loading providers...</p>}
      {error && <p className="text-xs text-red-600">Failed to load providers</p>}

      {data && data.providers.length === 0 && (
        <p className="text-xs text-gray-400">
          No providers configured. Add providers to{" "}
          <code className="bg-gray-100 px-1 rounded text-[10px]">config/providers.toml</code>.
        </p>
      )}

      {config && (
        <div className="space-y-3">
          {data?.providers.map((p) => (
            <ProviderCard
              key={p.name}
              provider={p}
              config={config}
              onConfigUpdate={handleConfigUpdate}
            />
          ))}
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
  const [gitUserName, setGitUserName] = useState("");
  const [gitUserEmail, setGitUserEmail] = useState("");
  const [gitToken, setGitToken] = useState("");
  const [hasGitToken, setHasGitToken] = useState(false);
  const [configuredVia, setConfiguredVia] = useState("");
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    skillsApi.getConfig().then((config) => {
      setRepoUrl(config.repo_url ?? "");
      setGitUserName(config.git_user_name ?? "");
      setGitUserEmail(config.git_user_email ?? "");
      setHasGitToken(config.has_git_token ?? false);
      setConfiguredVia(config.configured_via ?? "none");
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload: Record<string, string> = {
        repo_url: repoUrl,
        git_user_name: gitUserName,
        git_user_email: gitUserEmail,
      };
      // Only send token if user typed a new one (not the masked placeholder)
      if (gitToken && !gitToken.startsWith("****")) {
        payload.git_token = gitToken;
      }
      await skillsApi.updateConfig(payload);
      setConfiguredVia(repoUrl ? "persisted" : "none");
      if (gitToken && !gitToken.startsWith("****")) {
        setHasGitToken(true);
        setGitToken("");
      }
      addToast({ message: "Git sync settings saved", action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [repoUrl, gitUserName, gitUserEmail, gitToken, addToast]);

  const inputCls = "w-full text-sm border rounded-md px-3 py-1.5 focus:border-forge-500 focus:ring-1 focus:ring-forge-500";

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Skills Git Sync</h3>
      <p className="text-xs text-gray-500 mb-3">
        Configure git repository, identity, and authentication for syncing skills.
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
              className={inputCls}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Git User Name</label>
              <input
                type="text"
                value={gitUserName}
                onChange={(e) => setGitUserName(e.target.value)}
                placeholder="Your Name"
                className={inputCls}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Git User Email</label>
              <input
                type="email"
                value={gitUserEmail}
                onChange={(e) => setGitUserEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">
              Access Token (GitHub PAT)
              {hasGitToken && <span className="text-green-600 ml-2">configured</span>}
            </label>
            <input
              type="password"
              value={gitToken}
              onChange={(e) => setGitToken(e.target.value)}
              placeholder={hasGitToken ? "Enter new token to replace" : "ghp_..."}
              className={inputCls}
            />
            <p className="text-[10px] text-gray-400 mt-0.5">
              Used for HTTPS authentication. Never stored in .git/config.
            </p>
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
// AI Capabilities — per-scope operations with inline R/W/D permission toggles
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
  const { data: config, mutate } = useSWR<LLMConfig>("/llm/config");
  const { data: allCaps = [] } = useSWR("all-contracts", fetchAllContracts);
  const { addToast } = useToastStore();
  const [expandedScopes, setExpandedScopes] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
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

  const handlePermToggle = useCallback(async (
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

  // Group capabilities by scope
  const capsByScope = new Map<string, CapabilityDef[]>();
  for (const cap of allCaps) {
    const scope = cap.scope || "global";
    if (!capsByScope.has(scope)) capsByScope.set(scope, []);
    capsByScope.get(scope)!.push(cap);
  }

  // Show all scopes that have capabilities
  const scopes = ALL_SCOPES.filter((s) => capsByScope.has(s));

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">AI Capabilities & Permissions</h3>
      <p className="text-xs text-gray-500 mb-3">
        All operations the AI can perform, grouped by scope. Use R/W/D toggles to control permissions per scope.
      </p>

      <div className="space-y-1">
        {scopes.map((scope) => {
          const caps = capsByScope.get(scope) ?? [];
          const expanded = expandedScopes.has(scope);
          const readCount = caps.filter((c) => c.action === "READ").length;
          const writeCount = caps.filter((c) => c.action === "WRITE").length;
          const deleteCount = caps.filter((c) => c.action === "DELETE").length;
          const perm = permissions[scope] ?? { read: true, write: false, delete: false };

          return (
            <div key={scope} className="border rounded-md">
              <div className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 transition-colors">
                <button
                  onClick={() => toggleScope(scope)}
                  className="flex items-center gap-2 flex-1 text-left"
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
                    ({caps.length})
                  </span>
                </button>
                {/* Inline R/W/D permission toggles */}
                <div className="flex items-center gap-1.5 ml-2" onClick={(e) => e.stopPropagation()}>
                  {(["read", "write", "delete"] as const).map((action) => {
                    const label = action[0].toUpperCase();
                    const checked = perm[action] ?? false;
                    const color = action === "read" ? "text-blue-600" : action === "write" ? "text-amber-600" : "text-red-600";
                    return (
                      <label key={action} className="flex items-center gap-0.5 cursor-pointer" title={`${action} permission`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => handlePermToggle(scope, action, e.target.checked)}
                          disabled={saving}
                          className="h-3 w-3 rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                        />
                        <span className={`text-[9px] font-bold ${checked ? color : "text-gray-400"}`}>{label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
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
// Custom App Context
// ---------------------------------------------------------------------------

function CustomAppContextSection() {
  const { data: config, mutate } = useSWR<LLMConfig>("/llm/config");
  const { addToast } = useToastStore();
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (config && !initialized) {
      setText(config.custom_app_context ?? "");
      setInitialized(true);
    }
  }, [config, initialized]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await llm.updateConfig({ custom_app_context: text });
      mutate(updated, { revalidate: false });
      addToast({ message: "Custom App Context saved", action: "updated" });
    } catch (e) {
      addToast({ message: (e as Error).message, action: "failed" });
    } finally {
      setSaving(false);
    }
  }, [text, mutate, addToast]);

  return (
    <section className="border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Custom App Context</h3>
      <p className="text-xs text-gray-500 mb-3">
        Custom instructions injected into every AI system prompt. Use this to define team conventions,
        project-specific rules, or behavioral guidelines that the AI should always follow.
      </p>
      <div className="space-y-2 max-w-2xl">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Example: Always respond in Polish. Use snake_case for Python variables. Our API endpoints follow REST conventions..."
          rows={6}
          className="w-full text-sm border rounded-md px-3 py-2 focus:border-forge-500 focus:ring-1 focus:ring-forge-500 font-mono resize-y"
        />
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-gray-400">
            {text.length} characters
            {text.length > 0 && ` (~${Math.ceil(text.length / 4)} tokens)`}
          </span>
          <Button size="sm" onClick={handleSave} disabled={saving || text === (config?.custom_app_context ?? "")}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
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
