"use client";

import { useMemo } from "react";
import {
  getRelatedProducts,
  getAmazonUrl,
  getAmazonSearchUrl,
  CATEGORY_LABELS,
  type Product,
} from "@/lib/products";

const CATEGORY_EMOJI: Record<Product["category"], string> = {
  moisturizer: "\u{1f9f4}",
  skincare: "\u{2728}",
  bath: "\u{1f6c1}",
  book: "\u{1f4d6}",
  supplement: "\u{1f48a}",
};

export default function RelatedProducts({
  articleCategory,
  drugs,
}: {
  articleCategory: string;
  drugs?: string[];
}) {
  const products = useMemo(
    () => getRelatedProducts(articleCategory, 3),
    [articleCategory]
  );

  if (products.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t border-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
          関連するケア用品・書籍
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
          PR（アフィリエイト広告を含みます）
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {products.map((product) => (
          <a
            key={product.asin}
            href={getAmazonUrl(product.asin)}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="block bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition group"
          >
            <div className="flex items-start gap-2 mb-2">
              <span className="text-lg">
                {CATEGORY_EMOJI[product.category]}
              </span>
              <span className="text-xs text-slate-400">
                {CATEGORY_LABELS[product.category]}
              </span>
            </div>
            <h3 className="text-sm font-medium text-slate-800 group-hover:text-blue-600 transition leading-snug mb-1">
              {product.title}
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              {product.description}
            </p>
            <span className="inline-flex items-center gap-1 mt-2 text-xs text-orange-600 font-medium">
              Amazonで見る →
            </span>
          </a>
        ))}
      </div>

      {/* 薬品名での検索リンク */}
      {drugs && drugs.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-xs text-slate-400 py-1">関連商品を探す:</span>
          {drugs.slice(0, 3).map((drug) => (
            <a
              key={drug}
              href={getAmazonSearchUrl(drug)}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="text-xs px-2 py-1 bg-orange-50 text-orange-700 border border-orange-200 rounded-full hover:bg-orange-100 transition"
            >
              {drug} で検索
            </a>
          ))}
        </div>
      )}

      <p className="text-xs text-slate-400 mt-3">
        ※ 上記はAmazonアソシエイト・プログラムによるアフィリエイトリンクです。商品の購入は主治医にご相談の上ご判断ください。
      </p>
    </div>
  );
}
