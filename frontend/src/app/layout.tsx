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
  title: "Sales News Copilot - 営業パーソンのためのニュースキュレーション",
  description:
    "営業パーソンが押さえておくべき最新ニュースを日本・海外に分けて毎日キュレーション。業界動向、テクノロジー、経済・市場情報をお届けします。",
  openGraph: {
    title: "Sales News Copilot - 営業パーソンのためのニュースキュレーション",
    description:
      "営業パーソンが押さえておくべき最新ニュースを毎日キュレーション。業界動向、テクノロジー、経済・市場、競合情報を日本・海外に分けてお届けします。",
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
              <span className="text-2xl">{"\u{1f4f0}"}</span>
              <div>
                <h1 className="text-lg font-bold text-slate-800 leading-tight">
                  Sales News Copilot
                </h1>
                <p className="text-xs text-slate-500 hidden sm:block">
                  営業パーソンのためのデイリーニュース
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
              Sales News Copilot - 営業パーソンが押さえるべきニュースを毎日キュレーション
            </p>
            <p className="mt-1">
              AIによる自動キュレーションです。投資判断等にはご自身でご確認ください。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
