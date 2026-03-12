import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { SWRProvider } from "@/lib/swr-config";
import { ToastContainer } from "@/components/shared/ToastContainer";
import { DebugInit } from "@/components/debug/DebugInit";

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
      <body className="flex h-screen overflow-hidden">
        <SWRProvider>
          <DebugInit />
          <Sidebar />
          <main className="flex-1 overflow-hidden">{children}</main>
          <ToastContainer />
        </SWRProvider>
      </body>
    </html>
  );
}
