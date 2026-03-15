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
            IchthyoCureは、魚鱗癬紅皮症（Ichthyosis
            Erythroderma）に関する最新の医学情報を、世界中から毎日自動的にキュレーションし、日本語で分かりやすくお届けするサービスです。
          </p>
          <p className="text-slate-600 leading-relaxed mt-3">
            この疾患と向き合うご家族や患者様が、最新の治療法やケア方法、研究の進展を見逃すことなく把握できるよう支援することを目的としています。
          </p>
        </section>

        {/* About the Disease */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            魚鱗癬紅皮症とは
          </h2>
          <p className="text-slate-600 leading-relaxed">
            魚鱗癬紅皮症は、皮膚の角化異常を特徴とする希少な遺伝性皮膚疾患です。皮膚のバリア機能に影響を与え、広範囲にわたる鱗屑（りんせつ）や紅斑が見られます。
          </p>
          <p className="text-slate-600 leading-relaxed mt-3">
            先天性魚鱗癬様紅皮症や層板状魚鱗癬など、いくつかのサブタイプがあり、TGM1、ABCA12、ALOX12Bなどの遺伝子変異が関与することが知られています。
          </p>
        </section>

        {/* Information Sources */}
        <section className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            情報ソース
          </h2>
          <p className="text-slate-600 leading-relaxed mb-4">
            本サイトは、以下の信頼性の高い情報源から毎日自動的に情報を収集しています：
          </p>
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <span className="text-blue-500 font-bold text-lg leading-tight">
                {"\u{1f4c4}"}
              </span>
              <div>
                <strong className="text-slate-700">PubMed</strong>
                <p className="text-sm text-slate-500">
                  米国国立医学図書館が運営する世界最大の医学論文データベース
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-500 font-bold text-lg leading-tight">
                {"\u{1f9ea}"}
              </span>
              <div>
                <strong className="text-slate-700">ClinicalTrials.gov</strong>
                <p className="text-sm text-slate-500">
                  世界中の臨床試験を登録・公開しているデータベース
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-purple-500 font-bold text-lg leading-tight">
                {"\u{1f4f0}"}
              </span>
              <div>
                <strong className="text-slate-700">Google News</strong>
                <p className="text-sm text-slate-500">
                  世界中のニュースメディアから関連記事を収集（英語・日本語）
                </p>
              </div>
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
                毎朝、PubMed・ClinicalTrials.gov・ニュースサイトから魚鱗癬に関連する最新情報を自動収集
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                2
              </span>
              <p>
                AIが関連性を評価し、スコアリング・カテゴリ分類を実施
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                3
              </span>
              <p>英語の論文やニュースを日本語に翻訳・要約</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="bg-blue-100 text-blue-700 rounded-full h-7 w-7 flex items-center justify-center text-sm font-bold shrink-0">
                4
              </span>
              <p>
                キュレーション結果をこのサイトに掲載し、LINE通知でもお届け
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
              <strong>ケア・対処法</strong> - スキンケア、保湿、日常生活のアドバイス
            </li>
            <li>
              {"\u{1f517}"}{" "}
              <strong>関連疾患からの知見</strong> -
              アトピー等で魚鱗癬にも応用可能な情報
            </li>
            <li>
              {"\u{1f4f0}"}{" "}
              <strong>ニュース</strong> - 患者会、支援制度、メディア報道
            </li>
          </ul>
        </section>

        {/* Disclaimer */}
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-amber-900 mb-2">
            免責事項
          </h2>
          <p className="text-sm text-amber-800 leading-relaxed">
            本サイトの情報はAIによる自動キュレーションであり、医学的なアドバイスを提供するものではありません。治療方針の決定には必ず担当医や専門家にご相談ください。情報の正確性については最大限の努力を払っていますが、完全性を保証するものではありません。
          </p>
        </section>
      </div>
    </div>
  );
}
