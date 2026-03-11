/// <reference types="vitest/globals" />
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock Next.js modules for component testing
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => {
    const React = require("react");
    return React.createElement("a", { href, ...props }, children);
  },
}));

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    const React = require("react");
    return React.createElement("img", props);
  },
}));
