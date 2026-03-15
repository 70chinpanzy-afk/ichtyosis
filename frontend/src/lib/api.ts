const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface DigestSummary {
  date: string;
  article_count: number;
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
  relevance_score: number | null;
  url: string | null;
  published_date: string | null;
  curation_reasoning: string | null;
  created_at: string | null;
}

export type Category =
  | "新薬・治療法"
  | "研究論文"
  | "ケア・対処法"
  | "関連疾患からの知見"
  | "ニュース";

export const CATEGORIES: Category[] = [
  "新薬・治療法",
  "研究論文",
  "ケア・対処法",
  "関連疾患からの知見",
  "ニュース",
];

export const CATEGORY_CONFIG: Record<
  Category,
  { emoji: string; color: string; bgColor: string }
> = {
  "新薬・治療法": {
    emoji: "\u{1f48a}",
    color: "text-blue-700",
    bgColor: "bg-blue-50 border-blue-200",
  },
  研究論文: {
    emoji: "\u{1f4c4}",
    color: "text-purple-700",
    bgColor: "bg-purple-50 border-purple-200",
  },
  "ケア・対処法": {
    emoji: "\u{1f9f4}",
    color: "text-green-700",
    bgColor: "bg-green-50 border-green-200",
  },
  関連疾患からの知見: {
    emoji: "\u{1f517}",
    color: "text-orange-700",
    bgColor: "bg-orange-50 border-orange-200",
  },
  ニュース: {
    emoji: "\u{1f4f0}",
    color: "text-gray-700",
    bgColor: "bg-gray-50 border-gray-200",
  },
};

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 300 }, // 5分キャッシュ
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getDigests(limit = 30): Promise<DigestSummary[]> {
  return fetchApi<DigestSummary[]>(`/api/digests?limit=${limit}`);
}

export async function getDigestByDate(date: string): Promise<Article[]> {
  return fetchApi<Article[]>(`/api/digests/${date}`);
}

export async function getArticle(id: number): Promise<Article> {
  return fetchApi<Article>(`/api/articles/${id}`);
}

export async function searchArticles(
  query: string,
  limit = 50
): Promise<Article[]> {
  return fetchApi<Article[]>(
    `/api/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}
