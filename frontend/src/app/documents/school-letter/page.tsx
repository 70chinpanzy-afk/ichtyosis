import type { Metadata } from "next";
import SchoolLetterForm from "@/components/SchoolLetterForm";

export const metadata: Metadata = {
  title: "学校・保育園への説明文メーカー",
  description:
    "魚鱗癬のお子さんについて、担任の先生や養護教諭に渡す説明の手紙をフォーム入力だけで組み上げられます。入力内容は画面の外に一切送信・保存されません。",
  keywords: [
    "魚鱗癬",
    "学校",
    "保育園",
    "説明文",
    "手紙",
    "配慮事項",
    "養護教諭",
  ],
};

export default function SchoolLetterPage() {
  return (
    <div className="max-w-3xl mx-auto print:max-w-none">
      <SchoolLetterForm />
    </div>
  );
}
