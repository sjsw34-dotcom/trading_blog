import { getLatestReports } from "@/lib/db";
import type { Metadata } from "next";

const TELEGRAM_CHANNEL = "https://t.me/your_channel";

export const metadata: Metadata = {
  title: "주식 리포트 — 매일 한국/미국 시장 브리핑",
  description:
    "매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트. 상승/하락 종목, 테마 분석, 수급, 공시 자동 정리.",
};

// SSR — 매 요청마다 DB에서 최신 데이터 조회
export const dynamic = "force-dynamic";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function typeLabel(type: string): { text: string; color: string } {
  if (type === "morning") {
    return { text: "아침 브리핑", color: "bg-blue-600" };
  }
  return { text: "마감 리포트", color: "bg-primary" };
}

export default async function HomePage() {
  const reports = await getLatestReports(30);

  return (
    <div>
      <section className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">최신 리포트</h1>
        <p className="text-gray-400">
          매일 아침 미국장 마감 브리핑 + 오후 한국장 마감 리포트를 자동
          생성합니다.
        </p>
      </section>

      {/* 텔레그램 구독 유도 배너 */}
      <div className="mb-8 p-5 bg-gradient-to-r from-primary/20 to-blue-600/20 border border-primary/30 rounded-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-white font-semibold text-center sm:text-left">
          매일 아침·오후 리포트를 텔레그램으로 받아보세요
        </p>
        <a
          href={TELEGRAM_CHANNEL}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 px-5 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors text-sm font-medium"
        >
          텔레그램 채널 구독
        </a>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          아직 발행된 리포트가 없습니다.
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((r) => {
            const label = typeLabel(r.report_type);
            return (
              <a
                key={`${r.report_date}-${r.report_type}`}
                href={`/report/${r.report_date}?type=${r.report_type}`}
                className="block bg-surface border border-border rounded-lg p-5 hover:border-primary transition-colors"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={`text-xs text-white px-2 py-0.5 rounded ${label.color}`}
                  >
                    {label.text}
                  </span>
                  <span className="text-sm text-gray-400">
                    {formatDate(r.report_date)}
                  </span>
                </div>
                <h2 className="text-lg font-semibold text-white mb-1">
                  {r.title}
                </h2>
                {r.summary && (
                  <p className="text-sm text-gray-400 line-clamp-2 whitespace-pre-line">
                    {r.summary}
                  </p>
                )}
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
