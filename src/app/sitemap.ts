import { getLatestReports } from "@/lib/db";
import type { MetadataRoute } from "next";

const SITE_URL =
  process.env.NEXT_PUBLIC_BASE_URL || "https://kjusik.com";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const reports = await getLatestReports(1000);

  const reportUrls = reports.map((r) => ({
    url: `${SITE_URL}/report/${r.report_date}?type=${r.report_type}`,
    lastModified: new Date(r.report_date),
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  return [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    ...reportUrls,
  ];
}
