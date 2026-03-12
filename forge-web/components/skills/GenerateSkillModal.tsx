"use client";

import { useState } from "react";
import { skills as skillsApi } from "@/lib/api";
import { Button } from "@/components/shared/Button";

interface GenerateSkillModalProps {
  onGenerated: (content: string) => void;
  onClose: () => void;
}

const CATEGORY_OPTIONS = [
  "workflow", "analysis", "generation", "validation", "integration",
  "refactoring", "testing", "deployment", "documentation",
];

export function GenerateSkillModal({ onGenerated, onClose }: GenerateSkillModalProps) {
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("workflow");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await skillsApi.generate({
        description: description.trim(),
        categories: [category],
      });
      onGenerated(res.skill_md_content);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="font-semibold text-sm">Generate Skill with AI</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Describe what this skill should do
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. A skill that reviews Pull Requests for security vulnerabilities, checks for common OWASP issues, and provides actionable recommendations..."
              rows={4}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
        </div>

        <div className="flex justify-end gap-2 px-4 py-3 border-t">
          <Button size="sm" variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={loading || !description.trim()}
          >
            {loading ? "Generating..." : "Generate SKILL.md"}
          </Button>
        </div>
      </div>
    </div>
  );
}
