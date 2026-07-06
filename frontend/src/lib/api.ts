/**
 * API クライアント
 *
 * 2つのモードで動作:
 * - ローカル開発: NEXT_PUBLIC_API_URL が設定されている場合、FastAPIバックエンドに接続
 * - Vercel本番: 静的JSONファイル (/data/) から読み込み
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

/** 静的JSONモード: API_URLが未設定（= Vercelデプロイ時） */
const IS_STATIC = !API_BASE;

export interface DigestSummary {
  date: string;
  article_count: number;
}

export type Region = "japan" | "international";

export interface DrugInfo {
  drug_name: string;
  ingredients: string;
  description: string;
}

export interface Article {
  id: number;
  digest_date: string;
  source: string;
  source_id: string;
  original_title: string | null;
  title_ja: string | null;
  summary_ja: string | null;
  category: string | null;
  region: Region | null;
  relevance_score: number | null;
  url: string | null;
  published_date: string | null;
  curation_reasoning: string | null;
  drugs_json: string | null;
  patient_insight: string | null;
  created_at: string | null;
}

/** drugs_json文字列をDrugInfo配列にパース */
export function parseDrugs(drugsJson: string | null | undefined): DrugInfo[] {
  if (!drugsJson) return [];
  try {
    const parsed = JSON.parse(drugsJson);
    if (Array.isArray(parsed)) return parsed;
  } catch {
    // パース失敗
  }
  return [];
}

export type Category =
  | "新薬・治療法"
  | "研究論文"
  | "ケア・対処法"
  | "体験談・対処法"
  | "関連疾患からの知見"
  | "ニュース";

export const CATEGORIES: Category[] = [
  "新薬・治療法",
  "研究論文",
  "ケア・対処法",
  "体験談・対処法",
  "関連疾患からの知見",
  "ニュース",
];

export const CATEGORY_CONFIG: Record<
  Category,
  { emoji: string; color: string; bgColor: string }
> = {
  "新薬・治療法": {
    emoji: "\u{1f48a}",
    color: "text-red-700",
    bgColor: "bg-red-50 border-red-200",
  },
  "研究論文": {
    emoji: "\u{1f4c4}",
    color: "text-blue-700",
    bgColor: "bg-blue-50 border-blue-200",
  },
  "ケア・対処法": {
    emoji: "\u{1f9f4}",
    color: "text-green-700",
    bgColor: "bg-green-50 border-green-200",
  },
  "体験談・対処法": {
    emoji: "\u{1f4ac}",
    color: "text-amber-700",
    bgColor: "bg-amber-50 border-amber-200",
  },
  "関連疾患からの知見": {
    emoji: "\u{1f517}",
    color: "text-purple-700",
    bgColor: "bg-purple-50 border-purple-200",
  },
  "ニュース": {
    emoji: "\u{1f4f0}",
    color: "text-orange-700",
    bgColor: "bg-orange-50 border-orange-200",
  },
};

export const REGION_CONFIG: Record<
  Region,
  { label: string; emoji: string }
> = {
  japan: { label: "日本", emoji: "\u{1f1ef}\u{1f1f5}" },
  international: { label: "海外", emoji: "\u{1f30d}" },
};

/** 記事のregionを判定（regionフィールドがない場合はsourceから推定） */
export function getArticleRegion(article: Article): Region {
  if (article.region) return article.region;
  const japaneseSources = [
    "nikkei", "日経", "日本経済新聞",
    "yomiuri", "読売",
    "asahi", "朝日",
    "mainichi", "毎日",
    "sankei", "産経",
    "nhk", "NHK",
    "toyo keizai", "東洋経済",
    "diamond", "ダイヤモンド",
    "itmedia", "ITmedia",
    "impress", "Impress",
    "yahoo", "Yahoo",
  ];
  const sourceLower = (article.source || "").toLowerCase();
  const titleLower = (article.original_title || article.title_ja || "").toLowerCase();
  for (const s of japaneseSources) {
    if (sourceLower.includes(s.toLowerCase()) || titleLower.includes(s.toLowerCase())) {
      return "japan";
    }
  }
  // タイトルが日本語主体なら日本ニュースと推定
  const jaRegex = /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]/;
  if (article.original_title && jaRegex.test(article.original_title)) {
    return "japan";
  }
  return "international";
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    next: { revalidate: 300 }, // 5分キャッシュ
  });
  if (!res.ok) {
    throw new Error(`Fetch Error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ===== API Functions =====

export async function getDigests(limit = 30): Promise<DigestSummary[]> {
  if (IS_STATIC) {
    const all = await fetchJson<DigestSummary[]>("/data/digests.json");
    return all.slice(0, limit);
  }
  return fetchJson<DigestSummary[]>(`${API_BASE}/api/digests?limit=${limit}`);
}

export async function getDigestByDate(date: string): Promise<Article[]> {
  if (IS_STATIC) {
    return fetchJson<Article[]>(`/data/digests/${date}.json`);
  }
  return fetchJson<Article[]>(`${API_BASE}/api/digests/${date}`);
}

export async function getArticle(id: number): Promise<Article> {
  if (IS_STATIC) {
    return fetchJson<Article>(`/data/articles/${id}.json`);
  }
  return fetchJson<Article>(`${API_BASE}/api/articles/${id}`);
}

export async function searchArticles(
  query: string,
  limit = 50
): Promise<Article[]> {
  if (IS_STATIC) {
    // 静的モードでは全digestsからクライアント側検索
    const digests = await getDigests(365);
    const results: Article[] = [];
    const q = query.toLowerCase();

    for (const d of digests) {
      if (results.length >= limit) break;
      try {
        const articles = await getDigestByDate(d.date);
        for (const a of articles) {
          if (results.length >= limit) break;
          const searchable = [
            a.title_ja,
            a.summary_ja,
            a.original_title,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
          if (searchable.includes(q)) {
            results.push(a);
          }
        }
      } catch {
        // 日付のJSONがない場合はスキップ
      }
    }
    return results;
  }
  return fetchJson<Article[]>(
    `${API_BASE}/api/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}
