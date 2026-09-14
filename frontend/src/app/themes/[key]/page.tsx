"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getThemes,
  getThemeArticles,
  ThemeSummary,
  ThemeArticle,
  ArticleCardArticle,
} from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import { THEME_DOCUMENTS } from "@/lib/documents";

/**
 * ThemeArticle を ArticleCard が期待する最小限の形に変換する。
 * ThemeArticle には source / region / id が存在しないため、
 * 地域バッジは判定材料がなく既定値（海外）になる点に注意。
 */
function toCardArticle(article: ThemeArticle): ArticleCardArticle {
  return {
    slug: article.slug,
    title_ja: article.title_ja,
    summary_ja: article.summary_ja,
    category: article.category,
    relevance_score: article.relevance_score,
    url: article.url,
    // ThemeArticleにはpublished_dateが無いため、集計時点のdateを流用する
    published_date: article.date,
    // 国内/海外バッジの判定に使う
    source: article.source,
    original_title: article.original_title,
  };
}

export default function ThemeDetailPage() {
  const params = useParams();
  const key = Array.isArray(params.key) ? params.key[0] : params.key;

  const [theme, setTheme] = useState<ThemeSummary | null>(null);
  const [articles, setArticles] = useState<ThemeArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    async function load() {
      if (!key) return;
      setLoading(true);
      setNotFound(false);
      try {
        // 存在するテーマキーかどうかをthemes.jsonの一覧で確認する
        const themes = await getThemes();
        const matched = themes.find((t) => t.key === key);
        if (!matched) {
          setNotFound(true);
          return;
        }
        setTheme(matched);
        const data = await getThemeArticles(key);
        setArticles(data);
      } catch {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [key]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (notFound || !theme) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-500">指定されたテーマが見つかりませんでした。</p>
        <Link
          href="/themes"
          className="text-blue-600 hover:underline mt-4 inline-block"
        >
          テーマ一覧に戻る
        </Link>
      </div>
    );
  }

  return (
    <div>
      <nav className="text-sm text-slate-500 mb-4">
        <Link href="/themes" className="hover:text-blue-600">
          テーマから探す
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">{theme.label}</span>
      </nav>

      <div className="flex items-baseline gap-3 mb-6">
        <h2 className="text-2xl font-bold text-slate-800">{theme.label}</h2>
        <span className="text-sm text-slate-500">{theme.count}件の記事</span>
      </div>

      {/* 使える資料（テーマキーに紐づく道具があれば記事一覧の上に表示） */}
      {(THEME_DOCUMENTS[theme.key] ?? []).length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-slate-500 mb-2">
            {"\u{1f9f0}"} 使える資料
          </h3>
          <div className="space-y-2">
            {THEME_DOCUMENTS[theme.key].map((doc) => (
              <Link
                key={doc.href}
                href={doc.href}
                className="block rounded-xl border border-teal-200 bg-teal-50 p-4 transition hover:border-teal-300 hover:shadow-md"
              >
                <p className="font-semibold text-teal-800">{doc.title}</p>
                <p className="text-sm text-teal-700 mt-1">
                  {doc.description}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {articles.length > 0 ? (
        <div className="space-y-4">
          {articles.map((article) => (
            <ArticleCard key={article.slug} article={toCardArticle(article)} />
          ))}
        </div>
      ) : (
        <p className="text-center text-slate-500 py-10">
          このテーマの情報はまだ集まっていません。
        </p>
      )}
    </div>
  );
}
