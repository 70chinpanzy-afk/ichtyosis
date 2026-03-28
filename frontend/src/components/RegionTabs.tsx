"use client";

import { Region, REGION_CONFIG } from "@/lib/api";

interface RegionTabsProps {
  selected: Region | null;
  onSelect: (region: Region | null) => void;
  counts?: { japan: number; international: number };
}

const REGIONS: Region[] = ["japan", "international"];

export default function RegionTabs({
  selected,
  onSelect,
  counts,
}: RegionTabsProps) {
  return (
    <div className="flex border-b border-slate-200 mb-6">
      <button
        onClick={() => onSelect(null)}
        className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
          selected === null
            ? "border-blue-600 text-blue-600"
            : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
        }`}
      >
        すべて
        {counts && (
          <span className="ml-1.5 text-xs text-slate-400">
            ({counts.japan + counts.international})
          </span>
        )}
      </button>
      {REGIONS.map((region) => {
        const config = REGION_CONFIG[region];
        const count = counts?.[region] ?? 0;
        return (
          <button
            key={region}
            onClick={() => onSelect(region)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
              selected === region
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            {config.emoji} {config.label}
            {counts && (
              <span className="ml-1.5 text-xs text-slate-400">({count})</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
