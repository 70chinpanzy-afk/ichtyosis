import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = "https://ichtyosis.vercel.app";
  const entries: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/archive`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/themes`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  // 記事ページを動的に追加
  try {
    const res = await fetch(`${baseUrl}/data/digests.json`);
    if (res.ok) {
      const digests = await res.json();
      for (const digest of digests) {
        const articlesRes = await fetch(
          `${baseUrl}/data/digests/${digest.date}.json`
        );
        if (articlesRes.ok) {
          const articles = await articlesRes.json();
          for (const article of articles) {
            entries.push({
              url: `${baseUrl}/article/${article.slug || article.id}`,
              lastModified: new Date(),
              changeFrequency: "weekly",
              priority: 0.7,
            });
          }
        }
      }
    }
  } catch {
    // フェッチ失敗時はスキップ
  }

  // テーマ別ページを動的に追加（件数0のテーマも一覧ページとして存在するため含める）
  try {
    const themesRes = await fetch(`${baseUrl}/data/themes.json`);
    if (themesRes.ok) {
      const themes = await themesRes.json();
      for (const theme of themes) {
        entries.push({
          url: `${baseUrl}/themes/${theme.key}`,
          lastModified: new Date(),
          changeFrequency: "weekly",
          priority: 0.6,
        });
      }
    }
  } catch {
    // フェッチ失敗時はスキップ
  }

  return entries;
}
