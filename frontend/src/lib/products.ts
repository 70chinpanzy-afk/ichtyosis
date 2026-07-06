/**
 * 魚鱗癬紅皮症の患者さん・ご家族に役立つ厳選商品
 * Amazon評価が高く、実際に皮膚疾患の方に使用されている商品のみ掲載
 */

export const ASSOCIATE_ID = "peachpap-22";

export type Product = {
  asin: string;
  title: string;
  description: string;
  category: "moisturizer" | "skincare" | "bath" | "book" | "supplement";
  tags: string[]; // 記事カテゴリとのマッチング用
  imageKeyword: string; // 検索用キーワード
};

// 厳選商品リスト
export const PRODUCTS: Product[] = [
  // === 保湿剤 ===
  {
    asin: "B000FQUNMK",
    title: "ヒルドイドソフト軟膏（ヘパリン類似物質）",
    description: "皮膚科で最も処方される保湿剤の市販版。肌の水分保持力を高めます。",
    category: "moisturizer",
    tags: ["ケア・対処法", "体験談・対処法", "新薬・治療法", "関連疾患からの知見"],
    imageKeyword: "ヒルドイド",
  },
  {
    asin: "B01N7GXAXK",
    title: "HPクリーム（ヘパリン類似物質配合）",
    description: "乾燥性皮膚に。ヘパリン類似物質が肌の保湿をサポートします。",
    category: "moisturizer",
    tags: ["ケア・対処法", "体験談・対処法", "関連疾患からの知見"],
    imageKeyword: "HPクリーム",
  },
  {
    asin: "B000YZM70E",
    title: "ワセリンHG（高品質白色ワセリン）",
    description: "皮膚バリアの保護に。刺激が少なく敏感肌にも安心して使えます。",
    category: "moisturizer",
    tags: ["ケア・対処法", "体験談・対処法", "新薬・治療法"],
    imageKeyword: "ワセリンHG",
  },
  {
    asin: "B07GXCPWC5",
    title: "セタフィル モイスチャライジングクリーム",
    description: "世界中の皮膚科医が推奨。低刺激で乾燥肌・敏感肌に幅広く使われています。",
    category: "moisturizer",
    tags: ["ケア・対処法", "体験談・対処法", "関連疾患からの知見"],
    imageKeyword: "セタフィル",
  },
  // === スキンケア ===
  {
    asin: "B07D7R5CZN",
    title: "キュレル 潤浸保湿フェイスクリーム",
    description: "セラミド配合。肌のバリア機能を助け、乾燥による肌荒れを防ぎます。",
    category: "skincare",
    tags: ["ケア・対処法", "体験談・対処法", "関連疾患からの知見"],
    imageKeyword: "キュレル",
  },
  {
    asin: "B08RMRXW8Z",
    title: "ミノン全身保湿ミルク",
    description: "アミノ酸系保湿。全身に使える低刺激ミルクタイプの保湿剤です。",
    category: "skincare",
    tags: ["ケア・対処法", "体験談・対処法"],
    imageKeyword: "ミノン全身保湿",
  },
  // === 入浴関連 ===
  {
    asin: "B000FQR4JO",
    title: "コロイドオートミール入浴剤（Aveeno）",
    description: "オートミール由来の保湿成分が入浴中の肌を保護。欧米の皮膚科で推奨されています。",
    category: "bath",
    tags: ["ケア・対処法", "体験談・対処法", "関連疾患からの知見"],
    imageKeyword: "Aveeno 入浴剤",
  },
  // === 書籍 ===
  {
    asin: "4521748910",
    title: "あたらしい皮膚科学 第3版",
    description: "皮膚科の標準的な教科書。魚鱗癬を含む皮膚疾患の基礎知識を学べます。",
    category: "book",
    tags: ["研究論文", "新薬・治療法", "ニュース"],
    imageKeyword: "あたらしい皮膚科学",
  },
  {
    asin: "4260047159",
    title: "患者さんのための皮膚疾患ビジュアルブック",
    description: "皮膚疾患をわかりやすく解説。患者さんやご家族の理解に役立ちます。",
    category: "book",
    tags: ["研究論文", "ニュース"],
    imageKeyword: "皮膚疾患ビジュアルブック",
  },
];

/**
 * Amazonアフィリエイトリンクを生成
 */
export function getAmazonUrl(asin: string): string {
  return `https://www.amazon.co.jp/dp/${asin}?tag=${ASSOCIATE_ID}`;
}

/**
 * Amazon商品検索リンクを生成
 */
export function getAmazonSearchUrl(keyword: string): string {
  return `https://www.amazon.co.jp/s?k=${encodeURIComponent(keyword)}&tag=${ASSOCIATE_ID}`;
}

/**
 * 記事カテゴリに基づいて関連商品を返す
 */
export function getRelatedProducts(
  articleCategory: string,
  limit = 3
): Product[] {
  const matched = PRODUCTS.filter((p) => p.tags.includes(articleCategory));
  // マッチした中からランダムに選択（毎回同じにならないよう）
  const shuffled = [...matched].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, limit);
}

/**
 * カテゴリ別の商品ラベル
 */
export const CATEGORY_LABELS: Record<Product["category"], string> = {
  moisturizer: "保湿剤",
  skincare: "スキンケア",
  bath: "入浴ケア",
  book: "参考書籍",
  supplement: "サプリメント",
};
