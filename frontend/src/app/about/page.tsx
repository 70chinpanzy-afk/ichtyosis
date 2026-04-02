import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "IchthyoCureについて",
  description:
    "IchthyoCureは魚鱗癬紅皮症の最新研究・治療法・ケア情報を毎日自動キュレーションするサイトです。PubMed、Google News、Redditから情報を収集し、わかりやすい日本語でお届けします。",
  openGraph: {
    title: "IchthyoCureについて",
    description:
      "魚鱗癬紅皮症の最新医療情報を毎日お届け。患者さんとご家族のための情報サイトです。",
  },
};

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-800 mb-6">
        IchthyoCure について
      </h1>

      <div className="space-y-8">
        {/* Mission */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            このサイトの目的
          </h2>
          <p className="text-slate-600 leading-relaxed">
            IchthyoCureは、希少皮膚疾患「魚鱗癬紅皮症（Ichthyosis Erythroderma）」に関する最新の研究・治療法・ケア情報を、毎日自動的にキュレーションしてお届けするサイトです。
          </p>
          <p className="text-slate-600 leading-relaxed mt-3">
            患者さんご本人やご家族が、最新の医療情報を分かりやすい日本語で読めることを目指しています。
          </p>
        </section>

        {/* Who is it for */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            こんな方におすすめ
          </h2>
          <ul className="space-y-2 text-slate-600">
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>魚鱗癬紅皮症のお子様を持つ親御さん</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>魚鱗癬の治療・ケアに関する最新情報を探している方</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>海外の研究・臨床試験の情報を日本語で知りたい方</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>同じ疾患を持つ方々の体験談やケア方法を知りたい方</span>
            </li>
          </ul>
        </section>

        {/* How it works */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            仕組み
          </h2>
          <div className="space-y-3 text-slate-600">
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                1
              </span>
              <p>
                毎朝、PubMed（医学論文）、Google News、Reddit等から魚鱗癬に関連する最新情報を自動収集
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                2
              </span>
              <p>
                AIが関連性を評価し、カテゴリ分類・薬品情報の抽出を実施
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                3
              </span>
              <p>専門用語を分かりやすい日本語に噛み砕いて要約</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                4
              </span>
              <p>
                このサイトとLINEで毎日お届け
              </p>
            </div>
          </div>
        </section>

        {/* Categories */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            カテゴリについて
          </h2>
          <ul className="space-y-2 text-slate-600">
            <li>
              {"\u{1f48a}"}{" "}
              <strong>新薬・治療法</strong> - 新薬開発、臨床試験、承認情報、遺伝子治療
            </li>
            <li>
              {"\u{1f4c4}"}{" "}
              <strong>研究論文</strong> - 基礎研究、病態メカニズム、遺伝子解析
            </li>
            <li>
              {"\u{1f9f4}"}{" "}
              <strong>ケア・対処法</strong> - スキンケア、保湿剤、日常生活のアドバイス、患者の体験談
            </li>
            <li>
              {"\u{1f517}"}{" "}
              <strong>関連疾患からの知見</strong> - アトピー等の類似疾患から応用可能な治療法
            </li>
            <li>
              {"\u{1f4f0}"}{" "}
              <strong>ニュース</strong> - 患者会、支援制度、医療費助成、メディア報道
            </li>
          </ul>
        </section>

        {/* Disclaimer */}
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-amber-900 mb-2">
            免責事項
          </h2>
          <p className="text-sm text-amber-800 leading-relaxed">
            本サイトの情報はAIによる自動キュレーションであり、医療上のアドバイスを提供するものではありません。治療に関する判断は必ず主治医にご相談ください。情報の正確性については最大限の努力を払っていますが、完全性を保証するものではありません。
          </p>
        </section>
      </div>
    </div>
  );
}
