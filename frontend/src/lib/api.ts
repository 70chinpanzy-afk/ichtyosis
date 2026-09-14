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
  /** 申請・応募の締切や開催日（読み取れた場合のみ） */
  deadline?: string | null;
  /** 期限内に読者が動く必要があるか */
  action_required?: boolean | number | null;
  /** 公開URL用の安定ID。DBのidはCI実行ごとに振り直されるため使わない */
  slug?: string | null;
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
  | "制度・支援"
  | "ニュース";

export const CATEGORIES: Category[] = [
  "新薬・治療法",
  "研究論文",
  "ケア・対処法",
  "体験談・対処法",
  "関連疾患からの知見",
  "制度・支援",
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
  "制度・支援": {
    emoji: "\u{1f3e5}",
    color: "text-teal-700",
    bgColor: "bg-teal-50 border-teal-200",
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
export function getArticleRegion(
  article: Partial<Pick<Article, "region" | "source" | "original_title" | "title_ja">>
): Region {
  if (article.region) return article.region;

  const source = (article.source || "").toLowerCase();

  // ソースが分かっているものは、ソースで判定する。
  // 以前はタイトルに日本語が含まれるかで推測していたため、日本語の見出しを
  // 付けた海外ソース（FIRSTの実用ガイド等）が「日本」と表示されていた。
  const foreignSources = ["pubmed", "clinical_trials", "patient_org", "reddit", "inspire"];
  if (foreignSources.some((s) => source.includes(s))) return "international";

  const domesticSources = ["japan_support", "note_", "shouman", "nanbyou"];
  if (domesticSources.some((s) => source.includes(s))) return "japan";

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
  const titleLower = (article.original_title || article.title_ja || "").toLowerCase();
  for (const s of japaneseSources) {
    if (source.includes(s.toLowerCase()) || titleLower.includes(s.toLowerCase())) {
      return "japan";
    }
  }

  // ソースから判断できない場合のみ、タイトルの言語から推定する
  const jaRegex = /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]/;
  if (article.original_title && jaRegex.test(article.original_title)) {
    return "japan";
  }
  return "international";
}

/** 生のsource文字列は読者に見せない。人が読める名前に変換する */
export function sourceLabel(source: string | null | undefined): string {
  if (!source) return "その他";
  const [prefix, rest] = source.split(":");
  const map: Record<string, string> = {
    pubmed: "PubMed",
    clinical_trials: "臨床試験",
    reddit: "Reddit",
    google_news: rest || "ニュース",
    youtube: "YouTube",
    patient_blog: "note（患者・家族のブログ）",
    japan_support: rest || "制度・支援",
  };
  if (prefix === "patient_org") {
    return rest?.startsWith("FIRST") ? "FIRST（米国患者団体）" : rest || "患者団体";
  }
  return map[prefix] ?? source;
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

export async function getArticle(id: string | number): Promise<Article> {
  if (IS_STATIC) {
    return fetchJson<Article>(`/data/articles/${id}.json`);
  }
  return fetchJson<Article>(`${API_BASE}/api/articles/${id}`);
}

/** 記事の公開URLに使うID。slugがあれば優先し、無い古いデータはidにフォールバック */
export function articleHref(
  article: Partial<Pick<Article, "id" | "slug">>
): string {
  return `/article/${article.slug || article.id}`;
}

/**
 * ArticleCard コンポーネントが実際に使うフィールドだけを抜き出した型。
 * テーマ別ページ（ThemeArticle）など、Article型と完全には一致しないデータでも
 * 必要なフィールドさえ揃えればカードをそのまま再利用できるようにするための型。
 */
export type ArticleCardArticle = Pick<
  Article,
  "title_ja" | "summary_ja" | "category" | "relevance_score" | "url"
> &
  Partial<
    Pick<
      Article,
      "id" | "slug" | "source" | "original_title" | "published_date" | "region"
    >
  >;

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

// ===== テーマ別キュレーション =====

export type ThemeSummary = {
  key: string;
  label: string;
  count: number;
};

export type ThemeArticle = {
  slug: string;
  title_ja: string;
  summary_ja: string;
  category: string;
  relevance_score: number;
  date: string;
  url: string;
  source: string;
  original_title: string;
};

export async function getThemes(): Promise<ThemeSummary[]> {
  if (IS_STATIC) {
    return fetchJson<ThemeSummary[]>("/data/themes.json");
  }
  // テーマ集計用のAPIエンドポイントは未実装のため、静的モードと同じパスを使う
  return fetchJson<ThemeSummary[]>("/data/themes.json");
}

export async function getThemeArticles(key: string): Promise<ThemeArticle[]> {
  if (IS_STATIC) {
    return fetchJson<ThemeArticle[]>(`/data/themes/${key}.json`);
  }
  // テーマ集計用のAPIエンドポイントは未実装のため、静的モードと同じパスを使う
  return fetchJson<ThemeArticle[]>(`/data/themes/${key}.json`);
}
