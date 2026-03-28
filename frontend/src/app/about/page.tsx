export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-800 mb-6">
        Sales News Copilot について
      </h1>

      <div className="space-y-8">
        {/* Mission */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            このサイトの目的
          </h2>
          <p className="text-slate-600 leading-relaxed">
            Sales News Copilotは、営業パーソンが日々押さえておくべきニュースを、日本と海外に分けて毎日自動的にキュレーションし、分かりやすくお届けするサービスです。
          </p>
          <p className="text-slate-600 leading-relaxed mt-3">
            商談前の情報収集や、顧客との会話のきっかけ作りに活用いただけます。業界動向、テクノロジートレンド、経済・市場の動き、競合情報をまとめてチェックできます。
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
              <span>毎朝のニュースチェックを効率化したい営業パーソン</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>商談前に業界の最新動向を素早く把握したい方</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>海外の市場トレンドも日本語でキャッチアップしたい方</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">{"\u{2022}"}</span>
              <span>チームで共通のニュースソースを持ちたいセールスマネージャー</span>
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
                毎朝、国内外のニュースサイト・経済メディアから営業に関連する最新情報を自動収集
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                2
              </span>
              <p>
                AIが営業パーソンにとっての重要度を評価し、カテゴリ分類・日本/海外の振り分けを実施
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                3
              </span>
              <p>海外ニュースは日本語に翻訳・要約してお届け</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                4
              </span>
              <p>
                キュレーション結果をこのサイトに掲載し、毎日更新
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
              {"\u{1f4b9}"}{" "}
              <strong>経済・ビジネス</strong> - 景気動向、企業ニュース、マーケット情報、M&A
            </li>
            <li>
              {"\u{1f3db}\u{fe0f}"}{" "}
              <strong>政治・社会</strong> - 政策、法改正、社会問題など商談の話題になるニュース
            </li>
            <li>
              {"\u{1f4bb}"}{" "}
              <strong>テクノロジー</strong> - AI、DX、新サービスなど話題のテクノロジートピック
            </li>
            <li>
              {"\u{1f30d}"}{" "}
              <strong>国際</strong> - グローバル情勢、海外経済、地政学リスク
            </li>
            <li>
              {"\u{26bd}"}{" "}
              <strong>スポーツ・文化</strong> - スポーツ、エンタメ、文化など雑談に使える話題
            </li>
          </ul>
        </section>

        {/* Region */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            日本/海外ニュースの切り替え
          </h2>
          <p className="text-slate-600 leading-relaxed">
            各ページのタブで「日本」と「海外」のニュースを切り替えて表示できます。
          </p>
          <ul className="mt-3 space-y-2 text-slate-600">
            <li>
              {"\u{1f1ef}\u{1f1f5}"}{" "}
              <strong>日本ニュース</strong> - 国内メディアからの最新ビジネスニュース
            </li>
            <li>
              {"\u{1f30d}"}{" "}
              <strong>海外ニュース</strong> - グローバルメディアからの情報（日本語要約付き）
            </li>
          </ul>
        </section>

        {/* Disclaimer */}
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-amber-900 mb-2">
            免責事項
          </h2>
          <p className="text-sm text-amber-800 leading-relaxed">
            本サイトの情報はAIによる自動キュレーションであり、投資助言や商談上のアドバイスを提供するものではありません。重要な意思決定の際は必ず原文や公式情報をご確認ください。情報の正確性については最大限の努力を払っていますが、完全性を保証するものではありません。
          </p>
        </section>
      </div>
    </div>
  );
}
