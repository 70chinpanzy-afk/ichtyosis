import type { Metadata } from "next";
import fs from "fs";
import path from "path";
import ArticleContent from "./ArticleContent";

type Props = {
  params: Promise<{ id: string }>;
};

async function getArticleData(id: string) {
  try {
    const filePath = path.join(process.cwd(), `public/data/articles/${id}.json`);
    if (fs.existsSync(filePath)) {
      const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      return data;
    }
  } catch {
    // ファイルが存在しない場合
  }
  return null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const article = await getArticleData(id);

  if (!article) {
    return { title: "記事が見つかりません" };
  }

  const title = article.title_ja || article.original_title || "記事詳細";
  const description = article.summary_ja
    ? article.summary_ja.substring(0, 160)
    : "魚鱗癬紅皮症に関する医療情報";

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "article",
      publishedTime: article.published_date || undefined,
    },
    twitter: {
      card: "summary",
      title,
      description,
    },
  };
}

export default async function ArticleDetailPage({ params }: Props) {
  const { id } = await params;
  const articleId = Number(id);

  // 記事用のJSON-LD構造化データ
  const article = await getArticleData(id);
  const jsonLd = article
    ? {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        headline: article.title_ja || article.original_title,
        description: article.summary_ja?.substring(0, 300),
        datePublished: article.published_date || article.digest_date,
        dateModified: article.digest_date,
        publisher: {
          "@type": "Organization",
          name: "IchthyoCure",
        },
        about: {
          "@type": "MedicalCondition",
          name: "魚鱗癬紅皮症",
          alternateName: "Ichthyosis Erythroderma",
        },
      }
    : null;

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      <ArticleContent id={articleId} />
    </>
  );
}
