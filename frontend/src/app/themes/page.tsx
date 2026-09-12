"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getThemes, ThemeSummary } from "@/lib/api";

export default function ThemesPage() {
  const [themes, setThemes] = useState<ThemeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getThemes();
        // 件数の多い順に並べる（同数の場合は元の並び順を維持）
        const sorted = [...data].sort((a, b) => b.count - a.count);
        setThemes(sorted);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-500">テーマ一覧の取得に失敗しました。</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-800 mb-2">テーマから探す</h2>
      <p className="text-sm text-slate-500 mb-6">
        「夏の汗」「学校・保育園」など、困りごとのテーマからこれまでの記事をまとめて読めます。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {themes.map((theme) => {
          const hasArticles = theme.count > 0;
          return (
            <Link
              key={theme.key}
              href={`/themes/${theme.key}`}
              className={`block rounded-lg border p-4 transition hover:shadow-md ${
                hasArticles
                  ? "bg-white border-slate-200 hover:border-blue-300"
                  : "bg-slate-50 border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-base font-semibold text-slate-800">
                  {theme.label}
                </h3>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${
                    hasArticles
                      ? "bg-blue-50 text-blue-700"
                      : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {theme.count}件
                </span>
              </div>
              {!hasArticles && (
                <p className="text-xs text-slate-400 mt-2">
                  まだ情報がありません
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
