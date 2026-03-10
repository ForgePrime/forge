"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useProjectStore } from "@/stores/projectStore";

interface NavItem {
  label: string;
  segment: string;
}

const entityNav: NavItem[] = [
  { label: "Overview", segment: "" },
  { label: "Tasks", segment: "tasks" },
  { label: "Decisions", segment: "decisions" },
  { label: "Objectives", segment: "objectives" },
  { label: "Ideas", segment: "ideas" },
  { label: "Knowledge", segment: "knowledge" },
  { label: "Guidelines", segment: "guidelines" },
  { label: "Changes", segment: "changes" },
  { label: "Lessons", segment: "lessons" },
];

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const slug = params.slug as string;
  const { details, selectProject } = useProjectStore();
  const detail = details[slug];

  useEffect(() => {
    if (slug) selectProject(slug);
  }, [slug, selectProject]);

  const basePath = `/projects/${slug}`;

  return (
    <div>
      {/* Project header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
          <Link href="/projects" className="hover:text-gray-600">Projects</Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">{slug}</span>
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
