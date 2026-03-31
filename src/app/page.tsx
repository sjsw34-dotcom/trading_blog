import { getLatestReports, getReportCount } from "@/lib/db";
import type { Metadata } from "next";

const SITE_URL =
  process.env.NEXT_PUBLIC_BASE_URL || "https://kjusik.com";
const TELEGRAM_CHANNEL = "https://t.me/kr_stock_daily";

export const metadata: Metadata = {
  title: "주식 리포트 — 매일 한국/미국 시장 브리핑",
  description:
    "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트. 상승/하락 종목, 테마 분석, 공시 자동 정리.",
};

// WebSite + SearchAction JSON-LD for Google Sitelinks Search
const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "주식 리포트",
  url: SITE_URL,
};

// ISR — 60초마다 갱신 (매 요청 DB 쿼리 방지)
export const revalidate = 60;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function typeLabel(type: string): { text: string; color: string; icon: string } {
  if (type === "morning") {
    return { text: "아침 브리핑", color: "bg-stock-down text-white", icon: "🇺🇸" };
  }
  return { text: "마감 리포트", color: "bg-accent text-white", icon: "🇰🇷" };
}

interface PageProps {
  searchParams: { page?: string };
}

const PAGE_SIZE = 20;

export default async function HomePage({ searchParams }: PageProps) {
  const page = Math.max(1, parseInt(searchParams.page || "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;
  const [reports, totalCount] = await Promise.all([
    getLatestReports(PAGE_SIZE, offset),
    getReportCount(),
  ]);
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div>
      {/* Schema.org WebSite */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
      />

      {/* 텔레그램 구독 유도 배너 */}
      <div className="mb-8 p-5 bg-gradient-to-r from-primary to-primary/90 rounded-xl shadow-md flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📱</span>
          <p className="text-white font-semibold text-center sm:text-left">
            매일 아침·오후 리포트를 텔레그램으로 받아보세요
          </p>
        </div>
        <a
          href={TELEGRAM_CHANNEL}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 px-5 py-2.5 bg-white text-primary rounded-lg hover:bg-gray-100 transition-colors text-sm font-bold shadow-sm"
        >
          텔레그램 채널 구독
        </a>
      </div>

      {/* 제휴 배너 */}
      <div className="mb-8 space-y-4">
        <a
          href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-xl overflow-hidden hover:shadow-md transition-all"
        >
          <img
            src="/allcredit.jpg"
            alt="올크레딧 신용점수 조회"
            className="w-full h-auto"
            loading="eager"
          />
        </a>
        <a
          href="https://linkmoa.kr/click.php?m=agoda&a=A100693729&l=0000"
          target="_blank"
          rel="noopener noreferrer"
          className="block bg-gradient-to-r from-[#1a1a6c] via-[#b21f1f] to-[#fdbb2d] rounded-xl p-5 hover:shadow-lg transition-all"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white text-lg font-bold mb-1">✈️ 아고다 특가 호텔</p>
              <p className="text-white/80 text-sm">전 세계 숙소 최저가 비교 · 오늘만 특별 할인</p>
            </div>
            <span className="shrink-0 px-4 py-2 bg-white text-[#b21f1f] rounded-lg text-sm font-bold shadow-sm">
              예약하기 →
            </span>
          </div>
        </a>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-20 text-text-muted bg-white rounded-xl border border-border">
          아직 발행된 리포트가 없습니다.
        </div>
      ) : (
        <div className="grid gap-3">
          {reports.map((r) => {
            const label = typeLabel(r.report_type);
            return (
              <a
                key={`${r.report_date}-${r.report_type}`}
                href={`/report/${r.report_date}?type=${r.report_type}`}
                className="block bg-white border border-border rounded-xl p-5 hover:shadow-md hover:border-primary/40 transition-all group"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-semibold ${label.color}`}
                  >
                    {label.icon} {label.text}
                  </span>
                  <span className="text-sm text-text-muted">
                    {formatDate(r.report_date)}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-text-primary mb-1 group-hover:text-primary transition-colors">
                  {r.title}
                </h2>
                {r.summary && (
                  <p className="text-sm text-text-secondary line-clamp-2 whitespace-pre-line">
                    {r.summary}
                  </p>
                )}
              </a>
            );
          })}
        </div>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <nav className="mt-8 flex justify-center items-center gap-2">
          {page > 1 && (
            <a
              href={`/?page=${page - 1}`}
              className="px-4 py-2 bg-white border border-border rounded-lg text-sm hover:border-primary/40 transition-colors"
            >
              ← 이전
            </a>
          )}
          <span className="px-4 py-2 text-sm text-text-muted">
            {page} / {totalPages}
          </span>
          {page < totalPages && (
            <a
              href={`/?page=${page + 1}`}
              className="px-4 py-2 bg-white border border-border rounded-lg text-sm hover:border-primary/40 transition-colors"
            >
              다음 →
            </a>
          )}
        </nav>
      )}
    </div>
  );
}
