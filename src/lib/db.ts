import { Pool } from "@neondatabase/serverless";

const pool = new Pool({
  connectionString: process.env.NEON_DATABASE_URL,
});

export interface ReportRow {
  id: number;
  report_date: string;
  report_type: "morning" | "closing";
  title: string;
  content: string;
  summary: string | null;
  meta_description: string | null;
  market_data: Record<string, unknown> | null;
  top_gainers: Record<string, unknown>[] | null;
  top_losers: Record<string, unknown>[] | null;
  themes: Record<string, unknown> | null;
  disclosures: Record<string, unknown> | null;
  supply_data: Record<string, unknown> | null;
  news_links: Record<string, unknown>[] | null;
  created_at: string;
  published_at: string | null;
  telegram_sent: boolean;
}

export interface ReportSummary {
  report_date: string;
  report_type: string;
  title: string;
  summary: string | null;
  meta_description: string | null;
}

function toDateString(val: unknown): string {
  if (val instanceof Date) {
    return val.toISOString().split("T")[0];
  }
  return String(val).split("T")[0];
}

export async function getLatestReports(limit = 20): Promise<ReportSummary[]> {
  const { rows } = await pool.query(
    `SELECT report_date, report_type, title, summary, meta_description
     FROM stock_reports
     ORDER BY report_date DESC, report_type DESC
     LIMIT $1`,
    [limit],
  );
  return (rows as ReportSummary[]).map((r) => ({
    ...r,
    report_date: toDateString(r.report_date),
  }));
}

export async function getReport(
  date: string,
  type: string = "closing",
): Promise<ReportRow | null> {
  const { rows } = await pool.query(
    `SELECT * FROM stock_reports
     WHERE report_date = $1 AND report_type = $2`,
    [date, type],
  );
  const row = rows[0] as ReportRow | undefined;
  if (!row) return null;
  return { ...row, report_date: toDateString(row.report_date) };
}

export async function getReportDates(): Promise<string[]> {
  const { rows } = await pool.query(
    `SELECT DISTINCT report_date FROM stock_reports ORDER BY report_date DESC`,
  );
  return rows.map((r: { report_date: string }) => r.report_date);
}

export interface AdjacentReports {
  prev: { report_date: string; report_type: string; title: string } | null;
  next: { report_date: string; report_type: string; title: string } | null;
}

export async function getAdjacentReports(
  date: string,
  type: string,
): Promise<AdjacentReports> {
  const { rows: prevRows } = await pool.query(
    `SELECT report_date, report_type, title FROM stock_reports
     WHERE (report_date, report_type) < ($1, $2)
     ORDER BY report_date DESC, report_type DESC LIMIT 1`,
    [date, type],
  );
  const { rows: nextRows } = await pool.query(
    `SELECT report_date, report_type, title FROM stock_reports
     WHERE (report_date, report_type) > ($1, $2)
     ORDER BY report_date ASC, report_type ASC LIMIT 1`,
    [date, type],
  );
  const prev = prevRows[0] as AdjacentReports["prev"] | undefined;
  const next = nextRows[0] as AdjacentReports["next"] | undefined;
  return {
    prev: prev ? { ...prev, report_date: toDateString(prev.report_date) } : null,
    next: next ? { ...next, report_date: toDateString(next.report_date) } : null,
  };
}
