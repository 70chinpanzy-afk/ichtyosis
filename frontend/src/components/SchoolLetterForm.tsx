"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

/**
 * 未入力の項目に差し込む下線プレースホルダ。
 * 手紙をそのまま印刷し、あとから手書きで埋められるようにする。
 */
const PLACEHOLDER = "___________";

type FormState = {
  childName: string;
  grade: string;
  diagnosis: string;
  guardianName: string;
  guardianRelation: string;
  phone: string;
  hospital: string;
  moisturizeNote: string;
  activityNote: string;
  freeNote: string;
  includeHeat: boolean;
  includeMoisturize: boolean;
  includeShedding: boolean;
  includeActivity: boolean;
};

const INITIAL_FORM: FormState = {
  childName: "",
  grade: "",
  diagnosis: "先天性魚鱗癬様紅皮症",
  guardianName: "",
  guardianRelation: "母",
  phone: "",
  hospital: "",
  moisturizeNote: "",
  activityNote: "",
  freeNote: "",
  includeHeat: true,
  includeMoisturize: true,
  includeShedding: true,
  includeActivity: true,
};

/** 空欄ならプレースホルダに置き換える */
function fill(value: string): string {
  const trimmed = value.trim();
  return trimmed ? trimmed : PLACEHOLDER;
}

/** 入力値から手紙本文を組み立てる */
function buildLetter(form: FormState): string {
  const blocks: string[] = [];

  blocks.push(
    `${fill(form.grade)}　${fill(form.childName)} の保護者です。\nいつもお世話になっております。`
  );

  blocks.push(
    `${fill(form.childName)}には「${fill(
      form.diagnosis
    )}」という生まれつきの皮膚の病気があります。\n学校生活で知っておいていただきたいことをまとめました。`
  );

  blocks.push(
    "■ うつる病気ではありません\nこの病気は感染するものではありません。触れても、同じタオルやプールを\n使っても、まわりの方にうつることはありません。生まれつきの体質による\nもので、本人の不衛生とは関係ありません。"
  );

  blocks.push(
    "■ 見た目について\n皮膚が乾燥してうろこのように見えたり、赤みが出たりします。\n本人はそれを気にしていることがあります。お友達から質問されたときは\n「生まれつきの皮膚の体質で、うつらないよ」と伝えていただけると助かります。"
  );

  if (form.includeHeat) {
    blocks.push(
      "■ 汗をかきにくく、体温が上がりやすいです\n皮膚が厚いため汗が外に出にくく、体温を下げるのが苦手です。気温の高い日や\n運動のあとに、体温がこもって具合が悪くなることがあります。\n次のような配慮をお願いできると助かります。\n・こまめな水分補給を許可していただく\n・暑い日は日陰や冷房のある場所で休ませていただく\n・保冷剤や冷却タオルの持ち込みを許可していただく\n・気温の高い時間帯の屋外活動は短めにしていただく"
    );
    blocks.push(
      "■ 具合が悪くなったときのサイン\nふらつき、強いだるさ、顔色が悪い、気分が悪いといった様子が出たら、\n涼しい場所で休ませ、水分をとらせてください。\n反応が鈍い、けいれんがある、皮膚が熱く乾いているといった様子があれば、\nすぐに救急要請と保護者への連絡をお願いします。"
    );
  }

  if (form.includeMoisturize) {
    blocks.push(
      `■ 保湿のケアについて\n乾燥すると皮膚が切れて痛みが出るため、日中も保湿剤を塗る必要があります。\n${fill(
        form.moisturizeNote
      )}`
    );
  }

  if (form.includeShedding) {
    blocks.push(
      "■ 皮膚がはがれ落ちることがあります\n乾いた皮膚が細かくはがれ落ちて、机や床に白い粉のようにたまることが\nあります。不潔なものではありません。本人が気にしないよう、さりげなく\n対応していただけると助かります。"
    );
  }

  if (form.includeActivity) {
    blocks.push(
      `■ 体育・プール・校外学習について\n${fill(form.activityNote)}`
    );
  }

  if (form.freeNote.trim()) {
    blocks.push(`■ そのほかお願いしたいこと\n${form.freeNote.trim()}`);
  }

  blocks.push(
    `■ 連絡先\n保護者　${fill(form.guardianName)}（${fill(
      form.guardianRelation
    )}）\n電話　${fill(form.phone)}\n主治医　${fill(form.hospital)}`
  );

  blocks.push("お手数をおかけしますが、どうぞよろしくお願いいたします。");

  return blocks.join("\n\n");
}

/** テキスト入力1行分（ラベル＋input） */
function TextField({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-800 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
      />
    </div>
  );
}

/** テキストエリア1つ分（ラベル＋textarea） */
function TextAreaField({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 mb-1"
      >
        {label}
      </label>
      <textarea
        id={id}
        rows={3}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-800 leading-relaxed focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
      />
    </div>
  );
}

/** チェックボックス1つ分。行全体をタップ範囲にしてスマホでも押しやすくする */
function CheckboxField({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 cursor-pointer hover:border-teal-300"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-5 w-5 flex-shrink-0 accent-teal-600"
      />
      <span>
        <span className="block text-sm font-semibold text-slate-800">
          {label}
        </span>
        <span className="block text-xs text-slate-500 mt-0.5">
          {description}
        </span>
      </span>
    </label>
  );
}

export default function SchoolLetterForm() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [copyStatus, setCopyStatus] = useState<"idle" | "success" | "error">(
    "idle"
  );

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // 入力のたびに手紙本文を再生成する（フォームの状態だけから導出、外部保存なし）
  const letterText = useMemo(() => buildLetter(form), [form]);

  async function handleCopy() {
    try {
      if (!navigator?.clipboard?.writeText) {
        throw new Error("clipboard API not available");
      }
      await navigator.clipboard.writeText(letterText);
      setCopyStatus("success");
    } catch {
      // 非対応ブラウザや権限拒否でもクラッシュさせない
      setCopyStatus("error");
    } finally {
      setTimeout(() => setCopyStatus("idle"), 2500);
    }
  }

  return (
    <div>
      {/* ヘッダー（印刷時は非表示） */}
      <div className="mb-6 print:hidden">
        <Link
          href="/themes/school"
          className="text-sm text-teal-600 hover:underline"
        >
          &larr; 学校・保育園のテーマに戻る
        </Link>
        <h1 className="text-2xl font-bold text-slate-800 mt-4">
          {"\u{1f4c4}"} 学校・保育園への説明文メーカー
        </h1>
        <p className="text-slate-500 mt-2 text-sm leading-relaxed">
          新学期に担任の先生や養護教諭へ渡す説明の手紙を、下のフォームに入力するだけで組み上げます。
          入力しなかった項目は下線のプレースホルダのまま出力されるので、印刷してから手書きで補ってもかまいません。
        </p>
      </div>

      {/* 注意書き（印刷時は非表示） */}
      <div className="mb-6 print:hidden space-y-3">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm font-semibold text-blue-800">
            {"\u{1f512}"}{" "}
            入力内容はこの画面の中だけで処理され、保存も送信もされません。
          </p>
          <p className="text-xs text-blue-700 mt-1 leading-relaxed">
            サーバーへの送信や自動保存は一切行っていません。タブを閉じたり再読み込みすると入力内容は消えます。共有のパソコンで使う場合も、この画面を閉じれば情報は残りません。
          </p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-sm text-amber-800 leading-relaxed">
            {"\u{26a0}\u{fe0f}"}{" "}
            医学的な内容（症状の程度や必要な配慮など）は、必ず主治医に確認のうえ記入してください。このページは医療上の助言ではありません。
          </p>
        </div>
      </div>

      {/* 入力フォーム（印刷時は非表示） */}
      <form
        onSubmit={(e) => e.preventDefault()}
        className="print:hidden space-y-6 mb-8"
      >
        <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-4">
          <h2 className="text-base font-bold text-slate-800">基本情報</h2>
          <TextField
            id="childName"
            label="お子さんのお名前"
            value={form.childName}
            onChange={(v) => update("childName", v)}
          />
          <TextField
            id="grade"
            label="学年・クラス"
            value={form.grade}
            onChange={(v) => update("grade", v)}
            placeholder="例: 1年2組"
          />
          <TextField
            id="diagnosis"
            label="診断名"
            value={form.diagnosis}
            onChange={(v) => update("diagnosis", v)}
          />
          <TextField
            id="guardianName"
            label="保護者のお名前"
            value={form.guardianName}
            onChange={(v) => update("guardianName", v)}
          />
          <TextField
            id="guardianRelation"
            label="続柄"
            value={form.guardianRelation}
            onChange={(v) => update("guardianRelation", v)}
          />
          <TextField
            id="phone"
            label="連絡先電話番号"
            value={form.phone}
            onChange={(v) => update("phone", v)}
          />
          <TextField
            id="hospital"
            label="主治医・医療機関名（任意）"
            value={form.hospital}
            onChange={(v) => update("hospital", v)}
          />
        </section>

        <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
          <h2 className="text-base font-bold text-slate-800">
            含めるセクション
          </h2>
          <CheckboxField
            id="includeHeat"
            label="汗をかきにくく体温が上がりやすいこと"
            description="具合が悪くなったときのサインも含めて出力します"
            checked={form.includeHeat}
            onChange={(v) => update("includeHeat", v)}
          />
          <CheckboxField
            id="includeMoisturize"
            label="保湿ケアについて"
            description="下の補足欄の内容が本文に入ります"
            checked={form.includeMoisturize}
            onChange={(v) => update("includeMoisturize", v)}
          />
          <CheckboxField
            id="includeShedding"
            label="皮膚がはがれ落ちること"
            description="定型文をそのまま出力します"
            checked={form.includeShedding}
            onChange={(v) => update("includeShedding", v)}
          />
          <CheckboxField
            id="includeActivity"
            label="体育・プール・校外学習について"
            description="下の補足欄の内容が本文に入ります"
            checked={form.includeActivity}
            onChange={(v) => update("includeActivity", v)}
          />
        </section>

        <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-4">
          <h2 className="text-base font-bold text-slate-800">補足の記入</h2>
          <TextAreaField
            id="moisturizeNote"
            label="保湿ケアについて（時間帯・場所・本人でできるか）"
            value={form.moisturizeNote}
            onChange={(v) => update("moisturizeNote", v)}
            placeholder="例: 中休みと昼休みに保健室で本人が塗ります。塗り忘れがないか一声かけていただけると助かります。"
          />
          <TextAreaField
            id="activityNote"
            label="体育・プール・校外学習について（主治医と相談のうえ記入）"
            value={form.activityNote}
            onChange={(v) => update("activityNote", v)}
            placeholder="例: プールは主治医の許可が出ています。日焼け止めの使用と、長時間の直射日光を避けることをお願いします。"
          />
          <TextAreaField
            id="freeNote"
            label="そのほか特に配慮してほしいこと"
            value={form.freeNote}
            onChange={(v) => update("freeNote", v)}
          />
        </section>
      </form>

      {/* プレビュー */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3 print:hidden">
          <h2 className="text-base font-bold text-slate-800">プレビュー</h2>
          <div className="flex items-center gap-2">
            {copyStatus === "success" && (
              <span className="text-xs font-medium text-teal-600">
                コピーしました
              </span>
            )}
            {copyStatus === "error" && (
              <span className="text-xs font-medium text-red-600">
                コピーに失敗しました
              </span>
            )}
            <button
              type="button"
              onClick={handleCopy}
              className="px-4 py-2.5 rounded-lg bg-teal-600 text-white text-sm font-bold hover:bg-teal-700 transition"
            >
              {"\u{1f4cb}"} コピーする
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="px-4 py-2.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-300 text-sm font-bold hover:bg-slate-200 transition"
            >
              {"\u{1f5a8}\u{fe0f}"} 印刷する
            </button>
          </div>
        </div>

        <pre className="whitespace-pre-wrap font-sans text-sm text-slate-800 leading-relaxed bg-white border border-slate-200 rounded-xl p-5 print:border-none print:rounded-none print:p-0 print:text-black">
          {letterText}
        </pre>
      </section>

      {/* 出典表記（印刷時は非表示） */}
      <div className="print:hidden bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-500 leading-relaxed">
        <p>
          この文面は、米国患者団体 FIRST (Foundation for Ichthyosis &amp;
          Related Skin Types) の School Resources および Overheating
          ガイドを参考に作成しました。
        </p>
        <p className="mt-1">
          原文:{" "}
          <a
            href="https://www.firstskinfoundation.org/school-resources"
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal-600 hover:underline"
          >
            https://www.firstskinfoundation.org/school-resources
          </a>
          <br />
          {"　　"}
          <a
            href="https://www.firstskinfoundation.org/overheating"
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal-600 hover:underline"
          >
            https://www.firstskinfoundation.org/overheating
          </a>
        </p>
        <p className="mt-2">
          医学的な内容は必ず主治医にご確認のうえ記入してください。このページは医療上の助言ではありません。
        </p>
      </div>
    </div>
  );
}
