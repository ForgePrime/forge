"use client";

import { usePathname } from "next/navigation";
import { useSidebarStore } from "@/stores/sidebarStore";
import { RightSidebarSlot } from "@/components/layout/RightSidebarSlot";
import AISidebar from "./AISidebar";
import { useEffect } from "react";

export function AISidebarShell() {
  const pathname = usePathname();
  const { isRouteHidden, hydrate } = useSidebarStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  if (isRouteHidden(pathname)) {
    return null;
  }

  return (
    <RightSidebarSlot>
      <AISidebar />
    </RightSidebarSlot>
  );
}
