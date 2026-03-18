import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "주식 리포트 — 매일 한국/미국 시장 브리핑",
  description:
    "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트를 자동 생성합니다. 상승/하락 종목, 테마 분석, 수급, 공시 정리.",
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
          <header className="border-b border-border">
            <div className="max-w-[1280px] mx-auto px-4 py-4 flex items-center justify-between">
              <a href="/" className="text-xl font-bold text-white">
                📊 주식 리포트
              </a>
              <nav className="text-sm text-gray-400">
                매일 아침 7시 · 오후 4시 자동 발행
              </nav>
            </div>
          </header>
          <main className="max-w-[1280px] mx-auto px-4 py-8">{children}</main>
          <footer className="border-t border-border mt-16">
            <div className="max-w-[1280px] mx-auto px-4 py-6 text-center text-xs text-gray-500">
              ⚠️ 본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, 특정
              종목의 매수·매도를 권유하지 않습니다. 투자 판단의 최종 책임은
              투자자 본인에게 있습니다.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
