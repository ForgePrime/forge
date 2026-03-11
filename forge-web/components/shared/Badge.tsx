import { HTMLAttributes } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  success: "bg-green-100 text-green-700",
  warning: "bg-yellow-100 text-yellow-700",
  danger: "bg-red-100 text-red-700",
  info: "bg-blue-100 text-blue-700",
};

export function Badge({ variant = "default", className = "", children, ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}

/** Map entity status strings to badge variants. */
export function statusVariant(status: string): BadgeVariant {
  switch (status) {
    case "DONE":
    case "ACTIVE":
    case "CLOSED":
    case "APPROVED":
      return "success";
    case "IN_PROGRESS":
    case "CLAIMING":
    case "EXPLORING":
      return "info";
    case "FAILED":
    case "REJECTED":
    case "DEPRECATED":
    case "ABANDONED":
    case "ARCHIVED":
      return "danger";
    case "TODO":
    case "DRAFT":
    case "OPEN":
    case "DEFERRED":
    case "PAUSED":
      return "warning";
    case "ACHIEVED":
    case "MITIGATED":
    case "ACCEPTED":
    case "COMMITTED":
      return "success";
    case "ANALYZING":
      return "info";
    default:
      return "default";
  }
}
