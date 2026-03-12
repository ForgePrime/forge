import type { Metadata } from "next";
import "./globals.css";
import { TopNavBar } from "@/components/layout/TopNavBar";
import { LeftPanelProvider } from "@/components/layout/LeftPanelProvider";
import { LeftPanel } from "@/components/layout/LeftPanel";
import { RightSidebarSlot } from "@/components/layout/RightSidebarSlot";
import { SWRProvider } from "@/lib/swr-config";
import { ToastContainer } from "@/components/shared/ToastContainer";
import { DebugInit } from "@/components/debug/DebugInit";
import { BottomPanel } from "@/components/debug/BottomPanel";

export const metadata: Metadata = {
  title: "Forge Platform",
  description: "Structured Change Orchestrator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex flex-col h-screen overflow-hidden">
        <SWRProvider>
          <DebugInit />
          <TopNavBar />
          <LeftPanelProvider>
            <div className="flex flex-1 overflow-hidden">
              <LeftPanel />
              <main className="flex-1 overflow-y-auto">{children}</main>
              <RightSidebarSlot />
            </div>
          </LeftPanelProvider>
          <ToastContainer />
          <BottomPanel />
        </SWRProvider>
      </body>
    </html>
  );
}
