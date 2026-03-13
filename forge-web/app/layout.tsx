import type { Metadata } from "next";
import "./globals.css";
import { TopNavBar } from "@/components/layout/TopNavBar";
import { LeftPanelProvider } from "@/components/layout/LeftPanelProvider";
import { LeftPanel } from "@/components/layout/LeftPanel";
import { AISidebarShell } from "@/components/ai/AISidebarShell";
import { SWRProvider } from "@/lib/swr-config";
import { ToastContainer } from "@/components/shared/ToastContainer";
import { DecisionNotificationPopup } from "@/components/shared/DecisionNotificationPopup";
import { DebugInit } from "@/components/debug/DebugInit";
import { BottomPanel } from "@/components/debug/BottomPanel";
import { AIPageProvider } from "@/lib/ai-context";

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
          <AIPageProvider>
            <TopNavBar />
            <LeftPanelProvider>
              <div className="flex flex-1 overflow-hidden">
                <LeftPanel />
                <main className="flex-1 overflow-y-auto">{children}</main>
                <AISidebarShell />
              </div>
            </LeftPanelProvider>
            <ToastContainer />
            <DecisionNotificationPopup />
            <BottomPanel />
          </AIPageProvider>
        </SWRProvider>
      </body>
    </html>
  );
}
