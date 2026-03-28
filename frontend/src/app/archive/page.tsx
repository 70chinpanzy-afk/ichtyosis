"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  Article,
  Category,
  Region,
  DigestSummary,
  getDigests,
  getDigestByDate,
  getArticleRegion,
  searchArticles,
} from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import CategoryFilter from "@/components/CategoryFilter";
import DigestHeader from "@/components/DigestHeader";
import RegionTabs from "@/components/RegionTabs";
import SearchBar from "@/components/SearchBar";

function ArchiveContent() {
  const searchParams = useSearchParams();
  const dateParam = searchParams.get("date");
  const queryParam = searchParams.get("q");

  const [digests, setDigests] = useState<DigestSummary[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState<string>("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        if (queryParam) {
          const results = await searchArticles(queryParam);
          setArticles(results);
          setCurrentDate(`「${queryParam}」の検索結果`);
        } else {
          const digestList = await getDigests(90);
          setDigests(digestList);

          const targetDate = dateParam || (digestList.length > 0 ? digestList[0].date : "");
          if (targetDate) {
            const dateArticles = await getDigestByDate(targetDate);
            setArticles(dateArticles);
            setCurrentDate(targetDate);
          }
        }
      } catch {
        setArticles([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [dateParam, queryParam]);

  const handleDateChange = async (date: string) => {
    setLoading(true);
    setSelectedCategory(null);
    setSelectedRegion(null);
    try {
      const dateArticles = await getDigestByDate(date);
      setArticles(dateArticles);
      setCurrentDate(date);
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  // Region filtering
  const regionFilteredArticles = selectedRegion
    ? articles.filter((a) => getArticleRegion(a) === selectedRegion)
    : articles;

  // Category filtering
  const filteredArticles = selectedCategory
    ? regionFilteredArticles.filter((a) => a.category === selectedCategory)
    : regionFilteredArticles;

  // Region counts
  const regionCounts = { japan: 0, international: 0 };
  for (const a of articles) {
    const r = getArticleRegion(a);
    regionCounts[r]++;
  }

  // Category counts
  const categoryCounts: Record<string, number> = {};
  for (const a of regionFilteredArticles) {
    if (a.category) {
      categoryCounts[a.category] = (categoryCounts[a.category] || 0) + 1;
    }
  }

  return (
    <div>
      <div className="mb-6">
        <SearchBar />
      </div>

      <h2 className="text-2xl font-bold text-slate-800 mb-4">
        {queryParam ? `「${queryParam}」の検索結果` : "アーカイブ"}
      </h2>

      {!queryParam && digests.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {digests.map((d) => (
            <button
              key={d.date}
              onClick={() => handleDateChange(d.date)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                currentDate === d.date
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
              }`}
            >
              {d.date}
              <span
                className={
                  currentDate === d.date ? "text-blue-200 ml-1" : "text-slate-400 ml-1"
                }
              >
                ({d.article_count})
              </span>
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : articles.length > 0 ? (
        <>
          {!queryParam && (
            <DigestHeader date={currentDate} articleCount={articles.length} />
          )}

          {/* Region Tabs */}
          <RegionTabs
            selected={selectedRegion}
            onSelect={(region) => {
              setSelectedRegion(region);
              setSelectedCategory(null);
            }}
            counts={regionCounts}
          />

          <div className="mb-6">
            <CategoryFilter
              selected={selectedCategory}
              onSelect={setSelectedCategory}
              counts={categoryCounts}
            />
          </div>

          <div className="space-y-4">
            {filteredArticles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          {filteredArticles.length === 0 && (
            <p className="text-center text-slate-500 py-10">
              該当する記事はありません。
            </p>
          )}
        </>
      ) : (
        <p className="text-center text-slate-500 py-10">
          {queryParam
            ? "検索結果が見つかりませんでした。"
            : "この日のダイジェストはありません。"}
        </p>
      )}
    </div>
  );
}

export default function ArchivePage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      }
    >
      <ArchiveContent />
    </Suspense>
  );
}
