"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useProjectStore } from "@/stores/projectStore";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/shared/Button";

export default function ProjectsPage() {
  const { slugs, statuses, loading, error, fetchProjects, fetchStatus, createProject } =
    useProjectStore();
  const [showCreate, setShowCreate] = useState(false);
  const [newSlug, setNewSlug] = useState("");
  const [newGoal, setNewGoal] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    slugs.forEach((slug) => {
      if (!statuses[slug]) fetchStatus(slug);
    });
  }, [slugs, statuses, fetchStatus]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSlug.trim()) return;
    setCreating(true);
    try {
      await createProject({ slug: newSlug.trim(), goal: newGoal.trim() });
      setNewSlug("");
      setNewGoal("");
      setShowCreate(false);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Button size="sm" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancel" : "New Project"}
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {showCreate && (
        <Card className="mb-6">
          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
              <input
                type="text"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="my-project"
                className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Goal</label>
              <input
                type="text"
                value={newGoal}
                onChange={(e) => setNewGoal(e.target.value)}
                placeholder="Build a platform for..."
                className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
            </div>
            <Button type="submit" size="sm" disabled={creating || !newSlug.trim()}>
              {creating ? "Creating..." : "Create Project"}
            </Button>
          </form>
        </Card>
      )}

      {loading && slugs.length === 0 && (
        <p className="text-gray-500">Loading projects...</p>
      )}

      <div className="space-y-3">
        {slugs.map((slug) => {
          const status = statuses[slug];
          return (
            <Link key={slug} href={`/projects/${slug}`}>
              <Card className="hover:border-forge-300 transition-colors cursor-pointer flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">{slug}</h2>
                  {status && (
                    <p className="text-sm text-gray-500 mt-0.5">{status.goal}</p>
                  )}
                </div>
                {status && (
                  <div className="text-right text-sm">
                    <div className="text-forge-600 font-medium">
                      {Math.round(status.progress_pct ?? 0)}%
                    </div>
                    <div className="text-xs text-gray-400">
                      {status.total_tasks} tasks
                    </div>
                  </div>
                )}
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
