import { getLatestReports } from "@/lib/db";

const SITE_URL =
  process.env.NEXT_PUBLIC_BASE_URL || "https://kjusik.com";
const SITE_NAME = "주식 리포트";

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  const reports = await getLatestReports(30);

  const items = reports
    .map((r) => {
      const url = `${SITE_URL}/report/${r.report_date}?type=${r.report_type}`;
      const desc = r.meta_description || r.summary || r.title;
      return `    <item>
      <title>${escapeXml(r.title)}</title>
      <link>${url}</link>
      <guid isPermaLink="true">${url}</guid>
      <pubDate>${new Date(r.report_date).toUTCString()}</pubDate>
      <description>${escapeXml(desc)}</description>
    </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${SITE_NAME}</title>
    <link>${SITE_URL}</link>
    <description>매일 아침 미국장 마감 브리핑과 오후 한국장 마감 리포트</description>
    <language>ko</language>
    <atom:link href="${SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "s-maxage=3600, stale-while-revalidate",
    },
  });
}
