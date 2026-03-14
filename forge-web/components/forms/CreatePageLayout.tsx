"use client";

import Link from "next/link";
import { Button } from "@/components/shared/Button";

interface CreatePageLayoutProps {
  title: string;
  backHref: string;
  submitting: boolean;
  onSubmit: () => void;
  children: React.ReactNode;
}

export function CreatePageLayout({
  title,
  backHref,
  submitting,
  onSubmit,
  children,
}: CreatePageLayoutProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex items-center gap-2">
          <Link href={backHref}>
            <Button variant="secondary" size="sm" type="button">
              Cancel
            </Button>
          </Link>
          <Button size="sm" onClick={onSubmit} disabled={submitting}>
            {submitting ? "Creating..." : "Create"}
          </Button>
        </div>
      </div>
      <div className="max-w-2xl">
        <div className="bg-gray-50 border rounded-lg p-6 space-y-1">
          {children}
        </div>
      </div>
    </div>
  );
}
