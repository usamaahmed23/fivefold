import type { Role } from "@/lib/types";

// Distinct glyphs per role — single-color, stroke-based for clarity at small sizes.
export function RoleIcon({ role, className = "" }: { role: Role; className?: string }) {
  const common = {
    viewBox: "0 0 24 24",
    className,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (role) {
    case "top":
      // Crossed swords — top lane is the bruiser/skirmish duel lane.
      return (
        <svg {...common}>
          <path d="M3 3l9 9" />
          <path d="M21 3l-9 9" />
          <path d="M12 12l-3 3 2 2 3-3" />
          <path d="M12 12l3 3-2 2-3-3" />
          <path d="M7 17l-3 3" />
          <path d="M17 17l3 3" />
        </svg>
      );
    case "jungle":
      // Pine tree + monster claw — the jungle.
      return (
        <svg {...common}>
          <path d="M12 3l-5 7h3l-4 6h4l-3 5h10l-3-5h4l-4-6h3z" />
          <path d="M12 21v-2" />
        </svg>
      );
    case "mid":
      // Wand with sparkles — the mage / burst lane.
      return (
        <svg {...common}>
          <path d="M4 20l12-12" />
          <path d="M14 6l4 4" />
          <path d="M19 3l.8 2.2L22 6l-2.2.8L19 9l-.8-2.2L16 6l2.2-.8z" />
          <path d="M6 4l.5 1.5L8 6l-1.5.5L6 8l-.5-1.5L4 6l1.5-.5z" />
          <path d="M20 15l.4 1.2L21.5 17l-1.2.4L20 18.5l-.4-1.2L18.5 17l1.2-.4z" />
        </svg>
      );
    case "bot":
      // Crosshair / reticle — the marksman's target.
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" />
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v4" />
          <path d="M12 18v4" />
          <path d="M2 12h4" />
          <path d="M18 12h4" />
        </svg>
      );
    case "support":
      // Ward / eye — vision and peel.
      return (
        <svg {...common}>
          <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z" />
          <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" />
        </svg>
      );
  }
}
