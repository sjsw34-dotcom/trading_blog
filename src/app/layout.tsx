import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const SITE_URL =
  process.env.NEXT_PUBLIC_BASE_URL || "https://kjusik.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "주식 리포트 — 매일 한국/미국 시장 브리핑",
    template: "%s | 주식 리포트",
  },
  description:
    "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트를 자동 생성합니다. 상승/하락 종목, 테마 분석, 공시 정리.",
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: "주식 리포트",
    url: SITE_URL,
    title: "주식 리포트 — 매일 한국/미국 시장 브리핑",
    description:
      "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트. 상승/하락 종목, 테마 분석, 공시 정리.",
    images: [
      {
        url: `${SITE_URL}/og-image.jpeg`,
        width: 1200,
        height: 630,
        alt: "주식 리포트 — 매일 한국/미국 시장 브리핑",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "주식 리포트 — 매일 한국/미국 시장 브리핑",
    description:
      "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트. 상승/하락 종목, 테마 분석, 공시 정리.",
    images: [`${SITE_URL}/og-image.jpeg`],
  },
  alternates: {
    canonical: SITE_URL,
    types: {
      "application/rss+xml": `${SITE_URL}/feed.xml`,
    },
  },
  verification: {
    google: "SAED8Au21djQHjpHjhoulJhnE9jWh-YBEoIwfcQgMTM",
  },
  robots: {
    index: true,
    follow: true,
    "max-snippet": -1,
    "max-image-preview": "large",
    "max-video-preview": -1,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <div className="min-h-screen">
          {/* HTS 스타일 상단 헤더 */}
          <header className="bg-header-bg text-white shadow-lg">
            <div className="max-w-[1280px] mx-auto px-4 py-3 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2 text-xl font-bold text-white hover:opacity-90 transition-opacity">
                <span className="inline-flex items-center justify-center w-8 h-8 bg-accent rounded text-white text-sm font-black">SR</span>
                주식 리포트
              </a>
              <nav className="text-sm text-blue-200">
              </nav>
            </div>
            {/* HTS 틱커 바 */}
            <div className="bg-primary/80 border-t border-white/10">
              <div className="max-w-[1280px] mx-auto px-4 py-1.5 flex items-center gap-6 text-xs text-blue-100 overflow-x-auto">
                <span className="whitespace-nowrap">KOSPI</span>
                <span className="whitespace-nowrap">KOSDAQ</span>
                <span className="whitespace-nowrap">S&P 500</span>
                <span className="whitespace-nowrap">NASDAQ</span>
                <span className="whitespace-nowrap">USD/KRW</span>
              </div>
            </div>
          </header>

          <main className="max-w-[1280px] mx-auto px-4 py-8">{children}</main>

          <footer className="bg-header-bg border-t-4 border-accent mt-16">
            <div className="max-w-[1280px] mx-auto px-4 py-6 text-center text-xs text-blue-200 leading-relaxed">
              본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, 특정
              종목의 매수·매도를 권유하지 않습니다. 투자 판단의 최종 책임은
              투자자 본인에게 있습니다.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
