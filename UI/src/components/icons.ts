import {
  Bandage,
  CalendarClock,
  Footprints,
  HeartPulse,
  Moon,
  Package,
  Pill,
  Sun,
  TriangleAlert,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import type { Category } from "@/lib/types";

export const CATEGORY_ICON: Record<Category, LucideIcon> = {
  sleep: Moon,
  meals_hydration: Utensils,
  medication: Pill,
  mood_behavior: Sun,
  mobility_falls: Footprints,
  pain: Bandage,
  vitals: HeartPulse,
  incident: TriangleAlert,
  appointment: CalendarClock,
  logistics: Package,
};

/** Shared icon size/stroke so every screen draws icons the same way. */
export const ICON = { size: 20, strokeWidth: 1.75 } as const;
