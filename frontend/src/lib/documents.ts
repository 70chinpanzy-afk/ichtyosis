/**
 * テーマページに紐づける「使える資料」の定義。
 *
 * 記事を読むだけでなく実際に使える道具（フォーム入力で組み上がる書類など）を
 * テーマキーごとに紐づけるためのマップ。新しい資料を追加する場合は
 * THEME_DOCUMENTS にエントリを足すだけで、該当テーマのページに自動的に
 * カードが表示される。
 */

export type DocumentResource = {
  /** 資料ページへのパス */
  href: string;
  /** カードの見出し */
  title: string;
  /** カードの説明文 */
  description: string;
};

export const THEME_DOCUMENTS: Record<string, DocumentResource[]> = {
  school: [
    {
      href: "/documents/school-letter",
      title: "学校・保育園への説明文メーカー",
      description:
        "担任の先生や養護教諭に渡す説明の手紙を、入力するだけで組み上げられます。",
    },
  ],
};
