import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { SWRProvider } from "@/lib/swr-config";
import { ToastContainer } from "@/components/shared/ToastContainer";

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
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
          <ToastContainer />
        </SWRProvider>
      </body>
    </html>
  );
}
