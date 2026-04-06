"use client";

import { useState } from "react";
import { FeaturedProducts } from "@/components/RelatedProducts";

type FaqItem = {
  question: string;
  answer: string;
};

const FAQ_SECTIONS: { title: string; items: FaqItem[] }[] = [
  {
    title: "病気について",
    items: [
      {
        question: "魚鱗癬紅皮症とは何ですか？",
        answer:
          "魚鱗癬紅皮症（ぎょりんせん こうひしょう）は、遺伝子の変異により皮膚のバリア機能がうまく働かず、皮膚が魚のうろこのように硬くなり、全身が赤くなる皮膚疾患です。厚生労働省の指定難病に認定されています。詳しくは「魚鱗癬紅皮症とは」のページをご覧ください。",
      },
      {
        question: "遺伝しますか？",
        answer:
          "はい、魚鱗癬は遺伝性の疾患です。多くの場合「常染色体劣性遺伝」で、両親がともに変異遺伝子を持っている（保因者）場合に、4分の1の確率で子どもに発症します。両親自身には症状が出ないことがほとんどです。遺伝カウンセリングを受けることをおすすめします。",
      },
      {
        question: "治る病気ですか？",
        answer:
          "現時点では完治させる治療法はありません。しかし、保湿ケアやレチノイド療法などで症状を大幅に改善できます。また、遺伝子治療や新薬の研究が進んでおり、将来的には根本的な治療が可能になるかもしれません。",
      },
      {
        question: "人にうつりますか？",
        answer:
          "いいえ、魚鱗癬は遺伝子の違いによる疾患であり、接触や空気感染で他の人にうつることは絶対にありません。安心して日常生活を送ってください。",
      },
      {
        question: "どの科を受診すべきですか？",
        answer:
          "まずは皮膚科を受診してください。可能であれば、遺伝性皮膚疾患に詳しい大学病院や専門施設がおすすめです。難病診療連携拠点病院に相談することもできます。",
      },
    ],
  },
  {
    title: "日常のケア",
    items: [
      {
        question: "保湿剤はどのくらいの頻度で塗るべきですか？",
        answer:
          "最低でも1日2回（朝と入浴後）は塗りましょう。入浴後は5分以内に塗ることが重要です。日中に乾燥を感じたら追加で塗り直してください。詳しくは「保湿剤の選び方ガイド」をご覧ください。",
      },
      {
        question: "入浴で気をつけることは？",
        answer:
          "お湯の温度は38〜40度のぬるめに設定しましょう。熱いお湯は皮脂を奪い乾燥を悪化させます。入浴時間は15〜20分程度にし、石鹸は低刺激のものを泡立てて優しく洗います。入浴後はタオルで押さえるように拭き、すぐに保湿剤を塗りましょう。",
      },
      {
        question: "子どもの魚鱗癬のケアで気をつけることは？",
        answer:
          "子どもの皮膚は薄くデリケートです。保湿剤はワセリンなど低刺激なものから始め、刺激がなければヘパリン類似物質へ。尿素配合は刺激が強いので避けましょう。また、学校の先生に病気について説明しておくと安心です。プールの授業の後は必ず保湿ケアをしましょう。",
      },
      {
        question: "夏と冬でケアは変わりますか？",
        answer:
          "はい。冬は空気が乾燥するため保湿を強化し、加湿器の使用がおすすめです。夏は汗をかきにくいため体温調節に注意が必要です。日焼け対策も重要ですが、日焼け止めが刺激になる場合は帽子や長袖で対応しましょう。",
      },
      {
        question: "食事で気をつけることはありますか？",
        answer:
          "特定の食事療法で魚鱗癬が治るという医学的根拠はありません。ただし、ビタミンA、ビタミンD、オメガ3脂肪酸は皮膚の健康維持に役立ちます。バランスの良い食事を心がけ、水分をしっかり摂ることが大切です。",
      },
    ],
  },
  {
    title: "治療・制度・サポート",
    items: [
      {
        question: "最新の治療法はありますか？",
        answer:
          "遺伝子治療の研究が進んでおり、一部の魚鱗癬タイプでは臨床試験が始まっています。また、TMB-001というセレチノイド外用薬の第III相試験が進行中です。IchthyoCureでは最新の研究情報を毎日キュレーションしてお届けしています。",
      },
      {
        question: "医療費の助成制度はありますか？",
        answer:
          "はい、魚鱗癬は厚生労働省の指定難病（160番）です。「特定医療費（指定難病）受給者証」を取得すると、医療費の自己負担額が軽減されます。申請はお住まいの都道府県の保健所で行えます。また、障害者総合支援法による日常生活用具の給付も受けられる場合があります。",
      },
      {
        question: "仕事や学校生活での工夫は？",
        answer:
          "デスクの近くに加湿器を置く、こまめに保湿剤を塗り直す、綿の手袋をして作業するなどの工夫が有効です。周囲の理解を得るために、信頼できる人に病気について話すことも大切です。職場の場合、産業医に相談して配慮を求めることもできます。",
      },
      {
        question: "このサイトの情報は信頼できますか？",
        answer:
          "IchthyoCureはPubMed（米国国立医学図書館の医学文献データベース）やClinicalTrials.govの公式データをAIで要約・キュレーションしています。ただし、AIによる自動処理のため誤りが含まれる可能性があります。治療に関する判断は必ず主治医にご相談ください。",
      },
      {
        question: "IchthyoCureとは何ですか？",
        answer:
          "IchthyoCureは、魚鱗癬紅皮症に関する最新の医学情報を毎日AIでキュレーションしてお届けする情報サイトです。PubMedの研究論文、臨床試験情報、ケア方法など、患者さんやご家族に役立つ情報を日本語でわかりやすくまとめています。",
      },
    ],
  },
];

export default function FaqContent() {
  const [openIndex, setOpenIndex] = useState<string | null>(null);

  const toggleItem = (key: string) => {
    setOpenIndex(openIndex === key ? null : key);
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-8">
        <a href="/" className="text-sm text-teal-600 hover:underline">
          &larr; トップに戻る
        </a>
        <h1 className="text-2xl font-bold text-slate-800 mt-4">
          {"\u{2753}"} よくある質問（FAQ）
        </h1>
        <p className="text-slate-500 mt-2">
          魚鱗癬紅皮症に関するよくある質問にお答えします
        </p>
      </div>

      {/* FAQ セクション */}
      <div className="space-y-8">
        {FAQ_SECTIONS.map((section) => (
          <div key={section.title}>
            <h2 className="text-lg font-bold text-slate-700 mb-3 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-teal-500 rounded-full" />
              {section.title}
            </h2>
            <div className="space-y-2">
              {section.items.map((item, i) => {
                const key = `${section.title}-${i}`;
                const isOpen = openIndex === key;
                return (
                  <div
                    key={key}
                    className="bg-white border border-slate-200 rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() => toggleItem(key)}
                      className="w-full text-left px-5 py-4 flex items-center justify-between gap-3 hover:bg-slate-50 transition"
                    >
                      <span className="text-sm font-medium text-slate-800">
                        {item.question}
                      </span>
                      <span
                        className={`text-slate-400 transition-transform ${
                          isOpen ? "rotate-180" : ""
                        }`}
                      >
                        {"\u{25bc}"}
                      </span>
                    </button>
                    {isOpen && (
                      <div className="px-5 pb-4">
                        <p className="text-sm text-slate-600 leading-relaxed">
                          {item.answer}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 関連ページリンク */}
      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <a
          href="/ichthyosis"
          className="block bg-teal-50 border border-teal-200 rounded-xl p-4 hover:bg-teal-100 transition"
        >
          <h3 className="font-bold text-teal-800 text-sm">
            {"\u{1f9ec}"} 魚鱗癬紅皮症とは
          </h3>
          <p className="text-xs text-slate-600 mt-1">
            症状・原因・治療法の詳しい解説
          </p>
        </a>
        <a
          href="/moisturizer-guide"
          className="block bg-blue-50 border border-blue-200 rounded-xl p-4 hover:bg-blue-100 transition"
        >
          <h3 className="font-bold text-blue-800 text-sm">
            {"\u{1f9f4}"} 保湿剤の選び方ガイド
          </h3>
          <p className="text-xs text-slate-600 mt-1">
            種類・塗り方・症状別おすすめ
          </p>
        </a>
      </div>

      {/* 免責 */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mt-6">
        <p className="text-xs text-amber-800">
          {"\u{26a0}\u{fe0f}"}{" "}
          このページの情報は一般的な知識の提供を目的としています。
          個別の症状や治療については必ず主治医にご相談ください。
        </p>
      </div>

      <FeaturedProducts />
    </div>
  );
}
