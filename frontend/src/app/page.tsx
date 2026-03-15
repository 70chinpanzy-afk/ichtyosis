"use client";

import { useState, useEffect } from "react";
import {
  Article,
  Category,
  getDigests,
  getDigestByDate,
  DigestSummary,
} from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import CategoryFilter from "@/components/CategoryFilter";
import DigestHeader from "@/components/DigestHeader";
import SearchBar from "@/components/SearchBar";

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [digests, setDigests] = useState<DigestSummary[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const digestList = await getDigests(7);
        setDigests(digestList);

        if (digestList.length > 0) {
          const latestArticles = await getDigestByDate(digestList[0].date);
          setArticles(latestArticles);
        }
      } catch (e) {
        setError(
          "データの取得に失敗しました。バックエンドAPIが起動しているか確認してください。"
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredArticles = selectedCategory
    ? articles.filter((a) => a.category === selectedCategory)
    : articles;

  const categoryCounts: Record<string, number> = {};
  for (const a of articles) {
    if (a.category) {
      categoryCounts[a.category] = (categoryCounts[a.category] || 0) + 1;
    }
  }

  const latestDate = digests.length > 0 ? digests[0].date : "";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4" />
        <p className="text-slate-500">最新のキュレーション情報を取得中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-6xl mb-4">{"\u{1f52c}"}</p>
        <h2 className="text-xl font-bold text-slate-800 mb-2">
          IchthyoCure へようこそ
        </h2>
        <p className="text-slate-500 mb-6 max-w-md mx-auto">
          魚鱗癬紅皮症に関する最新の医学情報を毎日キュレーションしてお届けします。
        </p>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 max-w-md mx-auto">
          <p className="text-sm text-amber-800">{error}</p>
          <p className="text-xs text-amber-600 mt-2">
            バックエンド起動:
            <code className="bg-amber-100 px-1 rounded ml-1">
              cd backend && python -m ichthyosis_curator --serve
            </code>
          </p>
        </div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-6xl mb-4">{"\u{1f52c}"}</p>
        <h2 className="text-xl font-bold text-slate-800 mb-2">
          まだキュレーション記事がありません
        </h2>
        <p className="text-slate-500 max-w-md mx-auto">
          初回のキュレーションを実行してください:
        </p>
        <code className="bg-slate-100 px-3 py-1.5 rounded text-sm mt-3 inline-block">
          cd backend && python -m ichthyosis_curator --verbose
        </code>
      </div>
    );
  }

  return (
    <div>
      {/* Search */}
      <div className="mb-6">
        <SearchBar />
      </div>

      {/* Digest Header */}
      <DigestHeader date={latestDate} articleCount={articles.length} />

      {/* Category Filter */}
      <div className="mb-6">
        <CategoryFilter
          selected={selectedCategory}
          onSelect={setSelectedCategory}
          counts={categoryCounts}
        />
      </div>

      {/* Articles */}
      <div className="space-y-4">
        {filteredArticles.map((article) => (
          <ArticleCard key={article.id} article={article} />
        ))}
      </div>

      {filteredArticles.length === 0 && (
        <p className="text-center text-slate-500 py-10">
          このカテゴリの記事はありません。
        </p>
      )}

      {/* Recent Digests */}
      {digests.length > 1 && (
        <div className="mt-10 pt-6 border-t border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            最近のダイジェスト
          </h3>
          <div className="flex flex-wrap gap-2">
            {digests.slice(1, 8).map((d) => (
              <a
                key={d.date}
                href={`/archive?date=${d.date}`}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-100 transition"
              >
                {d.date}
                <span className="text-slate-400 ml-1">
                  ({d.article_count})
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
