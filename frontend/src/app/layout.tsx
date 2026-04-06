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

const SITE_URL = "https://ichtyosis.vercel.app";
const SITE_NAME = "IchthyoCure";
const SITE_DESCRIPTION =
  "魚鱗癬紅皮症（先天性魚鱗癬様紅皮症・層板状魚鱗癬）に関する最新の研究・治療法・薬品情報・スキンケア方法を毎日AIがキュレーション。患者さんとご家族のための医療情報サイトです。";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "IchthyoCure - 魚鱗癬紅皮症の最新医療情報キュレーション",
    template: "%s | IchthyoCure",
  },
  description: SITE_DESCRIPTION,
  keywords: [
    "魚鱗癬",
    "魚鱗癬紅皮症",
    "先天性魚鱗癬様紅皮症",
    "層板状魚鱗癬",
    "ichthyosis",
    "ichthyosis erythroderma",
    "皮膚疾患",
    "希少疾患",
    "スキンケア",
    "保湿剤",
    "遺伝子治療",
    "治療法",
    "臨床試験",
  ],
  openGraph: {
    title: "IchthyoCure - 魚鱗癬紅皮症の最新医療情報",
    description: SITE_DESCRIPTION,
    type: "website",
    locale: "ja_JP",
    siteName: SITE_NAME,
    url: SITE_URL,
  },
  twitter: {
    card: "summary",
    title: "IchthyoCure - 魚鱗癬紅皮症の最新医療情報",
    description: SITE_DESCRIPTION,
  },
  alternates: {
    canonical: SITE_URL,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "IchthyoCure",
              alternateName: "イクチオキュア",
              url: "https://ichtyosis.vercel.app",
              description: SITE_DESCRIPTION,
              publisher: {
                "@type": "Organization",
                name: "IchthyoCure",
              },
              potentialAction: {
                "@type": "SearchAction",
                target: "https://ichtyosis.vercel.app/archive?q={search_term_string}",
                "query-input": "required name=search_term_string",
              },
            }),
          }}
        />
      </head>
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
                  魚鱗癬紅皮症の最新医療情報
                </p>
              </div>
            </Link>
            <nav className="flex flex-wrap gap-3 text-sm">
              <Link
                href="/"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                最新
              </Link>
              <Link
                href="/ichthyosis"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                疾患解説
              </Link>
              <Link
                href="/moisturizer-guide"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                保湿ガイド
              </Link>
              <Link
                href="/faq"
                className="text-slate-600 hover:text-blue-600 transition"
              >
                FAQ
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
              IchthyoCure - 魚鱗癬紅皮症の最新情報を毎日お届け
            </p>
            <p className="mt-1">
              AIによる自動キュレーションです。治療に関する判断は必ず主治医にご相談ください。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
