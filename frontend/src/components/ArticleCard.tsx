import Link from "next/link";
import { Article, Category, CATEGORY_CONFIG } from "@/lib/api";

interface ArticleCardProps {
  article: Article;
}

export default function ArticleCard({ article }: ArticleCardProps) {
  const category = article.category as Category;
  const config = category ? CATEGORY_CONFIG[category] : null;

  return (
    <div
      className={`rounded-lg border p-4 transition hover:shadow-md ${
        config ? config.bgColor : "bg-white border-slate-200"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          {config && <span className="text-lg">{config.emoji}</span>}
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              config ? config.color : "text-slate-600"
            } bg-white/60`}
          >
            {category || "その他"}
          </span>
        </div>
        {article.relevance_score != null && (
          <span className="text-xs text-slate-500 whitespace-nowrap">
            関連度: {Math.round(article.relevance_score * 100)}%
          </span>
        )}
      </div>

      <Link href={`/article/${article.id}`}>
        <h3 className="text-base font-semibold text-slate-800 hover:text-blue-600 transition leading-snug mb-2">
          {article.title_ja || article.original_title || "タイトルなし"}
        </h3>
      </Link>

      {article.summary_ja && (
        <p className="text-sm text-slate-600 leading-relaxed mb-3 line-clamp-3">
          {article.summary_ja}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{article.source}</span>
        <div className="flex items-center gap-3">
          {article.published_date && <span>{article.published_date}</span>}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-700 underline"
            >
              原文を読む
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
