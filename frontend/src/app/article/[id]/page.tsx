"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Article,
  Category,
  CATEGORY_CONFIG,
  getArticle,
  getArticleRegion,
  REGION_CONFIG,
  parseDrugs,
} from "@/lib/api";
import RelatedProducts from "@/components/RelatedProducts";

export default function ArticleDetailPage() {
  const params = useParams();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const id = Number(params.id);
        if (!isNaN(id)) {
          const data = await getArticle(id);
          setArticle(data);
        }
      } catch {
        setArticle(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!article) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-500">記事が見つかりませんでした。</p>
        <Link
          href="/"
          className="text-blue-600 hover:underline mt-4 inline-block"
        >
          トップへ戻る
        </Link>
      </div>
    );
  }

  const category = article.category as Category;
  const config = category ? CATEGORY_CONFIG[category] : null;
  const region = getArticleRegion(article);
  const regionConfig = REGION_CONFIG[region];
  const drugs = parseDrugs(article.drugs_json);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <nav className="text-sm text-slate-500 mb-6">
        <Link href="/" className="hover:text-blue-600">
          トップ
        </Link>
        <span className="mx-2">/</span>
        <Link
          href={`/archive?date=${article.digest_date}`}
          className="hover:text-blue-600"
        >
          {article.digest_date}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">記事詳細</span>
      </nav>

      {/* Category & Region Badge */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {config && (
          <span
            className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${config.bgColor} ${config.color}`}
          >
            {config.emoji} {category}
          </span>
        )}
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border bg-slate-50 border-slate-200 text-slate-600">
          {regionConfig.emoji} {regionConfig.label}
        </span>
        {article.relevance_score != null && (
          <span className="text-sm text-slate-500">
            重要度: {Math.round(article.relevance_score * 100)}%
          </span>
        )}
      </div>

      {/* Title */}
      <h1 className="text-2xl font-bold text-slate-800 leading-snug mb-2">
        {article.title_ja || article.original_title || "タイトルなし"}
      </h1>

      {article.title_ja && article.original_title && (
        <p className="text-sm text-slate-500 mb-4 italic">
          {article.original_title}
        </p>
      )}

      {/* Meta */}
      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500 mb-6 pb-6 border-b border-slate-200">
        <span>ソース: {article.source}</span>
        {article.published_date && (
          <span>発行日: {article.published_date}</span>
        )}
        <span>配信日: {article.digest_date}</span>
      </div>

      {/* Summary */}
      {article.summary_ja && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
            要約
          </h2>
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
              {article.summary_ja}
            </p>
          </div>
        </div>
      )}

      {/* Patient Insight */}
      {article.patient_insight && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
            患者さんへのポイント
          </h2>
          <div className="bg-sky-50 rounded-lg border border-sky-200 p-5">
            <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
              {article.patient_insight}
            </p>
          </div>
        </div>
      )}

      {/* Drugs */}
      {drugs.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
            関連する薬品・薬剤
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {drugs.map((drug, i) => (
              <div
                key={i}
                className="bg-teal-50 border border-teal-200 rounded-lg p-3"
              >
                <p className="text-sm font-medium text-teal-800">
                  {drug.drug_name}
                </p>
                {drug.ingredients && (
                  <p className="text-xs text-teal-600 mt-0.5">
                    {drug.ingredients}
                  </p>
                )}
                {drug.description && (
                  <p className="text-xs text-slate-600 mt-1">
                    {drug.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Curation Reasoning */}
      {article.curation_reasoning && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2">
            キュレーション理由
          </h2>
          <p className="text-sm text-slate-600 bg-slate-100 rounded-lg p-4">
            {article.curation_reasoning}
          </p>
        </div>
      )}

      {/* Link to original */}
      {article.url && (
        <div className="mt-8">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
          >
            原文を読む
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>
      )}

      {/* Related Products (Affiliate) */}
      <RelatedProducts
        articleCategory={article.category}
        drugs={drugs.map((d) => d.drug_name)}
      />

      {/* Disclaimer */}
      <div className="mt-10 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
        <p className="font-medium mb-1">ご注意</p>
        <p>
          この情報はAIによるキュレーションです。治療に関する判断は必ず主治医にご相談ください。
        </p>
      </div>
    </div>
  );
}
