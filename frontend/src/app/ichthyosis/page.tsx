import type { Metadata } from "next";
import { FeaturedProducts } from "@/components/RelatedProducts";

export const metadata: Metadata = {
  title: "魚鱗癬紅皮症とは｜症状・原因・治療法をわかりやすく解説 | IchthyoCure",
  description:
    "魚鱗癬紅皮症（ぎょりんせんこうひしょう）の症状、原因、種類、診断方法、治療法、日常ケアについて中学生でも理解できるようにわかりやすく解説します。",
  keywords: [
    "魚鱗癬紅皮症",
    "魚鱗癬",
    "ichthyosis",
    "紅皮症",
    "皮膚疾患",
    "遺伝性皮膚疾患",
    "保湿ケア",
  ],
};

export default function IchthyosisPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "MedicalCondition",
    name: "魚鱗癬紅皮症",
    alternateName: ["Ichthyosis with Erythroderma", "Ichthyotic Erythroderma"],
    description:
      "魚鱗癬紅皮症は、皮膚が魚のうろこのように硬くなり、全身が赤くなる遺伝性の皮膚疾患です。",
    associatedAnatomy: { "@type": "AnatomicalStructure", name: "皮膚" },
    cause: {
      "@type": "MedicalCause",
      name: "遺伝子変異による皮膚バリア機能の異常",
    },
    possibleTreatment: [
      { "@type": "MedicalTherapy", name: "保湿療法" },
      { "@type": "MedicalTherapy", name: "レチノイド療法" },
    ],
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
          {"\u{1f9ec}"} 魚鱗癬紅皮症とは
        </h1>
        <p className="text-slate-500 mt-2">
          症状・原因・治療法をわかりやすく解説します
        </p>
      </div>

      {/* 概要 */}
      <section className="mb-8">
        <div className="bg-teal-50 border border-teal-200 rounded-xl p-6">
          <h2 className="text-lg font-bold text-teal-800 mb-3">
            魚鱗癬紅皮症ってどんな病気？
          </h2>
          <p className="text-slate-700 leading-relaxed">
            魚鱗癬紅皮症（ぎょりんせん こうひしょう）は、皮膚が魚のうろこのように硬く厚くなり、
            全身が赤くなる（紅皮症）遺伝性の皮膚疾患です。皮膚の一番外側にある「角質層」がうまく
            作れなくなることで、肌のバリア機能が低下します。
          </p>
          <p className="text-slate-700 leading-relaxed mt-3">
            日本では指定難病に認定されており、患者数は非常に少ない希少疾患です。
            完治は難しいですが、適切なケアで症状をコントロールすることができます。
          </p>
        </div>
      </section>

      {/* 症状 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1f4cb}"} 主な症状
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            {
              title: "皮膚の鱗屑（りんせつ）",
              desc: "皮膚が魚のうろこのように白〜褐色の薄い膜状に剥がれ落ちます",
            },
            {
              title: "全身の発赤（紅皮症）",
              desc: "皮膚全体が赤くなります。かゆみを伴うこともあります",
            },
            {
              title: "皮膚の乾燥・ひび割れ",
              desc: "水分を保てず極度に乾燥し、ひび割れが生じることがあります",
            },
            {
              title: "皮膚の硬化",
              desc: "関節部分などの皮膚が硬くなり、動きが制限されることも",
            },
            {
              title: "体温調節の困難",
              desc: "汗をうまくかけないため、体温調節が難しくなることがあります",
            },
            {
              title: "感染リスクの増加",
              desc: "皮膚バリアが弱いため、細菌感染のリスクが高まります",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="bg-white border border-slate-200 rounded-lg p-4"
            >
              <h3 className="font-semibold text-slate-800 text-sm mb-1">
                {item.title}
              </h3>
              <p className="text-xs text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 原因 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1f9ec}"} 原因
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <p className="text-slate-700 leading-relaxed">
            魚鱗癬紅皮症の原因は<strong>遺伝子の変異</strong>です。
            皮膚のバリア機能を維持するために必要なタンパク質（ケラチン、トランスグルタミナーゼなど）
            を作る遺伝子に異常があるために起こります。
          </p>
          <p className="text-slate-700 leading-relaxed mt-3">
            多くの場合、<strong>常染色体劣性遺伝</strong>（両親ともに変異遺伝子を持っている場合に
            子どもに発症する）で受け継がれます。両親が保因者（キャリア）であっても
            症状が出ないケースがほとんどです。
          </p>
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              {"\u{1f4a1}"}{" "}
              <strong>ポイント</strong>：魚鱗癬は「うつる病気」ではありません。
              遺伝子の違いによるもので、接触や空気感染で他の人に広がることはありません。
            </p>
          </div>
        </div>
      </section>

      {/* 種類 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1f4d1}"} 魚鱗癬の主な種類
        </h2>
        <div className="space-y-3">
          {[
            {
              name: "尋常性魚鱗癬",
              desc: "最も一般的。軽度の鱗屑と乾燥が特徴。フィラグリン遺伝子の変異が原因。",
              severity: "軽度〜中等度",
            },
            {
              name: "X連鎖性魚鱗癬",
              desc: "男性に多い。褐色の大きな鱗屑が特徴。ステロイドスルファターゼ欠損が原因。",
              severity: "中等度",
            },
            {
              name: "葉状魚鱗癬",
              desc: "広範囲の紅皮症と鱗屑。コロジオン児として出生することがある。",
              severity: "重度",
            },
            {
              name: "道化師様魚鱗癬",
              desc: "最も重症。出生時に厚い角質の板で覆われる。集中治療が必要。",
              severity: "最重度",
            },
            {
              name: "先天性魚鱗癬様紅皮症（CIE）",
              desc: "全身の紅皮症と細かい白い鱗屑。魚鱗癬紅皮症の代表的タイプ。",
              severity: "重度",
            },
          ].map((type) => (
            <div
              key={type.name}
              className="bg-white border border-slate-200 rounded-lg p-4 flex items-start gap-3"
            >
              <div className="flex-1">
                <h3 className="font-semibold text-slate-800">{type.name}</h3>
                <p className="text-sm text-slate-600 mt-1">{type.desc}</p>
              </div>
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-1 rounded whitespace-nowrap">
                {type.severity}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 診断 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1fa7a}"} 診断方法
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <ul className="space-y-3 text-slate-700">
            <li className="flex items-start gap-2">
              <span className="text-teal-600 font-bold mt-0.5">1.</span>
              <span>
                <strong>視診</strong>：皮膚科医が皮膚の状態を目で確認します
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-600 font-bold mt-0.5">2.</span>
              <span>
                <strong>家族歴の確認</strong>
                ：ご家族に同様の症状がある方がいないか確認します
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-600 font-bold mt-0.5">3.</span>
              <span>
                <strong>皮膚生検</strong>
                ：皮膚の一部を採取して顕微鏡で角質の状態を調べます
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-teal-600 font-bold mt-0.5">4.</span>
              <span>
                <strong>遺伝子検査</strong>
                ：原因遺伝子の変異を特定します（確定診断に重要）
              </span>
            </li>
          </ul>
        </div>
      </section>

      {/* 治療法 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1f48a}"} 治療法
        </h2>
        <p className="text-slate-600 mb-4">
          現在、魚鱗癬を完全に治す治療法はありませんが、症状を和らげる方法があります。
        </p>
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-bold text-blue-800 mb-2">
              {"\u{1f9f4}"} 保湿療法（最も基本的）
            </h3>
            <p className="text-sm text-slate-700">
              ワセリン、ヘパリン類似物質、セラミド配合クリームなどで皮膚の水分を保ちます。
              入浴後すぐに塗ることが効果的です。詳しくは
              <a
                href="/moisturizer-guide"
                className="text-teal-600 hover:underline font-medium"
              >
                保湿剤の選び方ガイド
              </a>
              をご覧ください。
            </p>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-5">
            <h3 className="font-bold text-purple-800 mb-2">
              {"\u{1f48a}"} レチノイド療法
            </h3>
            <p className="text-sm text-slate-700">
              ビタミンA誘導体（エトレチナートなど）の内服薬。角質の異常な増殖を抑えます。
              副作用があるため、医師の管理下で使用します。
            </p>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-5">
            <h3 className="font-bold text-green-800 mb-2">
              {"\u{1f6c1}"} 入浴療法
            </h3>
            <p className="text-sm text-slate-700">
              ぬるめのお湯にゆっくり浸かり、角質を柔らかくしてから優しく除去します。
              入浴剤（コロイドオートミールなど）の使用も効果的です。
            </p>
          </div>
          <div className="bg-gradient-to-br from-amber-50 to-yellow-50 border border-amber-200 rounded-xl p-5">
            <h3 className="font-bold text-amber-800 mb-2">
              {"\u{1f52c}"} 遺伝子治療・新薬（研究段階）
            </h3>
            <p className="text-sm text-slate-700">
              遺伝子治療や新しい外用薬（TMB-001など）の臨床試験が進んでいます。
              将来的に根本的な治療が可能になるかもしれません。最新情報は
              <a href="/" className="text-teal-600 hover:underline font-medium">
                IchthyoCureのトップページ
              </a>
              でキュレーションしています。
            </p>
          </div>
        </div>
      </section>

      {/* 日常のケア */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          {"\u{1f3e0}"} 日常のケアポイント
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <ul className="space-y-3 text-sm text-slate-700">
            {[
              "入浴後5分以内に保湿剤を塗る（皮膚が湿っているうちに）",
              "部屋の湿度を50〜60%に保つ（加湿器の活用）",
              "肌着は綿100%など刺激の少ない素材を選ぶ",
              "爪を短く切り、掻きむしりによる傷を防ぐ",
              "夏は日焼け対策、冬は乾燥対策を徹底する",
              "ストレスをためない工夫（ストレスで悪化することがある）",
              "定期的に皮膚科を受診し、状態をチェックする",
            ].map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-teal-500">{"\u{2714}\u{fe0f}"}</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 医療費助成 */}
      <section className="mb-8">
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <h2 className="text-lg font-bold text-amber-800 mb-3">
            {"\u{1f4b0}"} 医療費の助成制度
          </h2>
          <p className="text-sm text-slate-700 leading-relaxed">
            魚鱗癬は厚生労働省の「指定難病」に認定されています（指定難病160）。
            医療費助成制度を利用すると、自己負担額が軽減されます。
            お住まいの地域の保健所や難病相談支援センターに相談してみてください。
          </p>
        </div>
      </section>

      {/* 免責事項 */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-6">
        <p className="text-xs text-slate-500">
          {"\u{26a0}\u{fe0f}"}{" "}
          このページの情報は一般的な医学情報の提供を目的としています。
          個別の診断・治療については必ず主治医にご相談ください。
        </p>
      </div>

      {/* アフィリエイト */}
      <FeaturedProducts />
    </div>
  );
}
