import { getReport, getAdjacentReports } from "@/lib/db";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import sanitizeHtml from "sanitize-html";

const SITE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://kjusik.com";
const SITE_NAME = "주식 리포트";
const TELEGRAM_CHANNEL = "https://t.me/kr_stock_daily";

interface PageProps {
  params: { date: string };
  searchParams: { type?: string };
}

// ISR — 리포트는 게시 후 거의 변경되지 않으므로 5분 캐싱
export const revalidate = 300;

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

  const pageUrl = `${SITE_URL}/report/${params.date}?type=${type}`;
  const desc =
    report.meta_description ||
    `${params.date} 한국 주식 상승 하락 종목, 테마 분석, 공시 정리`;

  const ogImage = `${SITE_URL}/api/og?title=${encodeURIComponent(report.title)}&type=${type}&date=${params.date}`;

  return {
    title: report.title || `${params.date} ${titleSuffix}`,
    description: desc,
    alternates: {
      canonical: pageUrl,
    },
    openGraph: {
      title: report.title,
      description: desc,
      type: "article",
      publishedTime: report.published_at || undefined,
      siteName: SITE_NAME,
      url: pageUrl,
      images: [{ url: ogImage, width: 1200, height: 630, alt: report.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: report.title,
      description: desc,
      images: [ogImage],
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
  const typeIcon = report.report_type === "morning" ? "🇺🇸" : "🇰🇷";
  const typeBadgeColor =
    report.report_type === "morning"
      ? "bg-stock-down text-white"
      : "bg-accent text-white";

  const pageUrl = `${SITE_URL}/report/${params.date}?type=${type}`;

  // Schema.org Article JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: report.title,
    datePublished: report.published_at || report.report_date,
    description: report.meta_description || report.title,
    author: { "@type": "Organization", name: SITE_NAME },
    publisher: { "@type": "Organization", name: SITE_NAME },
    url: pageUrl,
    mainEntityOfPage: { "@type": "WebPage", "@id": pageUrl },
  };

  // Breadcrumb JSON-LD
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "홈",
        item: SITE_URL,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: report.title,
        item: pageUrl,
      },
    ],
  };

  // HTML sanitize 후 링크를 새 탭에서 열도록 처리
  const sanitized = sanitizeHtml(report.content, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat([
      "article", "section", "span", "div", "img", "h1", "h2", "h3", "h4",
    ]),
    allowedAttributes: {
      ...sanitizeHtml.defaults.allowedAttributes,
      span: ["class"],
      div: ["class"],
      article: ["class"],
      section: ["class"],
      a: ["href", "target", "rel", "class"],
      th: ["colspan", "rowspan"],
      td: ["colspan", "rowspan"],
    },
  });
  const contentWithTargetBlank = sanitized.replace(
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
      />

      <div className="max-w-6xl mx-auto lg:flex lg:gap-6">
        {/* 본문 영역 */}
        <article className="flex-1 min-w-0">
          {/* 광고 고지 */}
          <p className="mb-4 text-[13px] text-text-muted text-center">이 포스팅은 제휴 마케팅 광고를 포함하고 있습니다.</p>

          {/* 헤더 */}
          <div className="mb-8 bg-white rounded-xl shadow-sm border border-border p-6">
            <div className="flex items-center gap-3 mb-3">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold ${typeBadgeColor}`}
              >
                {typeIcon} {typeLabel}
              </span>
              <time className="text-sm text-text-muted">
                {formatDate(report.report_date)}
              </time>
            </div>
            <h1 className="text-2xl font-bold text-primary">{report.title}</h1>
          </div>

          {/* 올크레딧 CPS 배너 */}
          <div className="mb-6">
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
          </div>

          {/* 아고다 배너 */}
          <div className="mb-6">
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

          {/* CPC 광고 (본문 상단) */}
          <div className="mb-6">
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 hover:shadow-md hover:border-blue-400 transition-all text-center"
            >
              <span className="text-sm font-semibold text-blue-700">📊 올크레딧 — 내 신용점수·신용정보 무료 조회하기</span>
            </a>
          </div>

          {/* 본문 (HTML) — 중간에 CPC 광고 삽입 */}
          {(() => {
            const searchFrom = Math.floor(contentWithTargetBlank.length * 0.4);
            const h2Pos = contentWithTargetBlank.indexOf("<h2", searchFrom);
            if (h2Pos > 0) {
              const firstHalf = contentWithTargetBlank.slice(0, h2Pos);
              const secondHalf = contentWithTargetBlank.slice(h2Pos);
              return (
                <>
                  <div className="bg-white rounded-xl shadow-sm border border-border p-6 mb-6">
                    <div className="report-content" dangerouslySetInnerHTML={{ __html: firstHalf }} />
                  </div>
                  <div className="mb-6">
                    <a href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000" target="_blank" rel="noopener noreferrer"
                      className="block bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 hover:shadow-md hover:border-green-400 transition-all text-center">
                      <span className="text-sm font-semibold text-green-700 hidden sm:inline">📊 올크레딧 — 신용점수·대출정보·카드내역 무료 조회!</span>
                      <span className="text-sm font-semibold text-green-700 sm:hidden">📊 올크레딧 — 내 신용정보 무료 조회!</span>
                    </a>
                  </div>
                  <div className="bg-white rounded-xl shadow-sm border border-border p-6 mb-6">
                    <div className="report-content" dangerouslySetInnerHTML={{ __html: secondHalf }} />
                  </div>
                </>
              );
            }
            return (
              <div className="bg-white rounded-xl shadow-sm border border-border p-6 mb-6">
                <div className="report-content" dangerouslySetInnerHTML={{ __html: contentWithTargetBlank }} />
              </div>
            );
          })()}

          {/* 모바일 사이드바 광고 (lg 이하에서만 표시) */}
          <div className="lg:hidden my-6 space-y-4">
            {/* 아고다 배너 (모바일) */}
            <a
              href="https://linkmoa.kr/click.php?m=agoda&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gradient-to-r from-[#1a1a6c] via-[#b21f1f] to-[#fdbb2d] rounded-xl p-4 hover:shadow-md transition-all"
            >
              <p className="text-white text-sm font-bold mb-1">✈️ 아고다 특가 호텔</p>
              <p className="text-white/80 text-xs">전 세계 숙소 최저가 비교 · 오늘만 특별 할인</p>
            </a>
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white border border-border rounded-xl p-4 hover:shadow-md hover:border-blue-400 transition-all"
            >
              <p className="text-xs text-text-muted mb-2 font-semibold">AD</p>
              <p className="text-sm font-bold text-primary mb-1">올크레딧 신용정보 조회</p>
              <p className="text-xs text-text-secondary">내 신용점수, 대출 현황, 카드 정보까지 한눈에! 올크레딧에서 무료로 확인하세요.</p>
            </a>
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white border border-border rounded-xl p-4 hover:shadow-md hover:border-green-400 transition-all"
            >
              <p className="text-xs text-text-muted mb-2 font-semibold">AD</p>
              <p className="text-sm font-bold text-primary mb-1">신용점수 관리</p>
              <p className="text-xs text-text-secondary">신용등급 변동 알림, 금융사별 신용점수 비교까지. 올크레딧으로 관리하세요.</p>
            </a>
          </div>

          {/* 면책 문구 */}
          <div className="p-4 bg-gray-50 border border-border rounded-xl text-xs text-text-muted leading-relaxed">
            ⚠️ 본 콘텐츠는 공개된 시장 데이터 및 뉴스를 정리한 것으로, 특정
            종목의 매수·매도를 권유하지 않습니다. 투자 판단의 최종 책임은 투자자
            본인에게 있습니다. 본 블로그는 시세 조회 서비스가 아닌 뉴스 큐레이션
            블로그입니다.
          </div>

          {/* 텔레그램 구독 유도 배너 */}
          <div className="mt-6 p-5 bg-gradient-to-r from-primary to-primary/90 rounded-xl shadow-md text-center">
            <p className="text-white font-semibold mb-3">
              매일 아침·오후 리포트를 텔레그램으로 받아보세요
            </p>
            <a
              href={TELEGRAM_CHANNEL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block px-6 py-2.5 bg-white text-primary rounded-lg hover:bg-gray-100 transition-colors text-sm font-bold shadow-sm"
            >
              텔레그램 채널 구독하기
            </a>
          </div>

          {/* 이전/다음 리포트 네비게이션 */}
          <nav className="mt-8 grid grid-cols-2 gap-4">
            <div>
              {adjacent.prev ? (
                <a
                  href={`/report/${adjacent.prev.report_date}?type=${adjacent.prev.report_type}`}
                  className="block bg-white border border-border rounded-xl p-4 hover:shadow-md hover:border-primary/40 transition-all group"
                >
                  <span className="text-xs text-text-muted">← 이전 리포트</span>
                  <p className="text-sm text-primary font-medium group-hover:underline truncate mt-1">
                    {adjacent.prev.title}
                  </p>
                </a>
              ) : (
                <a
                  href="/"
                  className="block bg-white border border-border rounded-xl p-4 hover:shadow-md hover:border-primary/40 transition-all"
                >
                  <span className="text-xs text-text-muted">←</span>
                  <p className="text-sm text-primary font-medium mt-1">전체 목록</p>
                </a>
              )}
            </div>
            <div>
              {adjacent.next && (
                <a
                  href={`/report/${adjacent.next.report_date}?type=${adjacent.next.report_type}`}
                  className="block bg-white border border-border rounded-xl p-4 hover:shadow-md hover:border-primary/40 transition-all group text-right"
                >
                  <span className="text-xs text-text-muted">다음 리포트 →</span>
                  <p className="text-sm text-primary font-medium group-hover:underline truncate mt-1">
                    {adjacent.next.title}
                  </p>
                </a>
              )}
            </div>
          </nav>
        </article>

        {/* 데스크탑 사이드바 (lg 이상에서만 표시) */}
        <aside className="hidden lg:block w-[280px] shrink-0">
          <div className="sticky top-6 space-y-5">
            {/* 올크레딧 CPS 배너 */}
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-xl overflow-hidden hover:shadow-md transition-all"
            >
              <img
                src="/allcredit.jpg"
                alt="올크레딧 신용점수 조회"
                className="w-full h-auto rounded-xl"
                loading="lazy"
              />
            </a>

            {/* 아고다 배너 (사이드바) */}
            <a
              href="https://linkmoa.kr/click.php?m=agoda&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-xl overflow-hidden hover:shadow-md transition-all"
            >
              <img
                src="/agoda.jpg"
                alt="아고다 특가 호텔 예약"
                className="w-full h-auto rounded-xl"
                loading="lazy"
              />
            </a>

            {/* CPC 광고 1 */}
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white border border-border rounded-xl p-5 hover:shadow-md hover:border-blue-400 transition-all"
            >
              <p className="text-xs text-text-muted mb-2 font-semibold">AD</p>
              <p className="text-sm font-bold text-primary mb-2">올크레딧 신용정보 조회</p>
              <p className="text-xs text-text-secondary leading-relaxed">내 신용점수, 대출 현황, 카드 정보까지 한눈에! 올크레딧에서 무료로 확인하세요.</p>
              <span className="inline-block mt-3 text-xs font-semibold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-full">무료 조회 →</span>
            </a>

            {/* CPC 광고 2 */}
            <a
              href="https://linkmoa.kr/click.php?m=allcredit&a=A100693729&l=0000"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white border border-border rounded-xl p-5 hover:shadow-md hover:border-green-400 transition-all"
            >
              <p className="text-xs text-text-muted mb-2 font-semibold">AD</p>
              <p className="text-sm font-bold text-primary mb-2">신용점수 관리</p>
              <p className="text-xs text-text-secondary leading-relaxed">신용등급 변동 알림, 금융사별 신용점수 비교까지. 올크레딧으로 관리하세요.</p>
              <span className="inline-block mt-3 text-xs font-semibold text-green-600 bg-green-50 px-3 py-1.5 rounded-full">확인하기 →</span>
            </a>

            {/* 텔레그램 구독 */}
            <div className="bg-gradient-to-b from-primary to-primary/90 rounded-xl p-5 text-center">
              <p className="text-white text-sm font-semibold mb-3">텔레그램으로<br />매일 리포트 받기</p>
              <a
                href={TELEGRAM_CHANNEL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block w-full px-4 py-2.5 bg-white text-primary rounded-lg hover:bg-gray-100 transition-colors text-sm font-bold"
              >
                구독하기
              </a>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
