interface DigestHeaderProps {
  date: string;
  articleCount: number;
}

export default function DigestHeader({ date, articleCount }: DigestHeaderProps) {
  return (
    <div className="mb-6">
      <div className="flex items-baseline gap-3 mb-1">
        <h2 className="text-2xl font-bold text-slate-800">{date}</h2>
        <span className="text-sm text-slate-500">
          {articleCount}件の記事
        </span>
      </div>
      <div className="h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-green-500 rounded-full" />
    </div>
  );
}
