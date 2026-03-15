"use client";

import { Category, CATEGORIES, CATEGORY_CONFIG } from "@/lib/api";

interface CategoryFilterProps {
  selected: Category | null;
  onSelect: (category: Category | null) => void;
  counts?: Record<string, number>;
}

export default function CategoryFilter({
  selected,
  onSelect,
  counts,
}: CategoryFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => onSelect(null)}
        className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
          selected === null
            ? "bg-slate-800 text-white"
            : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
        }`}
      >
        すべて{counts ? ` (${Object.values(counts).reduce((a, b) => a + b, 0)})` : ""}
      </button>
      {CATEGORIES.map((cat) => {
        const config = CATEGORY_CONFIG[cat];
        const count = counts?.[cat] ?? 0;
        if (counts && count === 0) return null;
        return (
          <button
            key={cat}
            onClick={() => onSelect(cat)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
              selected === cat
                ? "bg-slate-800 text-white"
                : `bg-white ${config.color} border border-slate-200 hover:bg-slate-100`
            }`}
          >
            {config.emoji} {cat}{counts ? ` (${count})` : ""}
          </button>
        );
      })}
    </div>
  );
}
