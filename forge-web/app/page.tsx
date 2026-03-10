"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useProjectStore } from "@/stores/projectStore";
import { Card } from "@/components/shared/Card";

export default function DashboardPage() {
  const { slugs, statuses, loading, error, fetchProjects, fetchStatus } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Fetch status for each project once slugs are loaded
  useEffect(() => {
    slugs.forEach((slug) => {
      if (!statuses[slug]) fetchStatus(slug);
    });
  }, [slugs, statuses, fetchStatus]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Forge Dashboard</h1>
        <Link
          href="/projects"
          className="text-sm text-forge-600 hover:text-forge-700 font-medium"
        >
          View all projects
        </Link>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && slugs.length === 0 && (
        <p className="text-gray-500">Loading projects...</p>
      )}

      {!loading && slugs.length === 0 && (
        <Card>
          <p className="text-gray-500">No projects yet. Use <code className="bg-gray-100 px-1 rounded">/plan</code> to create one.</p>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {slugs.map((slug) => {
          const status = statuses[slug];
          return (
            <Link key={slug} href={`/projects/${slug}`}>
              <Card className="hover:border-forge-300 transition-colors cursor-pointer">
                <h2 className="text-lg font-semibold mb-1">{slug}</h2>
                {status ? (
                  <>
                    <p className="text-sm text-gray-500 mb-3 line-clamp-2">{status.goal}</p>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-gray-500">{status.total_tasks} tasks</span>
                      {status.progress_pct != null && (
                        <div className="flex-1">
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-forge-500 rounded-full transition-all"
                              style={{ width: `${Math.round(status.progress_pct)}%` }}
                            />
                          </div>
                        </div>
                      )}
                      <span className="text-forge-600 font-medium">
                        {Math.round(status.progress_pct ?? 0)}%
                      </span>
                    </div>
                    {status.status_counts && (
                      <div className="flex gap-2 mt-2 text-xs">
                        {Object.entries(status.status_counts).map(([key, val]) => (
                          val > 0 && (
                            <span key={key} className="text-gray-400">
                              {key}: {val}
                            </span>
                          )
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-400">Loading...</p>
                )}
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
