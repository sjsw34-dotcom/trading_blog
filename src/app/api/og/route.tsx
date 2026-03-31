import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const title = searchParams.get("title") || "주식 리포트";
  const type = searchParams.get("type") || "closing";
  const date = searchParams.get("date") || "";

  const isMorning = type === "morning";
  const icon = isMorning ? "🇺🇸" : "🇰🇷";
  const label = isMorning ? "아침 브리핑" : "마감 리포트";
  const gradientFrom = isMorning ? "#1e3a5f" : "#0f172a";
  const gradientTo = isMorning ? "#2d5a8e" : "#1e293b";
  const accentColor = isMorning ? "#ef4444" : "#f59e0b";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px",
          background: `linear-gradient(135deg, ${gradientFrom}, ${gradientTo})`,
          fontFamily: "sans-serif",
        }}
      >
        {/* 상단: 배지 + 날짜 */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: accentColor,
              color: "white",
              padding: "8px 20px",
              borderRadius: "30px",
              fontSize: "28px",
              fontWeight: 700,
            }}
          >
            {icon} {label}
          </div>
          {date && (
            <div style={{ color: "#94a3b8", fontSize: "26px" }}>{date}</div>
          )}
        </div>

        {/* 중간: 제목 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            flex: 1,
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: "52px",
              fontWeight: 800,
              color: "white",
              lineHeight: 1.3,
              wordBreak: "keep-all",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </div>
        </div>

        {/* 하단: 사이트명 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                background: accentColor,
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "18px",
                fontWeight: 900,
              }}
            >
              SR
            </div>
            <div style={{ color: "#cbd5e1", fontSize: "24px", fontWeight: 600 }}>
              kjusik.com
            </div>
          </div>
          <div style={{ color: "#64748b", fontSize: "20px" }}>
            매일 한국/미국 시장 브리핑
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    },
  );
}
