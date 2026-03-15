import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IchthyoCure - 魚鱗癬紅皮症 デイリーニュース",
  description:
    "魚鱗癬紅皮症（Ichthyosis Erythroderma）に関する最新の医学情報・治療法・ケア情報を毎日キュレーションしてお届けします。",
  openGraph: {
    title: "IchthyoCure - 魚鱗癬紅皮症 デイリーニュース",
    description:
      "魚鱗癬紅皮症に関する最新の医学情報を毎日キュレーション。新薬、治療法、ケア対策、研究論文を世界中から収集し日本語でお届けします。",
    type: "website",
    locale: "ja_JP",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-slate-50 min-h-screen`}
      >
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-4xl mx-auto px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-2">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80">
              <span className="text-2xl">{"\u{1f52c}"}</span>
              <div>
                <h1 className="text-lg font-bold text-slate-800 leading-tight">
                  IchthyoCure
                </h1>
                <p className="text-xs text-slate-500 hidden sm:block">
                  魚鱗癬紅皮症 デイリーニュース
                </p>
              </div>
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link
                href="/"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                最新
              </Link>
              <Link
                href="/archive"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                アーカイブ
              </Link>
              <Link
                href="/about"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                About
              </Link>
            </nav>
          </div>
        </header>

        {/* Main */}
        <main className="max-w-4xl mx-auto px-4 py-6">{children}</main>

        {/* Footer */}
        <footer className="bg-white border-t border-slate-200 mt-12">
          <div className="max-w-4xl mx-auto px-4 py-6 text-center text-sm text-slate-500">
            <p>
              IchthyoCure - 魚鱗癬紅皮症に関する医学情報を毎日キュレーション
            </p>
            <p className="mt-1">
              情報は参考目的です。治療に関しては必ず専門医にご相談ください。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
