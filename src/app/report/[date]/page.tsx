import { getReport, getAdjacentReports } from "@/lib/db";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://example.com";
const SITE_NAME = "주식 리포트";
const TELEGRAM_CHANNEL = "https://t.me/your_channel";

interface PageProps {
  params: { date: string };
  searchParams: { type?: string };
}

// SSR
export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
  searchParams,
}: PageProps): Promise<Metadata> {
  const type = searchParams.type || "closing";
  const report = await getReport(params.date, type);

  if (!report) {
    return { title: "리포트를 찾을 수 없습니다" };
  }

  const titleSuffix =
    type === "morning"
      ? `미국 증시 마감 정리 | 나스닥 S&P500 환율 | ${SITE_NAME}`
      : `주식 상승 종목 하락 종목 테마 분석 정리 | ${SITE_NAME}`;

  return {
    title: report.title || `${params.date} ${titleSuffix}`,
    description:
      report.meta_description ||
      `${params.date} 한국 주식 상승 하락 종목, 테마 분석, 공시 정리`,
    openGraph: {
      title: report.title,
      description: report.meta_description || report.title,
      type: "article",
      publishedTime: report.published_at || undefined,
      siteName: SITE_NAME,
      url: `${SITE_URL}/report/${params.date}?type=${type}`,
    },
  };
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });
}

export default async function ReportPage({ params, searchParams }: PageProps) {
  const type = searchParams.type || "closing";
  const report = await getReport(params.date, type);

  if (!report) {
    notFound();
  }

  const adjacent = await getAdjacentReports(params.date, type);

  const typeLabel =
    report.report_type === "morning" ? "아침 브리핑" : "마감 리포트";

  // Schema.org Article JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: report.title,
    datePublished: report.published_at || report.report_date,
    description: report.meta_description || report.title,
    author: { "@type": "Organization", name: SITE_NAME },
    url: `${SITE_URL}/report/${params.date}?type=${type}`,
  };

  // 본문 내 링크를 새 탭에서 열도록 처리
  const contentWithTargetBlank = report.content.replace(
    /<a\s+href=/g,
    '<a target="_blank" rel="noopener noreferrer" href=',
  );

  return (
    <>
      {/* Schema.org 구조화 데이터 */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <article className="max-w-4xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <span
              className={`text-xs text-white px-2 py-0.5 rounded ${
                report.report_type === "morning" ? "bg-blue-600" : "bg-primary"
              }`}
            >
              {typeLabel}
            </span>
            <time className="text-sm text-gray-400">
              {formatDate(report.report_date)}
            </time>
          </div>
          <h1 className="text-3xl font-bold text-white">{report.title}</h1>
        </div>

        {/* 본문 (HTML) */}
        <div
          className="report-content"
          dangerouslySetInnerHTML={{ __html: contentWithTargetBlank }}
        />

        {/* 면책 문구 */}
        <div className="mt-10 p-4 bg-surface border border-border rounded-lg text-xs text-gray-500 leading-relaxed">
          ⚠️ 본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, 특정
          종목의 매수·매도를 권유하지 않습니다. 투자 판단의 최종 책임은 투자자
          본인에게 있습니다. 본 블로그는 시세 조회 서비스가 아닌 뉴스 큐레이션
          블로그입니다.
        </div>

        {/* 텔레그램 구독 유도 배너 */}
        <div className="mt-6 p-5 bg-gradient-to-r from-primary/20 to-blue-600/20 border border-primary/30 rounded-lg text-center">
          <p className="text-white font-semibold mb-2">
            매일 아침·오후 리포트를 텔레그램으로 받아보세요
          </p>
          <a
            href={TELEGRAM_CHANNEL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-5 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors text-sm font-medium"
          >
            텔레그램 채널 구독하기
          </a>
        </div>

        {/* 이전/다음 리포트 네비게이션 */}
        <nav className="mt-8 pt-6 border-t border-border flex justify-between items-start gap-4">
          <div className="flex-1 min-w-0">
            {adjacent.prev ? (
              <a
                href={`/report/${adjacent.prev.report_date}?type=${adjacent.prev.report_type}`}
                className="group block"
              >
                <span className="text-xs text-gray-500">이전 리포트</span>
                <p className="text-sm text-primary group-hover:underline truncate">
                  ← {adjacent.prev.title}
                </p>
              </a>
            ) : (
              <a href="/" className="text-primary hover:underline text-sm">
                ← 전체 목록
              </a>
            )}
          </div>
          <div className="flex-1 min-w-0 text-right">
            {adjacent.next && (
              <a
                href={`/report/${adjacent.next.report_date}?type=${adjacent.next.report_type}`}
                className="group block"
              >
                <span className="text-xs text-gray-500">다음 리포트</span>
                <p className="text-sm text-primary group-hover:underline truncate">
                  {adjacent.next.title} →
                </p>
              </a>
            )}
          </div>
        </nav>
      </article>
    </>
  );
}
