"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationCenter } from "./NotificationCenter";

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

const mainNav: NavItem[] = [
  { label: "Dashboard", href: "/", icon: "\u25A6" },
  { label: "Projects", href: "/projects", icon: "\uD83D\uDCC1" },
  { label: "Skills", href: "/skills", icon: "\u26A1" },
  { label: "Sessions", href: "/sessions", icon: "\uD83D\uDCAC" },
];

const rightNav: NavItem[] = [
  { label: "Settings", href: "/settings/llm", icon: "\u2699" },
];

export function TopNavBar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const linkClasses = (href: string) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
      isActive(href)
        ? "bg-gray-700 text-white font-medium"
        : "text-gray-300 hover:text-white hover:bg-gray-800"
    }`;

  return (
    <header
      className="h-[var(--topnav-height)] flex-shrink-0 bg-gray-900 text-white flex items-center px-4 border-b border-gray-800"
    >
      <Link href="/" className="text-lg font-bold text-white mr-6 flex-shrink-0">
        Forge
      </Link>

      <nav className="flex items-center gap-1 flex-1">
        {mainNav.map((item) => (
          <Link key={item.href} href={item.href} className={linkClasses(item.href)}>
            <span className="text-base">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <nav className="flex items-center gap-2">
        <NotificationCenter />
        {rightNav.map((item) => (
          <Link key={item.href} href={item.href} className={linkClasses(item.href)}>
            <span className="text-base">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
