import type { Metadata } from "next";
import { FeaturedProducts } from "@/components/RelatedProducts";
import { PRODUCTS, getAmazonUrl } from "@/lib/products";

export const metadata: Metadata = {
  title: "保湿剤の選び方ガイド｜魚鱗癬の方に | IchthyoCure",
  description:
    "魚鱗癬・乾燥肌の方向けに、ワセリン・ヘパリン類似物質・セラミドなど保湿剤の種類と選び方、正しい塗り方をわかりやすく解説します。",
  keywords: [
    "保湿剤",
    "魚鱗癬",
    "ワセリン",
    "ヘパリン類似物質",
    "セラミド",
    "乾燥肌",
    "スキンケア",
  ],
};

const moisturizerTypes = [
  {
    name: "ワセリン系",
    desc: "皮膚の表面に油の膜を作り、水分の蒸発を防ぎます。刺激がほとんどなく、最も安全に使える保湿剤です。",
    pros: "低刺激、安価、赤ちゃんにも使える",
    cons: "ベタつきがある、水分を与える力は弱い",
    when: "皮膚が荒れてヒリヒリするとき、他の保湿剤が合わないとき",
    product: PRODUCTS.find((p) => p.asin === "B000YZM70E"),
  },
  {
    name: "ヘパリン類似物質",
    desc: "皮膚の水分保持力を高め、血行を促進します。皮膚科で最も多く処方される保湿剤の成分です。",
    pros: "高い保湿力、血行促進、塗りやすい",
    cons: "出血しやすい部位には不向き",
    when: "日常的な保湿ケア、乾燥がひどいとき",
    product: PRODUCTS.find((p) => p.asin === "B000FQUNMK"),
  },
  {
    name: "セラミド配合",
    desc: "皮膚のバリア機能を構成するセラミドを補います。魚鱗癬で不足しがちな成分を直接補えます。",
    pros: "バリア機能の補強、肌なじみが良い",
    cons: "やや高価",
    when: "肌荒れ・バリア機能の低下を感じるとき",
    product: PRODUCTS.find((p) => p.asin === "B07D7R5CZN"),
  },
  {
    name: "尿素配合",
    desc: "角質を柔らかくし、水分を引き寄せる効果があります。硬くなった角質のケアに適しています。",
    pros: "角質軟化、保水力が高い",
    cons: "傷やひび割れに塗るとしみる、刺激がやや強い",
    when: "角質が厚くなっている部位、かかと・ひじ",
    product: null,
  },
];

export default function MoisturizerGuidePage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "魚鱗癬の方のための保湿剤の選び方ガイド",
    description:
      "魚鱗癬・乾燥肌の方向けに保湿剤の種類と選び方を解説",
    author: { "@type": "Organization", name: "IchthyoCure" },
    publisher: { "@type": "Organization", name: "IchthyoCure" },
    mainEntityOfPage: "https://ichtyosis.vercel.app/moisturizer-guide",
  };

  return (
    <div className="max-w-3xl mx-auto">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ヘッダー */}
      <div className="mb-8">
        <a href="/" className="text-sm text-teal-600 hover:underline">
          &larr; トップに戻る
        </a>
        <h1 className="text-2xl font-bold text-slate-800 mt-4">
          {"\u{1f9f4}"} 保湿剤の選び方ガイド
        </h1>
        <p className="text-slate-500 mt-2">
          魚鱗癬・乾燥肌の方に向けた保湿剤の種類と正しい使い方
        </p>
      </div>

      {/* なぜ保湿が重要か */}
      <section className="mb-8">
        <div className="bg-teal-50 border border-teal-200 rounded-xl p-6">
          <h2 className="text-lg font-bold text-teal-800 mb-3">
            なぜ保湿がこんなに大切なの？
          </h2>
          <p className="text-slate-700 leading-relaxed">
            魚鱗癬の方の皮膚は、バリア機能を作るタンパク質がうまく働かないため、
            水分がどんどん蒸発してしまいます。健康な皮膚と比べて
            <strong>2〜3倍のスピード</strong>で水分が失われるという研究もあります。
          </p>
          <p className="text-slate-700 leading-relaxed mt-3">
            保湿剤は「失われる水分を補い、蒸発を防ぐ」という最も基本的な治療法です。
            薬ではありませんが、<strong>毎日の保湿ケアが症状改善の土台</strong>になります。
          </p>
        </div>
      </section>

      {/* 保湿剤の種類 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">
          {"\u{1f4d1}"} 保湿剤の種類と特徴
        </h2>
        <div className="space-y-4">
          {moisturizerTypes.map((type) => (
            <div
              key={type.name}
              className="bg-white border border-slate-200 rounded-xl p-5"
            >
              <h3 className="text-lg font-bold text-slate-800 mb-2">
                {type.name}
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed mb-3">
                {type.desc}
              </p>
              <div className="grid gap-2 sm:grid-cols-3 text-xs mb-3">
                <div className="bg-green-50 border border-green-200 rounded-lg p-2">
                  <span className="font-semibold text-green-700">
                    {"\u{2b55}"} メリット
                  </span>
                  <p className="text-slate-600 mt-1">{type.pros}</p>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                  <span className="font-semibold text-red-700">
                    {"\u{26a0}\u{fe0f}"} 注意点
                  </span>
                  <p className="text-slate-600 mt-1">{type.cons}</p>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                  <span className="font-semibold text-blue-700">
                    {"\u{1f4a1}"} おすすめの場面
                  </span>
                  <p className="text-slate-600 mt-1">{type.when}</p>
                </div>
              </div>
              {type.product && (
                <a
                  href={getAmazonUrl(type.product.asin)}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-full text-xs font-bold hover:from-orange-600 hover:to-amber-600 transition shadow-sm"
                >
                  {"\u{1f6d2}"} {type.product.title}をAmazonで見る
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 症状別おすすめ */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">
          {"\u{1f3af}"} 症状別の選び方
        </h2>
        <div className="space-y-3">
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <h3 className="font-bold text-green-800 mb-2">
              軽度の乾燥（カサカサする程度）
            </h3>
            <p className="text-sm text-slate-700">
              ヘパリン類似物質やセラミド配合クリームで十分。朝晩2回の塗布でOK。
            </p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
            <h3 className="font-bold text-amber-800 mb-2">
              中等度の乾燥（鱗屑が目立つ）
            </h3>
            <p className="text-sm text-slate-700">
              ヘパリン類似物質で保湿 → 上からワセリンで蓋をする「二層塗り」が効果的。
              尿素配合クリームで角質を柔らかくするのもおすすめ。
            </p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <h3 className="font-bold text-red-800 mb-2">
              重度の乾燥（ひび割れ・痛みがある）
            </h3>
            <p className="text-sm text-slate-700">
              まずワセリンで皮膚を保護。ひび割れが治まったら徐々にヘパリン類似物質に切り替え。
              痛みが強い場合は皮膚科を受診してください。
            </p>
          </div>
        </div>
      </section>

      {/* 塗り方のポイント */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">
          {"\u{270b}"} 正しい塗り方
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <ol className="space-y-4 text-sm text-slate-700">
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center font-bold text-xs">
                1
              </span>
              <div>
                <strong>入浴後5分以内に塗る</strong>
                <p className="text-slate-500 mt-1">
                  皮膚が湿っているうちに塗ると、水分を閉じ込められます。タオルで軽く押さえるように拭いたらすぐ塗りましょう。
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center font-bold text-xs">
                2
              </span>
              <div>
                <strong>たっぷり使う</strong>
                <p className="text-slate-500 mt-1">
                  目安は「ティッシュが肌にくっつくくらい」。薄く塗りすぎると効果が半減します。
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center font-bold text-xs">
                3
              </span>
              <div>
                <strong>毛の流れに沿って塗る</strong>
                <p className="text-slate-500 mt-1">
                  ゴシゴシ擦らず、毛の流れに沿って優しく伸ばします。摩擦は皮膚を傷めます。
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center font-bold text-xs">
                4
              </span>
              <div>
                <strong>1日2〜3回塗り直す</strong>
                <p className="text-slate-500 mt-1">
                  朝・入浴後は必須。日中に乾燥を感じたら追加で塗りましょう。
                </p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      {/* 入浴ケア */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">
          {"\u{1f6c1}"} 入浴時のケア
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <ul className="space-y-2 text-sm text-slate-700">
            {[
              "お湯の温度は38〜40度のぬるめに（熱いお湯は皮脂を奪います）",
              "長湯しすぎない（15〜20分程度）",
              "石鹸は低刺激のものを使い、泡で優しく洗う",
              "コロイドオートミール入浴剤は角質を柔らかくする効果あり",
              "タオルでゴシゴシ拭かず、押し当てるように水分を取る",
              "入浴後すぐに保湿剤を塗る（5分以内がベスト）",
            ].map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-teal-500">{"\u{2714}\u{fe0f}"}</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 避けるべきこと */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">
          {"\u{274c}"} 避けるべきこと
        </h2>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <ul className="space-y-2 text-sm text-slate-700">
            {[
              "香料・着色料の多い化粧品やボディクリーム",
              "アルコール（エタノール）入りの化粧水",
              "ナイロンタオルやブラシでのこすり洗い",
              "角質を無理にはがすこと（感染のリスクが高まります）",
              "熱すぎるお風呂やサウナ",
              "乾燥した環境に長時間いること",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-red-500">{"\u{26d4}"}</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 免責事項 */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-6">
        <p className="text-xs text-slate-500">
          {"\u{26a0}\u{fe0f}"}{" "}
          このページの情報は一般的な知識の提供を目的としています。
          保湿剤の選択や使い方については、必ず主治医・皮膚科医にご相談ください。
        </p>
      </div>

      <FeaturedProducts />
    </div>
  );
}
