"use client";

import { useMemo } from "react";
import {
  getRelatedProducts,
  getAmazonUrl,
  getAmazonSearchUrl,
  CATEGORY_LABELS,
  PRODUCTS,
  type Product,
} from "@/lib/products";

const CATEGORY_EMOJI: Record<Product["category"], string> = {
  moisturizer: "\u{1f9f4}",
  skincare: "\u{2728}",
  bath: "\u{1f6c1}",
  book: "\u{1f4d6}",
  supplement: "\u{1f48a}",
};

const CATEGORY_GRADIENT: Record<Product["category"], string> = {
  moisturizer: "from-blue-50 to-cyan-50 border-blue-200 hover:border-blue-400",
  skincare: "from-purple-50 to-pink-50 border-purple-200 hover:border-purple-400",
  bath: "from-teal-50 to-emerald-50 border-teal-200 hover:border-teal-400",
  book: "from-amber-50 to-yellow-50 border-amber-200 hover:border-amber-400",
  supplement: "from-green-50 to-lime-50 border-green-200 hover:border-green-400",
};

/**
 * 記事詳細ページ用の関連商品（カテゴリマッチ）
 */
export default function RelatedProducts({
  articleCategory,
  drugs,
}: {
  articleCategory: string | null;
  drugs?: string[];
}) {
  const products = useMemo(
    () => getRelatedProducts(articleCategory || "", 3),
    [articleCategory]
  );

  if (products.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t border-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-slate-700">
          {"\u{1f31f}"} おすすめのケア用品・書籍
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
          PR
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {products.map((product) => (
          <ProductCard key={product.asin} product={product} />
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
              className="text-xs px-3 py-1.5 bg-orange-50 text-orange-700 border border-orange-200 rounded-full hover:bg-orange-100 hover:shadow-sm transition font-medium"
            >
              {"\u{1f50d}"} {drug} で検索
            </a>
          ))}
        </div>
      )}

      <p className="text-xs text-slate-400 mt-3">
        ※ Amazonアソシエイト・プログラムによるアフィリエイトリンクです。商品の購入は主治医にご相談の上ご判断ください。
      </p>
    </div>
  );
}

/**
 * トップページ用のおすすめ商品セクション（全商品から厳選表示）
 */
export function FeaturedProducts() {
  const featured = useMemo(() => {
    const picks: Product[] = [];
    const categories: Product["category"][] = ["moisturizer", "skincare", "bath", "book"];
    for (const cat of categories) {
      const item = PRODUCTS.find((p) => p.category === cat);
      if (item) picks.push(item);
    }
    return picks;
  }, []);

  return (
    <div className="mt-10 pt-8 border-t border-slate-200">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold text-slate-800">
          {"\u{1f31f}"} 皮膚科医も推奨するケア用品
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
          PR
        </span>
      </div>
      <p className="text-sm text-slate-500 mb-5">
        魚鱗癬・乾燥肌の方に実際に使われている高評価アイテムを厳選しました
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {featured.map((product) => (
          <ProductCard key={product.asin} product={product} />
        ))}
      </div>

      <div className="mt-5 text-center">
        <a
          href={getAmazonSearchUrl("魚鱗癬 保湿 スキンケア")}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-full hover:from-orange-600 hover:to-amber-600 transition shadow-md hover:shadow-lg text-sm font-bold"
        >
          Amazonでもっと見る →
        </a>
      </div>

      <p className="text-xs text-slate-400 mt-4 text-center">
        ※ Amazonアソシエイト・プログラムによるアフィリエイトリンクです。商品の購入は主治医にご相談の上ご判断ください。
      </p>
    </div>
  );
}

/**
 * 共通の商品カードコンポーネント
 */
function ProductCard({ product }: { product: Product }) {
  const gradient = CATEGORY_GRADIENT[product.category];

  return (
    <a
      href={getAmazonUrl(product.asin)}
      target="_blank"
      rel="noopener noreferrer sponsored"
      className={`block bg-gradient-to-br ${gradient} border rounded-xl p-5 hover:shadow-md transition-all duration-200 group`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">{CATEGORY_EMOJI[product.category]}</span>
        <span className="text-xs font-semibold text-slate-500 bg-white/70 px-2 py-0.5 rounded-full">
          {CATEGORY_LABELS[product.category]}
        </span>
      </div>

      <h3 className="text-sm font-bold text-slate-800 group-hover:text-blue-700 transition leading-snug mb-2">
        {product.title}
      </h3>

      <p className="text-xs text-slate-600 leading-relaxed mb-3">
        {product.description}
      </p>

      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-full text-xs font-bold shadow-sm group-hover:shadow-md group-hover:from-orange-600 group-hover:to-amber-600 transition-all">
        {"\u{1f6d2}"} Amazonで詳しく見る
      </span>
    </a>
  );
}
